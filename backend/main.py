"""FastAPI server for IngredientIQ backend."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import json
import base64
from pathlib import Path

from config import settings
from rag.knowledge_base import ChemicalKnowledgeBase, seed_knowledge_base
from rag.data_loaders import populate_knowledge_base
from rag.rag_pipeline import IngredientSafetyRAG
from llm.llm_factory import LLMFactory
from mcp_server.tools import (
    ProductLookupTool, ChemicalDataTool, IngredientParserTool, MCPToolRegistry
)
from mcp_server.mcp_server import mcp_server


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
rag_pipeline = IngredientSafetyRAG(kb, llm=llm, mcp_server=mcp_server)


# ============= Pydantic Models =============

class ProductSearchRequest(BaseModel):
    """Request model for product search."""
    product_name: str


class IngredientAnalysisRequest(BaseModel):
    """Request model for ingredient analysis."""
    ingredients: List[str]


class ProductWithIngredientsRequest(BaseModel):
    """Request model for analyzing a product with manually-provided ingredients."""
    product_name: str
    brand: Optional[str] = None
    ingredients: List[str]
    description: Optional[str] = None


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
    kb_size = kb.count_chemicals()
    print(f"Knowledge base status: {kb_size} chemicals loaded")
    
    if kb_size == 0:
        print("Knowledge base is empty. Seeding with data from multiple sources (FDA, EWG, IARC, PubChem)...")
        populate_knowledge_base(kb)
        print(f"✓ Knowledge base seeded with {kb.count_chemicals()} chemicals.")
    elif kb_size < 20:
        print(f"Knowledge base has only {kb_size} chemicals. Re-populating with comprehensive data...")
        kb.clear()
        populate_knowledge_base(kb)
        print(f"✓ Knowledge base re-populated with {kb.count_chemicals()} chemicals.")
    else:
        print(f"✓ Knowledge base contains {kb_size} chemicals (no re-seeding needed)")
    
    # Log available MCP tools
    print(f"✓ Available MCP tools: {list(mcp_server.get_tools().keys())}")


# ============= API Endpoints =============

@app.post("/api/v1/analyze-product", response_model=ProductAnalysisResponse)
async def analyze_product(request: ProductSearchRequest):
    """Analyze a product by name.
    
    Flow:
    1. Try LLM-based ingredient extraction first (Claude generates likely ingredients)
    2. Fallback to Open Food Facts API if LLM extraction fails
    3. Analyze each ingredient with RAG pipeline
    4. Return comprehensive safety report
    """
    try:
        print(f"\n[Analyze Product] Starting analysis for: '{request.product_name}'")
        
        # Step 1: Try LLM extraction first
        print(f"[Analyze Product] Step 1: Trying LLM-based ingredient extraction...")
        product = _extract_ingredients_from_product_name(request.product_name)
        
        # Step 2: Fallback to API if LLM failed
        if not product or not product.get('ingredients'):
            print(f"[Analyze Product] Step 2: LLM extraction unsuccessful, trying Open Food Facts API...")
            product = ProductLookupTool.lookup_product(request.product_name)
            
            if not product:
                # New behavior: Suggest the ingredient analysis endpoint instead of failing completely
                print(f"[Analyze Product] ✗ Product '{request.product_name}' not found in any source")
                raise HTTPException(
                    status_code=404,
                    detail=f"Product '{request.product_name}' not found in LLM or Open Food Facts database. "
                           f"Please use the /api/v1/analyze-ingredients endpoint with your own ingredient list, "
                           f"upload a product label image, or provide ingredients in your request."
                )
        else:
            print(f"[Analyze Product] ✓ LLM extracted {len(product.get('ingredients', []))} ingredients")
        
        # Step 3: Verify ingredients were found
        ingredients = product.get('ingredients', [])
        if not ingredients:
            raise HTTPException(
                status_code=400,
                detail="No ingredients found for this product"
            )
        
        # Step 4: Analyze ingredients with RAG
        print(f"[Analyze Product] Step 3: Analyzing {len(ingredients)} ingredients with RAG...")
        analysis = rag_pipeline.analyze_product_ingredients(ingredients)
        
        # Add product metadata
        analysis['product_name'] = product.get('product_name', 'Unknown')
        analysis['source'] = product.get('source', 'Unknown')
        if 'reasoning' in product:
            analysis['extraction_reasoning'] = product['reasoning']
        
        print(f"[Analyze Product] ✓ Analysis complete - Overall rating: {analysis.get('overall_rating')}")
        return ProductAnalysisResponse(**analysis)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Analyze Product] ✗ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing product: {str(e)}"
        )


@app.post("/api/v1/analyze-product-with-ingredients")
async def analyze_product_with_ingredients(request: ProductWithIngredientsRequest):
    """Analyze a product with user-provided ingredients.
    
    Use this endpoint when:
    - The product is not found in LLM or Open Food Facts database
    - You want to analyze a specific product with known ingredients
    - You have a product label and want to manually provide ingredients
    
    Flow:
    1. Accept product name and ingredients from user
    2. Analyze each ingredient with multi-source lookup (PubChem, FDA, EWG, IARC)
    3. Return comprehensive safety report
    """
    try:
        print(f"\n[Analyze Product + Ingredients] Starting analysis for: '{request.product_name}'")
        
        # Verify ingredients were provided
        if not request.ingredients or len(request.ingredients) == 0:
            raise HTTPException(
                status_code=400,
                detail="Ingredient list cannot be empty"
            )
        
        # Analyze ingredients with RAG
        print(f"[Analyze Product + Ingredients] Analyzing {len(request.ingredients)} ingredients...")
        analysis = rag_pipeline.analyze_product_ingredients(request.ingredients)
        
        # Add product metadata
        analysis['product_name'] = request.product_name
        analysis['brand'] = request.brand or "Unknown"
        analysis['source'] = "User-Provided"
        if request.description:
            analysis['description'] = request.description
        
        print(f"[Analyze Product + Ingredients] ✓ Analysis complete - Overall rating: {analysis.get('overall_rating')}")
        return ProductAnalysisResponse(**analysis)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Analyze Product + Ingredients] ✗ Error: {e}")
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
    tools = mcp_server.get_tools()
    
    tools_info = []
    for tool_name, tool_def in tools.items():
        tools_info.append({
            "name": tool_name,
            "description": tool_def.get('description'),
            "parameters": tool_def.get('params')
        })
    
    return {"tools": tools_info, "count": len(tools_info)}


@app.get("/api/v1/knowledge-base-stats")
async def get_kb_stats():
    """Get statistics about the knowledge base."""
    return {
        "total_chemicals": kb.count_chemicals(),
        "vector_db_path": settings.VECTOR_DB_PATH,
        "embedding_model": settings.EMBEDDING_MODEL
    }


@app.post("/api/v1/mcp-call")
async def call_mcp_tool(tool_name: str, args: dict = None):
    """Call an MCP tool directly.
    
    Args:
        tool_name: Name of the MCP tool to call
        args: Tool arguments as JSON
    
    Returns:
        Tool result
    """
    if not args:
        args = {}
    
    try:
        result = mcp_server.call_tool(tool_name, args)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error calling MCP tool '{tool_name}': {str(e)}"
        )


# ============= Helper Functions =============

def _extract_ingredients_from_image(image_bytes: bytes, filename: str = "") -> Dict:
    """Extract ingredients from product label image using Claude Vision.
    
    Uses Claude's vision API to:
    1. Read text from product label image
    2. Extract and parse ingredient list
    3. Return parsed ingredients
    
    Args:
        image_bytes: Raw image file bytes
        filename: Filename to detect image format (jpg, png, etc.)
        
    Returns:
        Dictionary with extracted ingredients and metadata
    """
    try:
        if not settings.ANTHROPIC_API_KEY:
            return {
                "error": "API key not configured",
                "ingredients": []
            }
        
        import base64
        from anthropic import Anthropic
        
        # Encode image as base64
        image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
        
        # Determine image media type
        media_type = "image/jpeg"
        if filename.lower().endswith('.png'):
            media_type = "image/png"
        elif filename.lower().endswith('.gif'):
            media_type = "image/gif"
        elif filename.lower().endswith('.webp'):
            media_type = "image/webp"
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        vision_prompt = """You are a product label analysis expert. Analyze this product label image and extract the ingredient information.

CRITICAL: You MUST respond with ONLY valid JSON, no other text before or after.

TASK:
1. Identify and extract the ingredient list from the product label
2. Parse each ingredient name (ignore concentrations, percentages, and detailed descriptions)
3. Clean up ingredient names (remove extra spaces, parentheticals with concentrations)
4. Return ONLY valid JSON with the extracted data

RETURN JSON (no markdown, no explanation, ONLY this JSON object):
{
  "product_name": "detected product name or 'Unknown'",
  "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
  "extraction_confidence": 0.85,
  "notes": "brief notes about extraction quality"
}

RULES:
- Only JSON, nothing else
- If you cannot read the label, return empty ingredients array and note the issue
- Ingredient names only (no percentages, descriptions, or formatting chars)
- Example: "Aqua (Water) 50%" becomes "Water"
- No code blocks, no markdown, no explanation text"""
        
        try:
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
                                    "data": image_data,
                                }
                            },
                            {
                                "type": "text",
                                "text": vision_prompt
                            }
                        ]
                    }
                ]
            )
            
            # Extract and validate response
            if not message.content or len(message.content) == 0:
                print("[Image Extract] ✗ Empty response from Claude Vision API")
                return {
                    "error": "Claude Vision API returned empty response",
                    "ingredients": []
                }
            
            response_text = message.content[0].text.strip() if hasattr(message.content[0], 'text') else ""
            
            if not response_text:
                print("[Image Extract] ✗ Empty text in Claude Vision response")
                return {
                    "error": "Claude Vision could not extract text from image",
                    "ingredients": []
                }
            
            print(f"[Image Extract] Raw API response: {response_text[:200]}...")  # Log first 200 chars for debugging
            
            # Try to extract JSON from response (in case it's wrapped in markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON response
            try:
                parsed = json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"[Image Extract] ✗ Failed to parse JSON: {e}")
                print(f"[Image Extract] Response text: {json_text[:500]}")
                return {
                    "error": f"Claude Vision did not return valid JSON: {str(e)}",
                    "ingredients": [],
                    "raw_response": json_text[:300]
                }
            
            ingredients = parsed.get("ingredients", [])
            confidence = parsed.get("extraction_confidence", 0.5)
            product_name = parsed.get("product_name", "Unknown Product")
            notes = parsed.get("notes", "")
            
            if ingredients:
                print(f"[Image Extract] ✓ Extracted {len(ingredients)} ingredients from label (confidence: {confidence:.2f})")
                if notes:
                    print(f"[Image Extract] Notes: {notes}")
                return {
                    "product_name": product_name,
                    "ingredients": ingredients,
                    "confidence": confidence,
                    "notes": notes,
                    "source": "image_ocr"
                }
            else:
                return {
                    "error": f"Could not extract ingredients from image. {notes}",
                    "ingredients": [],
                    "confidence": confidence,
                    "notes": notes
                }
        
        except json.JSONDecodeError as e:
            print(f"[Image Extract] ✗ JSON parsing error: {e}")
            return {
                "error": f"Failed to parse image content: {str(e)}",
                "ingredients": []
            }
    
    except Exception as e:
        print(f"[Image Extract] ✗ Error: {e}")
        return {
            "error": f"Error analyzing image: {str(e)}",
            "ingredients": []
        }


def _extract_ingredients_from_product_name(product_name: str) -> Dict:
    """Extract likely ingredients using Claude LLM based on product name.
    
    Uses Claude to generate/infer ingredients for a product based on its name,
    brand, and general product knowledge. Falls back to empty list if LLM fails.
    
    Args:
        product_name: Name of the product (e.g., "Neutrogena Ultra Sheer Sunscreen")
        
    Returns:
        Dictionary with product info and ingredients list
    """
    try:
        if not settings.ANTHROPIC_API_KEY:
            print("[LLM Extract] API key not configured, skipping LLM extraction")
            return None
        
        from anthropic import Anthropic
        
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        extraction_prompt = f"""You are a product ingredient expert. Based on the product name provided, 
generate a comprehensive list of likely ingredients for this product.

PRODUCT NAME: {product_name}

INSTRUCTIONS:
1. Analyze the product name to determine product type, brand, and category
2. Based on common formulations for this type of product, list typical ingredients
3. For {product_name}, provide the most likely ingredients at typical concentrations
4. Include both active and inactive ingredients (water, preservatives, etc.)
5. Return ONLY valid JSON, no other text

RETURN JSON FORMAT:
{{
  "product_name": "{product_name}",
  "likely_ingredients": ["ingredient1", "ingredient2", ...],
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of ingredients chosen"
}}

INGREDIENT PATTERNS BY PRODUCT TYPE:
- **Bar Soap / Dove Soap**: sodium tallowate, water, glycerin, sodium carbonate, sodium chloride, parfum, tetrasodium edta, tetrasodium etidronate, mica, titanium dioxide, CI 77891, sodium palmitate, palm kernel acid, sodium stearate
- **Liquid Soap**: water, sodium laureth sulfate, cocamidopropyl betaine, glycerin, sodium chloride, preservatives, fragrance
- **Shampoo**: water, sodium laureth sulfate, cocamidopropyl betaine, glycerin, dimethicone, fragrance, preservatives, citric acid
- **Moisturizer**: water, glycerin, cetyl alcohol, dimethicone, carbomer, triethanolamine, methylparaben, propylparaben
- **Sunscreen**: water, zinc oxide or titanium dioxide, octinoxate, glycerin, cetyl alcohol, preservatives
- **Cleanser**: water, sodium laureth sulfate, glycerin, ascorbic acid, sodium hydroxide, preservatives, fragrance

For "{product_name}", identify the product type and generate realistic typical ingredients."""
        
        message = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": extraction_prompt
                }
            ],
        )
        
        response_text = message.content[0].text.strip()
        
        try:
            # Parse JSON response
            parsed = json.loads(response_text)
            ingredients = parsed.get("likely_ingredients", [])
            confidence = parsed.get("confidence", 0.5)
            
            # Accept ingredients if we have any, even with lower confidence
            # LLM generation is reasonable for common products
            if ingredients:
                print(f"[LLM Extract] ✓ Generated {len(ingredients)} ingredients for '{product_name}' (confidence: {confidence:.2f})")
                return {
                    "product_name": product_name,
                    "brand": "Unknown",
                    "ingredients": ingredients,
                    "source": "LLM-Generated",
                    "confidence": confidence,
                    "reasoning": parsed.get("reasoning", "")
                }
            else:
                print(f"[LLM Extract] ✗ No ingredients generated by LLM")
                return None
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[LLM Extract] ✗ Failed to parse response: {e}")
            return None
    
    except Exception as e:
        print(f"[LLM Extract] Error: {e}")
        return None
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
