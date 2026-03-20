"""FastAPI server for IngredientIQ backend."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import base64
from pathlib import Path

from config import settings
from rag.knowledge_base import ChemicalKnowledgeBase, seed_knowledge_base
from rag.rag_pipeline import IngredientSafetyRAG
from llm.llm_factory import LLMFactory
from mcp_server.tools import (
    ProductLookupTool, ChemicalDataTool, IngredientParserTool, MCPToolRegistry
)


# Initialize FastAPI app
app = FastAPI(
    title="IngredientIQ",
    description="AI-powered ingredient safety analysis with RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
kb = ChemicalKnowledgeBase(settings.VECTOR_DB_PATH)
llm = LLMFactory.create_llm()
rag_pipeline = IngredientSafetyRAG(kb, llm=llm)


# ============= Pydantic Models =============

class ProductSearchRequest(BaseModel):
    """Request model for product search."""
    product_name: str


class IngredientAnalysisRequest(BaseModel):
    """Request model for ingredient analysis."""
    ingredients: List[str]


class ImageUploadRequest(BaseModel):
    """Request model for image upload."""
    image_base64: str
    instructions: Optional[str] = None


class ProductAnalysisResponse(BaseModel):
    """Response model for product analysis."""
    overall_rating: str
    overall_score: float
    ingredient_count: int
    safety_summary: dict
    ingredients: List[dict]


# ============= Health Check =============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "kb_size": kb.count_chemicals(),
        "llm_provider": settings.LLM_PROVIDER,
    }


# ============= Initialization =============

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    # Check if knowledge base is already seeded
    if kb.count_chemicals() == 0:
        print("Seeding knowledge base with initial data...")
        seed_knowledge_base(kb)
        print(f"Knowledge base seeded with {kb.count_chemicals()} chemicals.")


# ============= API Endpoints =============

@app.post("/api/v1/analyze-product", response_model=ProductAnalysisResponse)
async def analyze_product(request: ProductSearchRequest):
    """Analyze a product by name.
    
    Flow:
    1. Look up product in Open Food Facts API (MCP tool)
    2. Extract ingredients
    3. Analyze each ingredient with RAG
    4. Return comprehensive safety report
    
    Note: If product lookup fails, suggest using the direct ingredient analysis endpoint.
    """
    try:
        # Step 1: Look up product
        product = ProductLookupTool.lookup_product(request.product_name)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product '{request.product_name}' not found in database. " +
                       "Please use the direct ingredient analysis endpoint instead and provide " +
                       "the ingredients list manually."
            )
        
        # Step 2: Extract ingredients
        ingredients = product.get('ingredients', [])
        if not ingredients:
            raise HTTPException(
                status_code=400,
                detail="No ingredients found for this product"
            )
        
        # Step 3: Analyze ingredients
        analysis = rag_pipeline.analyze_product_ingredients(ingredients)
        
        return ProductAnalysisResponse(**analysis)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing product: {str(e)}"
        )


@app.post("/api/v1/analyze-ingredients")
async def analyze_ingredients(request: IngredientAnalysisRequest):
    """Analyze a list of ingredients.
    
    Pass raw ingredient list for analysis with RAG reasoning.
    """
    try:
        if not request.ingredients:
            raise HTTPException(
                status_code=400,
                detail="Ingredient list cannot be empty"
            )
        
        # Analyze ingredients
        analysis = rag_pipeline.analyze_product_ingredients(request.ingredients)
        
        return ProductAnalysisResponse(**analysis)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing ingredients: {str(e)}"
        )


@app.post("/api/v1/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    """Analyze a product label image.
    
    Flow:
    1. Accept image upload
    2. Use Claude Vision to extract ingredient text (OCR)
    3. Parse extracted text into ingredient list
    4. Analyze ingredients with RAG
    5. Return safety report
    """
    try:
        # Read image
        contents = await file.read()
        
        # Use Claude Vision to extract text (pass filename for format detection)
        analysis_result = _extract_ingredients_from_image(contents, file.filename or "")
        
        if not analysis_result.get('ingredients'):
            raise HTTPException(
                status_code=400,
                detail=analysis_result.get('error', "Could not extract ingredients from image")
            )
        
        # Analyze extracted ingredients
        analysis = rag_pipeline.analyze_product_ingredients(
            analysis_result['ingredients']
        )
        
        # Add extraction info
        analysis['extraction_source'] = 'image_ocr'
        analysis['image_analysis'] = analysis_result
        
        return analysis
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing image: {str(e)}"
        )


@app.post("/api/v1/ingredient-search")
async def search_ingredient(ingredient_name: str):
    """Search for information about a single ingredient.
    
    Returns:
    - Knowledge base match with RAG analysis
    - PubChem data if available
    - Safety classification with evidence
    """
    try:
        # Get RAG analysis
        analysis = rag_pipeline.analyze_ingredient(ingredient_name)
        
        # Try to get additional PubChem data
        pubchem_data = ChemicalDataTool.search_pubchem(ingredient_name)
        
        return {
            "ingredient": ingredient_name,
            "rag_analysis": analysis,
            "pubchem_data": pubchem_data
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching ingredient: {str(e)}"
        )


@app.get("/api/v1/tools")
async def list_available_tools():
    """List all available MCP tools."""
    tools_info = []
    for tool_name in MCPToolRegistry.list_tools():
        tool_def = MCPToolRegistry.get_tool(tool_name)
        tools_info.append({
            "name": tool_name,
            "description": tool_def.get('description'),
            "parameters": tool_def.get('params')
        })
    
    return {"tools": tools_info}


@app.get("/api/v1/knowledge-base-stats")
async def get_kb_stats():
    """Get statistics about the knowledge base."""
    return {
        "total_chemicals": kb.count_chemicals(),
        "vector_db_path": settings.VECTOR_DB_PATH,
        "embedding_model": settings.EMBEDDING_MODEL
    }


# ============= Helper Functions =============

def _extract_ingredients_from_image(image_bytes: bytes, filename: str = "") -> dict:
    """Extract ingredients from product image using Claude Vision.
    
    Args:
        image_bytes: Image file bytes
        filename: Optional filename to detect image format
        
    Returns:
        Dictionary with extracted ingredients and source
    """
    try:
        import base64
        from anthropic import Anthropic
        
        # Detect media type
        media_type = "image/jpeg"  # Default
        if filename:
            filename_lower = filename.lower()
            if filename_lower.endswith('.png'):
                media_type = "image/png"
            elif filename_lower.endswith('.gif'):
                media_type = "image/gif"
            elif filename_lower.endswith('.webp'):
                media_type = "image/webp"
            elif filename_lower.endswith(('.jpg', '.jpeg')):
                media_type = "image/jpeg"
        
        # Validate image size (max 5MB)
        if len(image_bytes) > 5 * 1024 * 1024:
            return {
                "ingredients": [],
                "error": "Image file too large (max 5MB)",
                "success": False
            }
        
        # Encode image
        image_base64 = base64.standard_b64encode(image_bytes).decode('utf-8')
        
        # Validate API key is set
        if not settings.ANTHROPIC_API_KEY:
            return {
                "ingredients": [],
                "error": "ANTHROPIC_API_KEY not configured. Please set the API key in backend/.env",
                "success": False
            }
        
        # Create Anthropic client with API key
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Call Claude Vision with improved prompt
        vision_prompt = """You are analyzing a product label image to extract ingredient information.

EXTRACT these fields if visible on the label:
1. PRODUCT_NAME: Full product name as shown
2. BRAND: Brand/manufacturer name
3. BARCODE: Any barcode/UPC number visible (12-14 digits)
4. PRODUCT_TYPE: Category (e.g., "body wash", "sunscreen", "lotion", "ketchup")
5. INGREDIENTS: Complete list of all ingredients listed on the package

SPECIAL RULES:
- Extract ingredient names EXACTLY as written on the label
- For cosmetics, prefer INCI names if provided
- Include percentages if shown: "Sodium Chloride 2.5%"
- Handle multiple ingredient sections (e.g., Active + Inactive)
- If ingredients are hard to read, mark confidence lower

RETURN VALID JSON ONLY (no other text):
{
  "product_name": "string or null",
  "brand": "string or null",
  "barcode": "string or null",
  "product_type": "string or null",
  "ingredients": ["ingredient1", "ingredient2", ...],
  "extraction_confidence": 0.0-1.0,
  "quality_issues": ["issue1", "issue2"],
  "is_cosmetic": true/false
}

QUALITY_ISSUES examples: ["Label too blurry", "Partial ingredients visible", "Image rotated"]
is_cosmetic: true if product_type suggests skincare/cosmetics, false otherwise

If you cannot extract ingredients, return:
{"ingredients": [], "extraction_confidence": 0.0, "quality_issues": ["Unable to read label"]}
"""
        
        message = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": vision_prompt
                        }
                    ],
                }
            ],
        )
        
        # Parse response - improved to handle structured JSON
        response_text = message.content[0].text.strip()
        
        try:
            # Try parsing as JSON (new format)
            parsed = json.loads(response_text)
            
            ingredients = parsed.get("ingredients", [])
            extraction_confidence = parsed.get("extraction_confidence", 0.5)
            quality_issues = parsed.get("quality_issues", [])
            product_name = parsed.get("product_name")
            brand = parsed.get("brand")
            barcode = parsed.get("barcode")
            product_type = parsed.get("product_type")
            is_cosmetic = parsed.get("is_cosmetic", False)
            
            return {
                "ingredients": ingredients,
                "product_name": product_name,
                "brand": brand,
                "barcode": barcode,
                "product_type": product_type,
                "is_cosmetic": is_cosmetic,
                "extraction_confidence": extraction_confidence,
                "quality_issues": quality_issues,
                "raw_response": response_text,
                "success": len(ingredients) > 0
            }
        
        except json.JSONDecodeError:
            # Fallback: parse as comma-separated list (old format)
            print(f"[Warning] Could not parse as JSON, falling back to comma-sep format")
            ingredients = [
                ing.strip() for ing in response_text.split(',')
                if ing.strip() and len(ing.strip()) > 2
            ]
            
            return {
                "ingredients": ingredients,
                "product_name": None,
                "brand": None,
                "barcode": None,
                "product_type": None,
                "is_cosmetic": False,
                "extraction_confidence": 0.5,
                "quality_issues": ["Response format unexpected"],
                "raw_response": response_text,
                "success": len(ingredients) > 0
            }
    
    except Exception as e:
        print(f"Error extracting ingredients from image: {e}")
        return {
            "ingredients": [],
            "error": str(e),
            "success": False
        }


# ============= Root =============

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "IngredientIQ API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG
    )
