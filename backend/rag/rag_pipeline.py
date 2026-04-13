"""RAG pipeline for ingredient safety analysis."""
from typing import List, Dict, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from .knowledge_base import ChemicalKnowledgeBase
from .data_loaders import PubChemLoader, FDAGRASLoader, EWGLoader, IARCLoader
import json
import requests
import logging

logger = logging.getLogger(__name__)


class IngredientSafetyRAG:
    """RAG pipeline for analyzing ingredient safety with citations."""
    
    def __init__(self, kb: ChemicalKnowledgeBase, llm=None, mcp_server=None):
        """Initialize the RAG pipeline.
        
        Args:
            kb: ChemicalKnowledgeBase instance
            llm: Language model to use (if None, uses Claude via Anthropic)
            mcp_server: Optional MCP server for tool access
        """
        self.kb = kb
        self.llm = llm
        self.mcp_server = mcp_server
        
        # Initialize loaders for multi-source lookup
        self.fda_loader = FDAGRASLoader()
        self.ewg_loader = EWGLoader()
        self.iarc_loader = IARCLoader()
        
        self.safety_prompt_template = """You are a chemical safety expert analyzing ingredients in consumer products.

Based on the chemical safety database information provided below, classify the ingredient and provide reasoning.
The database may include data from multiple sources:
- Local knowledge base (compiled from PubChem, FDA GRAS, EWG, IARC)
- Real-time PubChem API queries (marked as "Live data from PubChem")

CHEMICAL SAFETY DATABASE:
{context}

INGREDIENT TO ANALYZE: {question}

Provide your response in the following JSON format:
{{
    "ingredient_name": "string - normalized ingredient name",
    "safety_rating": "SAFE|CAUTION|HARMFUL|UNKNOWN",
    "reasoning": "string - detailed explanation of the classification",
    "hazards": ["list of identified hazards"],
    "sources": ["list of evidence sources"],
    "confidence_score": 0.0-1.0
}}

Rules:
1. Only return valid JSON, no additional text
2. Base your classification on the database information provided
3. If database shows conflicting information, weight by source authority
4. If database includes live PubChem data, use it to provide a proper safety classification (never say the database lacks data if live data is provided)
5. If no relevant information found, return UNKNOWN only if both KB and live API searches failed
6. Always cite the sources used in classification
7. Be conservative - when in doubt, err toward CAUTION"""
        
        self.prompt = PromptTemplate(
            template=self.safety_prompt_template,
            input_variables=["context", "question"]
        )
    
    def _lookup_from_all_sources(self, ingredient: str) -> Optional[Dict]:
        """Look up chemical data from all available sources (PubChem, FDA, EWG, IARC).
        
        Queries in order: PubChem (live) → FDA GRAS → EWG → IARC
        Combines results from all matching sources.
        
        Args:
            ingredient: Ingredient/chemical name
            
        Returns:
            Combined chemical data dictionary or None if not found in any source
        """
        sources_data = []
        combined_data = {
            "name": ingredient,
            "safety_ratings": {},  # Track ratings from different sources
            "hazards": set(),
            "sources": set(),
            "data_source": "multi-source"
        }
        
        print(f"\n[Multi-Source Lookup] Starting search for '{ingredient}'...")
        
        # 1. Query PubChem live API first
        print(f"[Multi-Source] 1. Querying PubChem live API...")
        try:
            pubchem_data = self._fetch_live_pubchem_data(ingredient)
            if pubchem_data:
                sources_data.append(pubchem_data)
                combined_data["safety_ratings"]["PubChem"] = pubchem_data.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("PubChem (live API)")
                if pubchem_data.get('hazards'):
                    combined_data["hazards"].update(pubchem_data['hazards'].split('; '))
                print(f"[Multi-Source] ✓ Found in PubChem: {pubchem_data.get('name')}")
            else:
                print(f"[Multi-Source] ✗ Not found in PubChem")
        except Exception as e:
            print(f"[Multi-Source] ✗ PubChem query failed: {e}")
        
        # 2. Look up in FDA GRAS list
        print(f"[Multi-Source] 2. Searching FDA GRAS list...")
        try:
            fda_chemicals = self.fda_loader.load_gras_list()
            print(f"[Multi-Source] Loaded {len(fda_chemicals)} chemicals from FDA")
            fda_match = self._find_chemical_match(ingredient, fda_chemicals)
            if fda_match:
                sources_data.append(fda_match)
                combined_data["safety_ratings"]["FDA_GRAS"] = fda_match.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("FDA GRAS List")
                if fda_match.get('hazards'):
                    combined_data["hazards"].add(fda_match['hazards'])
                print(f"[Multi-Source] ✓ Found in FDA GRAS: {fda_match.get('name')}")
            else:
                print(f"[Multi-Source] ✗ Not found in FDA GRAS")
        except Exception as e:
            print(f"[Multi-Source] ✗ FDA query failed: {e}")
        
        # 3. Look up in EWG Skin Deep
        print(f"[Multi-Source] 3. Searching EWG Skin Deep...")
        try:
            ewg_chemicals = self.ewg_loader.load_cosmetic_ingredients()
            print(f"[Multi-Source] Loaded {len(ewg_chemicals)} chemicals from EWG")
            ewg_match = self._find_chemical_match(ingredient, ewg_chemicals)
            if ewg_match:
                sources_data.append(ewg_match)
                combined_data["safety_ratings"]["EWG"] = ewg_match.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("EWG Skin Deep")
                if ewg_match.get('hazards'):
                    combined_data["hazards"].add(ewg_match['hazards'])
                print(f"[Multi-Source] ✓ Found in EWG: {ewg_match.get('name')}")
            else:
                print(f"[Multi-Source] ✗ Not found in EWG")
        except Exception as e:
            print(f"[Multi-Source] ✗ EWG query failed: {e}")
        
        # 4. Look up in IARC carcinogen list
        print(f"[Multi-Source] 4. Searching IARC carcinogen list...")
        try:
            iarc_chemicals = self.iarc_loader.load_iarc_carcinogens()
            print(f"[Multi-Source] Loaded {len(iarc_chemicals)} chemicals from IARC")
            iarc_match = self._find_chemical_match(ingredient, iarc_chemicals)
            if iarc_match:
                sources_data.append(iarc_match)
                combined_data["safety_ratings"]["IARC"] = iarc_match.get('safety_rating', 'UNKNOWN')
                combined_data["sources"].add("IARC Carcinogen List")
                if iarc_match.get('hazards'):
                    combined_data["hazards"].add(iarc_match['hazards'])
                print(f"[Multi-Source] ✓ Found in IARC: {iarc_match.get('name')}")
            else:
                print(f"[Multi-Source] ✗ Not found in IARC")
        except Exception as e:
            print(f"[Multi-Source] ✗ IARC query failed: {e}")
        
        # If no sources found, return None
        if not sources_data:
            print(f"[Multi-Source] ✗ No data found in ANY source for '{ingredient}'")
            return None
        
        # Combine data from all sources
        combined_data["hazards"] = "; ".join(sorted(combined_data["hazards"]))
        combined_data["sources"] = ", ".join(sorted(combined_data["sources"]))
        
        # Determine overall safety rating based on authority hierarchy
        if "IARC" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["IARC"]  # IARC most authoritative for carcinogens
        elif "EWG" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["EWG"]
        elif "PubChem" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["PubChem"]
        elif "FDA_GRAS" in combined_data["safety_ratings"]:
            combined_data["safety_rating"] = combined_data["safety_ratings"]["FDA_GRAS"]
        else:
            combined_data["safety_rating"] = "UNKNOWN"
        
        combined_data["document"] = f"Multi-source data: {combined_data['sources']}"
        combined_data["similarity_score"] = 0.95
        
        print(f"[Multi-Source] ✓ Completed search for '{ingredient}': Rating={combined_data['safety_rating']}, Sources={len(sources_data)}, All Sources: {combined_data['sources']}")
        return combined_data
    
    def _find_chemical_match(self, ingredient: str, chemical_list: List[Dict]) -> Optional[Dict]:
        """Find a matching chemical in a list by name (case-insensitive fuzzy match).
        
        Args:
            ingredient: Chemical name to search for
            chemical_list: List of chemical dictionaries
            
        Returns:
            Matching chemical dictionary or None
        """
        ingredient_lower = ingredient.lower().strip()
        for chem in chemical_list:
            chem_name = chem.get('name', '').lower()
            # Exact match or partial match
            if chem_name == ingredient_lower or ingredient_lower in chem_name or chem_name in ingredient_lower:
                return chem
        return None
    
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
        # Priority 1: Try multi-source lookup (PubChem + FDA + EWG + IARC)
        logger.info(f"Analyzing ingredient: {ingredient}")
        multi_source_data = self._lookup_from_all_sources(ingredient)
        
        if multi_source_data:
            # Use multi-source data
            retrieved_docs = [multi_source_data]
            data_source = "live_databases"
            logger.info(f"Using multi-source data for '{ingredient}'")
        else:
            # Fallback to static KB
            logger.info(f"No multi-source data found, falling back to knowledge base...")
            retrieved_docs = self.retrieve_context(ingredient, top_k=top_k)
            data_source = "knowledge_base"
            
            if not retrieved_docs:
                # If KB also empty, return UNKNOWN
                logger.warning(f"No data found for '{ingredient}' in any source")
                return {
                    "ingredient_name": ingredient,
                    "safety_rating": "UNKNOWN",
                    "reasoning": "No information found in any source (PubChem, FDA, EWG, IARC, or local knowledge base). Please research further or consult product documentation.",
                    "hazards": [],
                    "sources": [],
                    "confidence_score": 0.0,
                    "data_source": "none"
                }
        
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
            logger.error(f"LLM analysis error: {e}")
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
            logger.error(f"JSON parsing error: {e}")
            # Fallback if JSON parsing fails
            analysis = self._generate_response_with_fallback(ingredient, retrieved_docs)
        
        # Add retrieved docs as evidence
        analysis['evidence'] = retrieved_docs
        analysis['retrieval_used'] = len(retrieved_docs) > 0
        analysis['data_source'] = data_source
        
        return analysis
    
    def _fetch_live_pubchem_data(self, ingredient: str) -> Optional[Dict]:
        """Fetch live chemical data from PubChem API.

        Args:
            ingredient: Ingredient name to search for

        Returns:
            Dictionary with PubChem data or None if not found
        """
        try:
            # Search PubChem for the compound using correct PUG REST URL
            from config import settings as cfg
            search_url = f"{cfg.PUBCHEM_API}/compound/name/{ingredient}/JSON"

            search_response = requests.get(search_url, timeout=5)
            if search_response.status_code != 200:
                logger.warning(f"PubChem search failed for '{ingredient}': status {search_response.status_code}")
                return None

            search_data = search_response.json()
            # PubChem PUG REST returns 'PC_Compounds', not 'compound'
            if "PC_Compounds" not in search_data or not search_data["PC_Compounds"]:
                logger.info(f"No PubChem results found for '{ingredient}'")
                return None

            # Get the first matching compound — CID is nested at id.id.cid
            compound = search_data["PC_Compounds"][0]
            cid = compound.get("id", {}).get("id", {}).get("cid")

            # Extract IUPAC name from props array
            compound_name = ingredient
            for prop in compound.get("props", []):
                if prop.get("urn", {}).get("label") == "IUPAC Name" and prop.get("urn", {}).get("name") == "Preferred":
                    compound_name = prop.get("value", {}).get("sval", ingredient)
                    break
            
            # Fetch GHS hazard data from PubChem safety annotations
            # HazardSummary is not a valid PUG property; use the safety/GHS annotations endpoint instead
            hazards = []
            if cid:
                ghs_url = f"{cfg.PUBCHEM_API}/compound/cid/{cid}/property/IUPACName,MolecularFormula/JSON"
                ghs_annotations_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS+Classification"
                try:
                    ghs_response = requests.get(ghs_annotations_url, timeout=5)
                    if ghs_response.status_code == 200:
                        ghs_data = ghs_response.json()
                        # Walk the PubChem annotations tree for GHS hazard statements
                        sections = ghs_data.get("Record", {}).get("Section", [])
                        for section in sections:
                            for subsection in section.get("Section", []):
                                for info in subsection.get("Information", []):
                                    for val in info.get("Value", {}).get("StringWithMarkup", []):
                                        text = val.get("String", "")
                                        if text.startswith("H") and len(text) > 3:
                                            hazards.append(text)
                except Exception:
                    pass  # GHS fetch is best-effort; carry on without it
            
            # Assume moderate safety unless severe hazards found
            safety_rating = "SAFE"
            if any(h in ["Acute Toxicity"] for h in hazards):
                safety_rating = "HARMFUL"
            elif hazards:
                safety_rating = "CAUTION"
            
            # Format as KB document
            pubchem_doc = {
                "name": compound_name,
                "cas_number": "N/A",
                "safety_rating": safety_rating,
                "hazards": "; ".join(hazards) if hazards else "No significant hazards identified",
                "sources": f"PubChem (CID: {cid})",
                "similarity_score": 0.95,
                "document": f"Live data from PubChem for {compound_name}. CID: {cid}. This ingredient was not found in the local knowledge base but was retrieved from PubChem API.",
                "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
            }
            
            logger.info(f"Successfully fetched PubChem data for '{ingredient}': {compound_name}")
            return pubchem_doc
            
        except requests.exceptions.Timeout:
            logger.warning(f"PubChem API timeout for '{ingredient}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"PubChem API error for '{ingredient}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching PubChem data for '{ingredient}': {e}")
            return None
    
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