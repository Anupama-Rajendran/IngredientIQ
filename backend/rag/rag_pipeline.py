"""RAG pipeline for ingredient safety analysis."""
from typing import List, Dict, Optional
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from .knowledge_base import ChemicalKnowledgeBase
import json


class IngredientSafetyRAG:
    """RAG pipeline for analyzing ingredient safety with citations."""
    
    def __init__(self, kb: ChemicalKnowledgeBase, llm=None):
        """Initialize the RAG pipeline.
        
        Args:
            kb: ChemicalKnowledgeBase instance
            llm: Language model to use (if None, uses Claude via Anthropic)
        """
        self.kb = kb
        self.llm = llm
        
        self.safety_prompt_template = """You are a chemical safety expert analyzing ingredients in consumer products.
Your task is to classify the ingredient's safety based ONLY on the provided chemical safety database.

CRITICAL INSTRUCTIONS:
- Do NOT use any general knowledge about chemicals
- Do NOT infer or assume safety levels
- If the ingredient is not in the database, respond with UNKNOWN
- Only cite information explicitly present in the database
- Be conservative: when uncertain, rate CAUTION or HARMFUL

CHEMICAL SAFETY DATABASE:
{context}

INGREDIENT TO ANALYZE: {question}

Provide your response in the following JSON format:
{{
    "ingredient_name": "string - exact normalized ingredient name from database or question",
    "safety_rating": "SAFE|CAUTION|HARMFUL|UNKNOWN",
    "reasoning": "string - detailed explanation citing ONLY database sources",
    "hazards": ["list of hazards explicitly mentioned in database"],
    "sources": ["list of exact source citations from database"],
    "confidence_score": 0.0-1.0
}}

VALIDATION RULES:
1. Only return valid JSON, no markdown or additional text
2. Every claim must be traceable to database content
3. If database is silent on safety, say UNKNOWN
4. List only hazards explicitly mentioned in retrieved data
5. Cite exact source names/references from database
6. confidence_score reflects how well database answers the question (not general knowledge)
7. When in doubt between ratings, choose the more conservative (e.g., CAUTION over SAFE)"""
        
        self.prompt = PromptTemplate(
            template=self.safety_prompt_template,
            input_variables=["context", "question"]
        )
    
    def retrieve_context(self, ingredient: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant chemical safety information.
        
        Args:
            ingredient: Ingredient name to search for
            top_k: Number of results to retrieve
            
        Returns:
            List of relevant chemical records with similarity scores
        """
        return self.kb.search(ingredient, top_k=top_k)
    
    def format_context(self, retrieved_docs: List[Dict]) -> str:
        """Format retrieved documents for the LLM prompt.
        
        Args:
            retrieved_docs: List of retrieved chemical records
            
        Returns:
            Formatted context string
        """
        if not retrieved_docs:
            return "No relevant chemical data found in knowledge base."
        
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            part = f"""
Record {i}:
- Chemical Name: {doc.get('name', 'Unknown')}
- CAS Number: {doc.get('cas_number', 'N/A')}
- Safety Rating: {doc.get('safety_rating', 'UNKNOWN')}
- Hazards: {doc.get('hazards', 'None identified')}
- Sources: {doc.get('sources', 'Unknown')}
- Similarity Score: {doc.get('similarity_score', 0):.2%}
- Full Document: {doc.get('document', '')}
"""
            context_parts.append(part)
        
        return "\n".join(context_parts)
    
    def analyze_ingredient(self, ingredient: str, top_k: int = 5) -> Dict:
        """Analyze a single ingredient for safety.
        
        Args:
            ingredient: Ingredient name to analyze
            top_k: Number of retrieved documents to use
            
        Returns:
            Dictionary with analysis results and citations
        """
        # Retrieve relevant context from knowledge base
        retrieved_docs = self.retrieve_context(ingredient, top_k=top_k)
        context = self.format_context(retrieved_docs)
        
        # Prepare the full prompt
        full_prompt = self.safety_prompt_template.format(
            context=context,
            question=f"Analyze the safety of this ingredient: {ingredient}"
        )
        
        # Generate response using LLM
        try:
            if self.llm:
                response = self.llm.invoke(full_prompt)
                if isinstance(response, dict):
                    response_text = response
                elif hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)
            else:
                # Fallback for when LLM is not initialized
                response_text = self._generate_response_with_fallback(ingredient, retrieved_docs)
        except Exception as e:
            response_text = self._generate_response_with_fallback(ingredient, retrieved_docs)
        
        # Parse the response
        try:
            # Check if response_text is already a dict (from fallback or direct response)
            if isinstance(response_text, dict):
                analysis = response_text
            else:
                # String response - convert to dict
                response_str = str(response_text).strip() if response_text else ""
                if response_str.startswith("```json"):
                    response_str = response_str[7:]
                if response_str.startswith("```"):
                    response_str = response_str[3:]
                if response_str.endswith("```"):
                    response_str = response_str[:-3]
                
                analysis = json.loads(response_str.strip())
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            # Fallback if JSON parsing fails
            analysis = self._generate_response_with_fallback(ingredient, retrieved_docs)
        
        # Add retrieved docs as evidence
        analysis['evidence'] = retrieved_docs
        analysis['retrieval_used'] = len(retrieved_docs) > 0
        
        return analysis
    
    def _generate_response_with_fallback(self, ingredient: str, retrieved_docs: List[Dict]) -> Dict:
        """Generate response when LLM is unavailable.
        
        Args:
            ingredient: Ingredient name
            retrieved_docs: Retrieved chemical documents
            
        Returns:
            Fallback analysis dictionary
        """
        if retrieved_docs:
            top_doc = retrieved_docs[0]
            return {
                "ingredient_name": top_doc.get('name', ingredient),
                "safety_rating": top_doc.get('safety_rating', 'UNKNOWN'),
                "reasoning": f"Based on knowledge base match: {top_doc.get('document', 'No details available')}",
                "hazards": top_doc.get('hazards', '').split(';'),
                "sources": top_doc.get('sources', 'Unknown').split(','),
                "confidence_score": top_doc.get('similarity_score', 0)
            }
        else:
            return {
                "ingredient_name": ingredient,
                "safety_rating": "UNKNOWN",
                "reasoning": "No information found in knowledge base. Please research further or consult product documentation.",
                "hazards": [],
                "sources": [],
                "confidence_score": 0.0
            }
    
    def analyze_product_ingredients(self, ingredients: List[str]) -> Dict:
        """Analyze multiple ingredients from a product.
        
        Args:
            ingredients: List of ingredient names
            
        Returns:
            Dictionary with comprehensive product safety analysis
        """
        analyses = []
        safety_counts = {"SAFE": 0, "CAUTION": 0, "HARMFUL": 0, "UNKNOWN": 0}
        
        for ingredient in ingredients:
            analysis = self.analyze_ingredient(ingredient)
            analyses.append(analysis)
            safety_counts[analysis.get('safety_rating', 'UNKNOWN')] += 1
        
        # Calculate overall safety score (0-100)
        total = len(ingredients)
        if total > 0:
            overall_score = (
                (safety_counts["SAFE"] * 100) +
                (safety_counts["CAUTION"] * 60) +
                (safety_counts["HARMFUL"] * 0) +
                (safety_counts["UNKNOWN"] * 40)
            ) / (total * 100) * 100
        else:
            overall_score = 0
        
        # Determine overall rating
        if safety_counts["HARMFUL"] > 0:
            overall_rating = "HARMFUL"
        elif safety_counts["CAUTION"] > 0:
            overall_rating = "CAUTION"
        elif safety_counts["UNKNOWN"] > 0:
            overall_rating = "CAUTION"
        else:
            overall_rating = "SAFE"
        
        return {
            "overall_rating": overall_rating,
            "overall_score": round(overall_score, 1),
            "ingredient_count": total,
            "safety_summary": safety_counts,
            "ingredients": analyses
        }
