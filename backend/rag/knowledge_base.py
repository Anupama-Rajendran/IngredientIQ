"""Knowledge base ingestion and management for RAG."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
import os
from pathlib import Path


class ChemicalKnowledgeBase:
    """Manages the chemical safety knowledge base using ChromaDB."""
    
    def __init__(self, db_path: str = "./data/chroma"):
        """Initialize the knowledge base.
        
        Args:
            db_path: Path to ChromaDB storage directory
        """
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB
        chroma_settings = ChromaSettings(
            is_persistent=True,
            persist_directory=db_path,
            anonymized_telemetry=False
        )
        self.client = chromadb.Client(chroma_settings)
        self.collection = self.client.get_or_create_collection(
            name="chemical_safety",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chemicals(self, chemicals: List[Dict]) -> None:
        """Add chemicals to the knowledge base.
        
        Args:
            chemicals: List of chemical dictionaries with:
                - name (str): Chemical name
                - cas_number (str): CAS registry number
                - safety_rating (str): SAFE, CAUTION, HARMFUL, UNKNOWN
                - hazards (str): List of hazards
                - sources (str): Citation sources
                - description (str): Full chemical description
        """
        ids = []
        documents = []
        metadatas = []
        
        for chem in chemicals:
            chem_id = f"chem_{chem.get('cas_number', chem['name'].replace(' ', '_'))}"
            ids.append(chem_id)
            
            # Create a searchable document combining all text fields
            doc_text = f"""
            Chemical: {chem['name']}
            CAS Number: {chem.get('cas_number', 'N/A')}
            Safety Rating: {chem['safety_rating']}
            Hazards: {chem.get('hazards', 'None identified')}
            Sources: {chem.get('sources', 'Unknown')}
            Description: {chem.get('description', '')}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "name": chem['name'],
                "cas_number": chem.get('cas_number', 'N/A'),
                "safety_rating": chem['safety_rating'],
                "hazards": chem.get('hazards', ''),
                "sources": chem.get('sources', ''),
            })
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for chemicals in the knowledge base.
        
        Args:
            query: Chemical name or description to search for
            top_k: Number of top results to return
            
        Returns:
            List of matching chemical records with scores
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        if not results['documents'] or not results['documents'][0]:
            return []
        
        formatted_results = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            formatted_results.append({
                'name': metadata.get('name', 'Unknown'),
                'cas_number': metadata.get('cas_number', 'N/A'),
                'safety_rating': metadata.get('safety_rating', 'UNKNOWN'),
                'hazards': metadata.get('hazards', ''),
                'sources': metadata.get('sources', ''),
                'document': doc,
                'similarity_score': 1 - distance,  # Convert distance to similarity
            })
        
        return formatted_results
    
    def get_chemical_by_name(self, name: str) -> Optional[Dict]:
        """Get a specific chemical by name.
        
        Args:
            name: Chemical name to look up
            
        Returns:
            Chemical record if found, None otherwise
        """
        results = self.search(name, top_k=1)
        if results and results[0]['similarity_score'] > 0.8:
            return results[0]
        return None
    
    def count_chemicals(self) -> int:
        """Count total chemicals in the knowledge base."""
        return self.collection.count()
    
    def clear(self) -> None:
        """Clear the entire knowledge base."""
        self.client.delete_collection(name="chemical_safety")
        self.collection = self.client.get_or_create_collection(
            name="chemical_safety",
            metadata={"hnsw:space": "cosine"}
        )


def seed_knowledge_base(kb: ChemicalKnowledgeBase) -> None:
    """Seed the knowledge base with initial chemical data.
    
    Args:
        kb: ChemicalKnowledgeBase instance
    """
    initial_chemicals = [
        {
            "name": "Sodium Lauryl Sulfate",
            "cas_number": "151-21-3",
            "safety_rating": "CAUTION",
            "hazards": "Skin irritation at high concentrations; potential scalp irritation",
            "sources": "EWG Skin Deep, PubChem",
            "description": "Common surfactant in shampoos and soaps. Generally recognized as safe in cosmetic concentrations but can cause irritation with prolonged exposure to high concentrations."
        },
        {
            "name": "Benzene",
            "cas_number": "71-43-2",
            "safety_rating": "HARMFUL",
            "hazards": "Carcinogenic (Group 1); bone marrow toxicity; leukemia risk",
            "sources": "IARC Monographs, OSHA, CDC",
            "description": "Volatile organic compound. Classified as a known human carcinogen by IARC Group 1. Associated with leukemia and other blood cancers."
        },
        {
            "name": "Glycerin",
            "cas_number": "56-81-5",
            "safety_rating": "SAFE",
            "hazards": "None identified at normal concentrations",
            "sources": "FDA GRAS List, PubChem",
            "description": "Humectant widely used in cosmetics and food. Generally recognized as safe (GRAS) by FDA. Non-toxic at normal usage levels."
        },
        {
            "name": "Parabens (Methylparaben)",
            "cas_number": "99-76-3",
            "safety_rating": "CAUTION",
            "hazards": "Weak estrogenic activity; potential endocrine disruption at very high doses; skin reaction in sensitive individuals",
            "sources": "EWG Skin Deep, European Commission",
            "description": "Preservative used in many cosmetics and pharmaceuticals. FDA considers it safe at cosmetic levels, but some studies suggest weak estrogenic properties at high doses."
        },
        {
            "name": "Titanium Dioxide",
            "cas_number": "13463-67-7",
            "safety_rating": "CAUTION",
            "hazards": "Inhalation concerns with nano-particles; potential lung inflammation; possible photocatalytic activity",
            "sources": "PubChem, IARC",
            "description": "Widely used UV filter in sunscreens and cosmetics. Safe for topical use on healthy skin, but inhalation of nano-particles may pose respiratory risks."
        },
        {
            "name": "Triclosan",
            "cas_number": "3380-34-5",
            "safety_rating": "HARMFUL",
            "hazards": "Endocrine disruption; antibiotic resistance promotion; bioaccumulation; potential thyroid effects",
            "sources": "FDA, EWG Skin Deep, Environmental Protection Agency",
            "description": "Antimicrobial agent formerly in consumer products. FDA banned it from consumer hand soaps in 2016 due to endocrine disruption concerns and lack of efficacy."
        },
        {
            "name": "Vitamin C (Ascorbic Acid)",
            "cas_number": "50-81-7",
            "safety_rating": "SAFE",
            "hazards": "None identified at cosmetic concentrations",
            "sources": "FDA GRAS List, PubChem",
            "description": "Antioxidant and skin brightening ingredient. Well-established safety record. Essential nutrient naturally found in many foods."
        },
        {
            "name": "Phthalates (Diethyl Phthalate)",
            "cas_number": "84-66-2",
            "safety_rating": "HARMFUL",
            "hazards": "Endocrine disruption; reproductive toxicity; developmental toxicity; bioaccumulation",
            "sources": "EWG, Environmental Protection Agency, CPSC",
            "description": "Plasticizer used in fragrances and cosmetics. Classified as harmful to reproductive system. Banned or restricted in cosmetics in EU and Canada."
        },
        {
            "name": "Aloe Vera Extract",
            "cas_number": "84603-48-5",
            "safety_rating": "SAFE",
            "hazards": "Potential laxative effect if ingested in large quantities; rare allergies",
            "sources": "PubChem, Traditional medicine databases",
            "description": "Natural extract from aloe plant. Widely used in cosmetics and topical products. Safe for external use; long history of traditional use."
        },
        {
            "name": "Formaldehyde",
            "cas_number": "50-00-0",
            "safety_rating": "HARMFUL",
            "hazards": "Carcinogenic (Group 1); respiratory irritation; allergic contact dermatitis; off-gassing in nail products",
            "sources": "IARC, OSHA, EWG",
            "description": "Volatile chemical used as preservative in some cosmetics. Classified as Group 1 carcinogen by IARC. Restricted in many countries."
        }
    ]
    
    kb.add_chemicals(initial_chemicals)
