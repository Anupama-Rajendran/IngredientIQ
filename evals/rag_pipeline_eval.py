"""Evaluation RAG pipeline for RAGAS metrics assessment.

This pipeline is optimized for RAGAS evaluation with:
- KB-only mode (no external APIs for consistency)
- Detailed logging and metrics tracking
- Tunable parameters for testing
"""
from typing import List, Dict, Optional
import sys
import logging
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.rag.knowledge_base import ChemicalKnowledgeBase
from backend.rag.data_loaders import FDAGRASLoader, EWGLoader, IARCLoader
import json

logger = logging.getLogger(__name__)


class IngredientSafetyRAGEval:
    """Evaluation RAG pipeline optimized for RAGAS metrics.
    
    Features:
    - KB-only mode (no external APIs) for consistent, repeatable evaluation
    - Detailed logging for debugging retrieval quality
    - Metrics tracking (retrieval counts, similarity scores, etc.)
    - Tunable parameters (top_k, threshold) for testing different configurations
    """
    
    def __init__(self, kb: ChemicalKnowledgeBase, llm=None, mcp_server=None,
                 top_k: int = 5, similarity_threshold: float = 0.0):
        """Initialize the evaluation RAG pipeline.
        
        Args:
            kb: ChemicalKnowledgeBase instance
            llm: Language model to use (defaults to Claude via Anthropic)
            mcp_server: Optional MCP server for tool access
            top_k: Number of documents to retrieve (default 5)
            similarity_threshold: Minimum similarity score threshold (default 0.0)
        """
        self.kb = kb
        self.llm = llm
        self.mcp_server = mcp_server
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # Initialize loaders for static data lookups (no live APIs in eval mode)
        self.fda_loader = FDAGRASLoader()
        self.ewg_loader = EWGLoader()
        self.iarc_loader = IARCLoader()
        
        # Metrics tracking
        self.retrieval_metrics = {}
        
        self.safety_prompt_template = """You are a chemical safety expert. Answer ONLY the specific question asked using the provided database.

CHEMICAL SAFETY DATABASE:
{context}

QUESTION: {question}

ANSWER GUIDELINES:
- Directly answer the specific question with database information only
- Do NOT include general background or extra information
- If you cannot fully answer from the database, state what is unknown
- Be concise but thorough in answering just the question asked
- Always cite your database source

Return ONLY valid JSON:
{{
    "ingredient_name": "ingredient from question",
    "safety_rating": "SAFE|CAUTION|HARMFUL|UNKNOWN",
    "reasoning": "focused answer to the specific question, using only database information",
    "hazards": ["from database"],
    "sources": ["database sources used"],
    "confidence_score": 0.0-1.0
}}"""
        
        logger.info(f"[EVAL] Initialized EvaluationRAG: top_k={top_k}, threshold={similarity_threshold}")
    
    def _lookup_from_static_sources(self, ingredient: str) -> Optional[Dict]:
        """Look up chemical data from static sources (FDA, EWG, IARC).
        
        Note: Does NOT use live PubChem API - only static data for consistency.
        
        Args:
            ingredient: Ingredient/chemical name
            
        Returns:
            Combined chemical data dictionary or None if not found
        """
        sources_data = []
        combined_data = {
            "name": ingredient,
            "safety_ratings": {},
            "hazards": set(),
            "sources": set(),
            "data_source": "static_database"
        }
        
        logger.debug(f"[EVAL] Starting static lookup for '{ingredient}'...")
        
        # 1. Look up in FDA GRAS list
        try:
            fda_chemicals = self.fda_loader.load_gras_list()
            fda_match = self._find_chemical_match(ingredient, fda_chemicals)
            if fda_match:
                sources_data.append(fda_match)
                combined_data["safety_ratings"]["FDA_GRAS"] = fda_match.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("FDA GRAS List")
                if fda_match.get('hazards'):
                    combined_data["hazards"].add(fda_match['hazards'])
                logger.debug(f"[EVAL] Found in FDA: {fda_match.get('name')}")
        except Exception as e:
            logger.debug(f"[EVAL] FDA lookup failed: {e}")
        
        # 2. Look up in EWG Skin Deep
        try:
            ewg_chemicals = self.ewg_loader.load_cosmetic_ingredients()
            ewg_match = self._find_chemical_match(ingredient, ewg_chemicals)
            if ewg_match:
                sources_data.append(ewg_match)
                combined_data["safety_ratings"]["EWG"] = ewg_match.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("EWG Skin Deep")
                if ewg_match.get('hazards'):
                    combined_data["hazards"].add(ewg_match['hazards'])
                logger.debug(f"[EVAL] Found in EWG: {ewg_match.get('name')}")
        except Exception as e:
            logger.debug(f"[EVAL] EWG lookup failed: {e}")
        
        # 3. Look up in IARC carcinogen list
        try:
            iarc_chemicals = self.iarc_loader.load_iarc_carcinogens()
            iarc_match = self._find_chemical_match(ingredient, iarc_chemicals)
            if iarc_match:
                sources_data.append(iarc_match)
                combined_data["safety_ratings"]["IARC"] = iarc_match.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("IARC Carcinogen List")
                if iarc_match.get('hazards'):
                    combined_data["hazards"].add(iarc_match['hazards'])
                logger.debug(f"[EVAL] Found in IARC: {iarc_match.get('name')}")
        except Exception as e:
            logger.debug(f"[EVAL] IARC lookup failed: {e}")
        
        # Return None if nothing found
        if not sources_data:
            logger.debug(f"[EVAL] No static data found for '{ingredient}'")
            return None
        
        # Combine data
        combined_data["hazards"] = "; ".join(sorted(combined_data["hazards"]))
        combined_data["sources"] = ", ".join(sorted(combined_data["sources"]))
        
        # Determine overall rating by authority hierarchy
        if "IARC" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["IARC"]
        elif "EWG" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["EWG"]
        elif "FDA_GRAS" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["FDA_GRAS"]
        else:
            combined_data["safety_rating"] = "UNKNOWN"
        
        combined_data["document"] = f"Static database sources: {combined_data['sources']}"
        combined_data["similarity_score"] = 0.95
        
        logger.debug(f"[EVAL] Static lookup result: {combined_data['safety_rating']}")
        return combined_data
    
    def _find_chemical_match(self, ingredient: str, chemical_list: List[Dict]) -> Optional[Dict]:
        """Find a matching chemical in a list by name (case-insensitive).
        
        Args:
            ingredient: Chemical name to search for
            chemical_list: List of chemical dictionaries
            
        Returns:
            Matching chemical dictionary or None
        """
        ingredient_lower = ingredient.lower().strip()
        for chem in chemical_list:
            chem_name = chem.get('name', '').lower()
            if chem_name == ingredient_lower or ingredient_lower in chem_name or chem_name in ingredient_lower:
                return chem
        return None
    
    def retrieve_context(self, ingredient: str, top_k: int = None) -> List[Dict]:
        """Retrieve relevant chemical safety information from KB.
        
        Args:
            ingredient: Ingredient name to search for
            top_k: Number of results to retrieve (overrides instance top_k if provided)
            
        Returns:
            List of relevant chemical records with similarity scores
        """
        retrieve_k = top_k if top_k is not None else self.top_k
        results = self.kb.search(ingredient, top_k=retrieve_k)
        
        # Filter by similarity threshold
        filtered_results = [r for r in results if r.get('similarity_score', 0) >= self.similarity_threshold]
        
        # Keep at least top result even if below threshold
        if not filtered_results and results:
            filtered_results = [results[0]]
        
        # Log retrieval metrics
        if ingredient not in self.retrieval_metrics:
            self.retrieval_metrics[ingredient] = []
        
        scores = [r.get('similarity_score', 0) for r in filtered_results]
        self.retrieval_metrics[ingredient].append({
            "source": "knowledge_base",
            "retrieved_count": len(filtered_results),
            "avg_similarity": sum(scores) / len(scores) if scores else 0,
            "top_similarity": max(scores) if scores else 0
        })
        
        logger.debug(f"[EVAL] KB Retrieved {len(filtered_results)} docs for '{ingredient}' "
                    f"(avg similarity: {sum(scores) / len(scores) if scores else 0:.3f})")
        
        return filtered_results
    
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
    
    def analyze_ingredient(self, ingredient: str) -> Dict:
        """Analyze a single ingredient for safety using KB-only data.
        
        Args:
            ingredient: Ingredient name to analyze
            
        Returns:
            Dictionary with analysis results and citations
        """
        logger.info(f"[EVAL] Analyzing: {ingredient}")
        
        # Try static sources first
        static_data = self._lookup_from_static_sources(ingredient)
        
        if static_data:
            retrieved_docs = [static_data]
            data_source = "static_database"
        else:
            # Fall back to KB search
            retrieved_docs = self.retrieve_context(ingredient)
            data_source = "knowledge_base"
            
            if not retrieved_docs:
                logger.warning(f"[EVAL] No data found for '{ingredient}'")
                return {
                    "ingredient_name": ingredient,
                    "safety_rating": "UNKNOWN",
                    "reasoning": "No information found in knowledge base or static sources.",
                    "hazards": [],
                    "sources": [],
                    "confidence_score": 0.0,
                    "data_source": "none"
                }
        
        context = self.format_context(retrieved_docs)
        
        # Prepare prompt
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
                response_text = self._generate_response_with_fallback(ingredient, retrieved_docs)
        except Exception as e:
            logger.error(f"[EVAL] LLM error: {e}")
            response_text = self._generate_response_with_fallback(ingredient, retrieved_docs)
        
        # Parse response
        try:
            if isinstance(response_text, dict):
                analysis = response_text
            else:
                response_str = str(response_text).strip() if response_text else ""
                if response_str.startswith("```json"):
                    response_str = response_str[7:]
                if response_str.startswith("```"):
                    response_str = response_str[3:]
                if response_str.endswith("```"):
                    response_str = response_str[:-3]
                
                analysis = json.loads(response_str.strip())
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            logger.error(f"[EVAL] JSON parse error: {e}")
            analysis = self._generate_response_with_fallback(ingredient, retrieved_docs)
        
        # Add metadata
        analysis['evidence'] = retrieved_docs
        analysis['retrieval_used'] = len(retrieved_docs) > 0
        analysis['data_source'] = data_source
        
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
            reasoning = f"Based on database: {top_doc.get('document', '')}"
            if not reasoning or reasoning == "Based on database: ":
                reasoning = f"{top_doc.get('name')} has safety rating {top_doc.get('safety_rating', 'UNKNOWN')} per database."
            return {
                "ingredient_name": top_doc.get('name', ingredient),
                "safety_rating": top_doc.get('safety_rating', 'UNKNOWN'),
                "reasoning": reasoning,
                "hazards": top_doc.get('hazards', '').split(';') if top_doc.get('hazards') else [],
                "sources": top_doc.get('sources', 'Unknown').split(',') if top_doc.get('sources') else [],
                "confidence_score": top_doc.get('similarity_score', 0)
            }
        else:
            return {
                "ingredient_name": ingredient,
                "safety_rating": "UNKNOWN",
                "reasoning": "UNKNOWN - not in database.",
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
        
        # Calculate overall safety score
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
    
    def get_retrieval_metrics(self, ingredient: Optional[str] = None) -> Dict:
        """Get retrieval metrics for debugging.
        
        Args:
            ingredient: Specific ingredient or None for all
            
        Returns:
            Dictionary with retrieval metrics
        """
        if ingredient:
            return self.retrieval_metrics.get(ingredient, [])
        return self.retrieval_metrics
