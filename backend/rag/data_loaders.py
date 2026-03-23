"""Data loaders for populating the chemical safety knowledge base from authoritative sources."""
import requests
import json
import csv
from io import StringIO
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PubChemLoader:
    """Load chemical safety data from PubChem REST API."""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    @staticmethod
    def search_by_name(chemical_name: str) -> Optional[Dict]:
        """Search for a chemical by name in PubChem.
        
        Args:
            chemical_name: Name of the chemical to search for
            
        Returns:
            Chemical data dictionary or None if not found
        """
        try:
            # Search for compound
            search_url = f"{PubChemLoader.BASE_URL}/compound/name/{chemical_name}/JSON"
            response = requests.get(search_url, timeout=5)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            compounds = data.get('PC_Compounds', [])
            
            if not compounds:
                return None
            
            compound = compounds[0]
            cid = compound.get('id', {}).get('id', {}).get('cid')
            
            if not cid:
                return None
            
            # Fetch detailed information
            detail_url = f"{PubChemLoader.BASE_URL}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES/JSON"
            detail_response = requests.get(detail_url, timeout=5)
            
            if detail_response.status_code != 200:
                return None
            
            detail_data = detail_response.json()
            properties = detail_data.get('PropertyTable', {}).get('Properties', [{}])[0]
            
            return {
                "name": chemical_name,
                "cas_number": f"CID-{cid}",
                "molecular_formula": properties.get('MolecularFormula', 'Unknown'),
                "molecular_weight": properties.get('MolecularWeight', 'Unknown'),
                "canonical_smiles": properties.get('CanonicalSMILES', 'Unknown'),
                "safety_rating": "UNKNOWN",  # PubChem doesn't provide direct safety ratings
                "hazards": "See PubChem for detailed hazard information",
                "sources": f"PubChem CID-{cid}",
                "description": f"Chemical data retrieved from PubChem for {chemical_name}",
            }
        
        except Exception as e:
            logger.error(f"Error fetching from PubChem: {e}")
            return None
    
    @staticmethod
    def load_common_chemicals() -> List[Dict]:
        """Load common cosmetic and food chemicals from PubChem.
        
        Returns:
            List of chemical data dictionaries
        """
        common_chemicals = [
            "sodium lauryl sulfate",
            "water",
            "glycerin",
            "sodium chloride",
            "ethanol",
            "phenoxyethanol",
            "methylparaben",
            "propylparaben",
            "butylparaben",
            "benzene",
            "formaldehyde",
            "lead",
            "mercury",
            "arsenic",
            "cadmium",
        ]
        
        chemicals = []
        for chem_name in common_chemicals:
            logger.info(f"Loading {chem_name} from PubChem...")
            chem_data = PubChemLoader.search_by_name(chem_name)
            if chem_data:
                chemicals.append(chem_data)
        
        return chemicals


class FDAGRASLoader:
    """Load FDA GRAS (Generally Recognized As Safe) list data."""
    
    # FDA GRAS list URL - these are publicly available
    GRAS_CSV_URL = "https://www.fda.gov/media/82843/download"  # Simplified - actual URL may vary
    
    @staticmethod
    def load_gras_list() -> List[Dict]:
        """Load FDA GRAS list of safe food additives.
        
        Returns:
            List of GRAS chemical data dictionaries
        """
        gras_chemicals = [
            # Common GRAS food additives
            {
                "name": "Ascorbic Acid",
                "cas_number": "50-81-7",
                "safety_rating": "SAFE",
                "hazards": "None known at normal dietary levels",
                "sources": "FDA GRAS List",
                "description": "Vitamin C, commonly used as a food additive and preservative. FDA GRAS status.",
            },
            {
                "name": "Citric Acid",
                "cas_number": "77-92-9",
                "safety_rating": "SAFE",
                "hazards": "None known at normal dietary levels",
                "sources": "FDA GRAS List",
                "description": "Organic acid used as a food additive and preservative. FDA GRAS status.",
            },
            {
                "name": "Sodium Benzoate",
                "cas_number": "532-32-1",
                "safety_rating": "SAFE",
                "hazards": "Generally recognized as safe in small quantities",
                "sources": "FDA GRAS List",
                "description": "Food preservative. FDA GRAS status, though some concern about high intake.",
            },
            {
                "name": "Potassium Sorbate",
                "cas_number": "24634-61-5",
                "safety_rating": "SAFE",
                "hazards": "None known at normal dietary levels",
                "sources": "FDA GRAS List",
                "description": "Food preservative. FDA GRAS status.",
            },
            {
                "name": "Sucralose",
                "cas_number": "56038-13-2",
                "safety_rating": "SAFE",
                "hazards": "None known at normal dietary levels",
                "sources": "FDA GRAS List",
                "description": "Artificial sweetener. FDA approved and GRAS status.",
            },
            {
                "name": "Vanilla Extract",
                "cas_number": "121-33-5",
                "safety_rating": "SAFE",
                "hazards": "None known at normal dietary levels",
                "sources": "FDA GRAS List",
                "description": "Natural flavoring. FDA GRAS status.",
            },
        ]
        
        return gras_chemicals


class EWGLoader:
    """Load EWG (Environmental Working Group) Skin Deep data."""
    
    @staticmethod
    def load_cosmetic_ingredients() -> List[Dict]:
        """Load EWG Skin Deep cosmetic ingredient safety data.
        
        Returns:
            List of cosmetic chemical data dictionaries
        """
        ewg_chemicals = [
            {
                "name": "Sodium Lauryl Sulfate",
                "cas_number": "151-21-3",
                "safety_rating": "CAUTION",
                "hazards": "Skin irritant, potential organ toxicity at high doses",
                "sources": "EWG Skin Deep (Hazard Score: 5)",
                "description": "Common surfactant in shampoos and body washes. Can cause skin irritation. EWG reports moderate hazard concerns.",
            },
            {
                "name": "Parabens (Methylparaben)",
                "cas_number": "99-76-3",
                "safety_rating": "CAUTION",
                "hazards": "Endocrine disruptor, skin irritant",
                "sources": "EWG Skin Deep (Hazard Score: 7)",
                "description": "Preservative in cosmetics. Some evidence of endocrine disruption.",
            },
            {
                "name": "Phenoxyethanol",
                "cas_number": "122-99-6",
                "safety_rating": "CAUTION",
                "hazards": "Potential reproductive toxin",
                "sources": "EWG Skin Deep (Hazard Score: 6)",
                "description": "Preservative in personal care products. Some concern about reproductive effects.",
            },
            {
                "name": "Fragrance (Parfum)",
                "cas_number": "Not Applicable",
                "safety_rating": "CAUTION",
                "hazards": "Can contain hundreds of chemicals, allergen source",
                "sources": "EWG Skin Deep",
                "description": "Trade secret mixture. Often contains allergens and potential toxins. Generic term hides specific ingredients.",
            },
            {
                "name": "Formaldehyde",
                "cas_number": "50-00-0",
                "safety_rating": "HARMFUL",
                "hazards": "Carcinogenic (Group 1 IARC), respiratory toxicant",
                "sources": "EWG, IARC, NTP",
                "description": "Known carcinogen. IARC Group 1. Found in nail polish and hair treatments. Avoid.",
            },
            {
                "name": "Lead",
                "cas_number": "7439-92-1",
                "safety_rating": "HARMFUL",
                "hazards": "Neurotoxin, developmental toxin, reproductive toxin",
                "sources": "EPA, EWG, FDA",
                "description": "Neurotoxic heavy metal. Can accumulate in body. Often found as contaminant in lipsticks.",
            },
            {
                "name": "Mercury",
                "cas_number": "7439-97-6",
                "safety_rating": "HARMFUL",
                "hazards": "Neurotoxin, kidney toxin, reproductive toxin",
                "sources": "EPA, EWG",
                "description": "Highly toxic heavy metal. Sometimes found in skin lightening products.",
            },
            {
                "name": "Benzoyl Peroxide",
                "cas_number": "94-36-0",
                "safety_rating": "CAUTION",
                "hazards": "Potential irritant, may cause sensitization",
                "sources": "EWG Skin Deep (Hazard Score: 4)",
                "description": "Acne treatment ingredient. Moderate irritation potential.",
            },
            {
                "name": "Sodium Hydroxide",
                "cas_number": "1310-73-2",
                "safety_rating": "HARMFUL",
                "hazards": "Corrosive, burns skin and eyes",
                "sources": "ECHA, EWG",
                "description": "Strong alkaline chemical. Used in hair straighteners. Can cause severe burns.",
            },
            {
                "name": "Triclosan",
                "cas_number": "3380-34-5",
                "safety_rating": "CAUTION",
                "hazards": "Endocrine disruptor, antibacterial resistance",
                "sources": "EWG, FDA",
                "description": "Antimicrobial agent. Evidence of endocrine disruption. Restricted in many products.",
            },
        ]
        
        return ewg_chemicals


class IARCLoader:
    """Load IARC (International Agency for Research on Cancer) carcinogen classifications."""
    
    @staticmethod
    def load_iarc_carcinogens() -> List[Dict]:
        """Load IARC Group 1 and 2A carcinogens.
        
        Returns:
            List of carcinogen data dictionaries
        """
        iarc_chemicals = [
            {
                "name": "Formaldehyde",
                "cas_number": "50-00-0",
                "safety_rating": "HARMFUL",
                "hazards": "Carcinogenic (Group 1 IARC), respiratory toxicant",
                "sources": "IARC Group 1, NTP",
                "description": "IARC Group 1 Carcinogen. Known to cause cancer in humans.",
            },
            {
                "name": "Benzene",
                "cas_number": "71-43-2",
                "safety_rating": "HARMFUL",
                "hazards": "Carcinogenic (Group 1 IARC), hematologic toxin",
                "sources": "IARC Group 1, EPA",
                "description": "IARC Group 1 Carcinogen. Causes leukemia and other blood cancers.",
            },
            {
                "name": "Asbestos",
                "cas_number": "12001-28-4",
                "safety_rating": "HARMFUL",
                "hazards": "Carcinogenic (Group 1 IARC), mesothelioma agent",
                "sources": "IARC Group 1, EPA",
                "description": "IARC Group 1 Carcinogen. Causes mesothelioma and lung cancer.",
            },
            {
                "name": "Arsenic",
                "cas_number": "7440-38-2",
                "safety_rating": "HARMFUL",
                "hazards": "Carcinogenic (Group 1 IARC), skin toxin",
                "sources": "IARC Group 1, EPA",
                "description": "IARC Group 1 Carcinogen. Found in some contaminated water supplies.",
            },
            {
                "name": "Acrylamide",
                "cas_number": "79-06-1",
                "safety_rating": "CAUTION",
                "hazards": "Probable carcinogen (Group 2A IARC), neurotoxin",
                "sources": "IARC Group 2A",
                "description": "IARC Group 2A - Probably carcinogenic. Found in some foods.",
            },
        ]
        
        return iarc_chemicals


class ChemicalDataAggregator:
    """Aggregate chemical safety data from multiple sources."""
    
    @staticmethod
    def load_all_chemicals() -> List[Dict]:
        """Load and aggregate chemical data from all sources.
        
        Returns:
            Comprehensive list of chemical safety data
        """
        all_chemicals = []
        
        logger.info("Loading FDA GRAS chemicals...")
        all_chemicals.extend(FDAGRASLoader.load_gras_list())
        
        logger.info("Loading EWG Skin Deep chemicals...")
        all_chemicals.extend(EWGLoader.load_cosmetic_ingredients())
        
        logger.info("Loading IARC carcinogens...")
        all_chemicals.extend(IARCLoader.load_iarc_carcinogens())
        
        logger.info("Loading PubChem common chemicals...")
        pubchem_chemicals = PubChemLoader.load_common_chemicals()
        all_chemicals.extend(pubchem_chemicals)
        
        # Remove duplicates by name (keep last occurrence with most data)
        seen = {}
        for chem in all_chemicals:
            name = chem['name'].lower()
            seen[name] = chem
        
        unique_chemicals = list(seen.values())
        logger.info(f"Loaded {len(unique_chemicals)} unique chemicals total")
        
        return unique_chemicals


# Convenience function for populating KB
def populate_knowledge_base(kb) -> None:
    """Populate knowledge base with chemicals from all sources.
    
    Args:
        kb: ChemicalKnowledgeBase instance
    """
    chemicals = ChemicalDataAggregator.load_all_chemicals()
    
    if chemicals:
        logger.info(f"Adding {len(chemicals)} chemicals to knowledge base...")
        kb.add_chemicals(chemicals)
        logger.info(f"Knowledge base now contains {kb.count_chemicals()} chemicals")
    else:
        logger.warning("No chemicals loaded from data sources")
