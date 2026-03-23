"""Knowledge base ingestion and management for RAG."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
import os
from pathlib import Path
import uuid


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
            # Use chemical name as base for ID, with UUID suffix to ensure uniqueness
            base_id = chem['name'].replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').lower()
            unique_id = f"chem_{base_id}_{str(uuid.uuid4())[:8]}"
            ids.append(unique_id)
            
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
    """Seed the knowledge base with comprehensive chemical safety data.
    
    Includes 40+ chemicals commonly found in skincare, cosmetics, and personal care products.
    Args:
        kb: ChemicalKnowledgeBase instance
    """
    initial_chemicals = [
        # Core ingredients (original 10, enhanced)
        {
            "name": "Sodium Lauryl Sulfate (SLS)",
            "cas_number": "151-21-3",
            "safety_rating": "CAUTION",
            "hazards": "Skin irritation at concentrations >2%; scalp irritation with prolonged use; eye irritation; disrupts skin barrier; can enhance penetration of other chemicals",
            "sources": "EWG Skin Deep, PubChem, Cosmetics Ingredient Review (CIR), International Journal of Toxicology",
            "description": "Anionic surfactant commonly used in shampoos, body washes, and cleansers at 1-3% concentration. Effective at removing oils and dirt but highly irritating at elevated levels. FDA allows use but recommends limiting to < 1% for sensitive skin applications. European Commission permits in rinse-off products only."
        },
        {
            "name": "Benzene",
            "cas_number": "71-43-2",
            "safety_rating": "HARMFUL",
            "hazards": "Group 1 carcinogen; bone marrow toxicity; aplastic anemia; leukemia; acute exposure causes CNS effects; chronic exposure linked to hematotoxicity",
            "sources": "IARC Group 1 Monographs, OSHA, CDC, NTP, WHO",
            "description": "Volatile aromatic hydrocarbon. Banned or severely restricted in cosmetics globally. Found in contaminated products or as solvent impurity. No safe threshold for human exposure. Acute exposure causes dizziness, headache; chronic exposure increases leukemia risk."
        },
        {
            "name": "Glycerin",
            "cas_number": "56-81-5",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations (typically 3-20%); rare contact dermatitis; may cause osmotic diarrhea if ingested in excessive amounts",
            "sources": "FDA GRAS List, European Union Cosmetics Directive, Cosmetic Ingredient Review",
            "description": "Polyhydric alcohol and humectant. GRAS by FDA. Used in lotions, moisturizers, and serums at 3-20% concentration. Hygroscopic - draws moisture from environment into skin. No reproductive, developmental, or systemic toxicity. Considered one of safest cosmetic ingredients."
        },
        {
            "name": "Parabens (Methylparaben)",
            "cas_number": "99-76-3",
            "safety_rating": "CAUTION",
            "hazards": "Weak estrogenic activity in vitro; potential endocrine disruption at high doses; dermal penetration concerns with damaged skin barrier; up to 0.4% may bioaccumulate",
            "sources": "EWG Skin Deep, European Commission, FDA Safety Review, Cosmetic Ingredient Review, Environmental Health Perspectives",
            "description": "Preservative in 50-80% of personal care products. Used at 0.1-0.5% in rinse-off products and 0.8-1% in leave-on products. FDA rates as safe, but EU limits to 0.4% methylparaben. Some studies show estrogenic activity only at very high concentrations well above cosmetic use levels."
        },
        {
            "name": "Titanium Dioxide",
            "cas_number": "13463-67-7",
            "safety_rating": "CAUTION",
            "hazards": "Inhalation risk of nano-particles in powders; potential lung inflammation and oxidative stress; photocatalytic ROS generation; nanoparticles may penetrate skin if barrier impaired",
            "sources": "IARC, PubChem, Safety Review - Cosmetic Ingredient Review, Environmental Health Perspectives",
            "description": "White pigment and UV filter in sunscreens and mineral cosmetics. Generally safe for topical use on intact skin (forms barrier preventing penetration). Nano-sized particles (<100 nm) pose inhalation risks in powder form. Non-nano form safe; occupational exposure during manufacturing is primary concern."
        },
        {
            "name": "Triclosan",
            "cas_number": "3380-34-5",
            "safety_rating": "HARMFUL",
            "hazards": "Endocrine disruption (weak thyroid hormone activity); promotes antibiotic resistance; bioaccumulates in body and environment; crosses placental barrier; linked to immune suppression",
            "sources": "FDA Ban 2016, Environmental Protection Agency, Endocrine Society, Nature Microbiology",
            "description": "Antibacterial agent formerly in consumer hand soaps, toothpaste, and cosmetics. FDA banned from OTC hand soaps in 2016 due to lack of efficacy and endocrine concerns. Still allowed in some products. Bioaccumulates in fatty tissues and breast milk. No proven advantage over soap and water."
        },
        {
            "name": "Vitamin C (Ascorbic Acid)",
            "cas_number": "50-81-7",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations (5-20%); high pH solutions may cause irritation; oxidizes quickly in air and water requiring stabilization",
            "sources": "FDA GRAS List, PubChem, Cosmetic Ingredient Review, Journal of Clinical and Aesthetic Dermatology",
            "description": "Potent antioxidant and collagen booster in serums at 10-20% concentration. Well-tolerated. Essential nutrient naturally abundant in citrus fruits and vegetables. Effective for brightening, anti-aging, and reducing hyperpigmentation. Stability challenge requires proper formulation."
        },
        {
            "name": "Phthalates (Diethyl Phthalate / DBP)",
            "cas_number": "84-66-2",
            "safety_rating": "HARMFUL",
            "hazards": "Endocrine disruptor; reproductive toxicity (reduced sperm count, testicular effects); developmental toxicity; bioaccumulation; fetal exposure linked to developmental issues",
            "sources": "EWG, EPA, CPSC, EU Ban 2008, CDC Biomonitoring Program, Reproductive Toxicology",
            "description": "Plasticizer used historically in nail polish and fragrances. Banned in EU cosmetics since 2008. Restricted in consumer products in Canada and California. Found in fragrance products due to loopholes in fragrance ingredient listing. Major endocrine disruptor of concern."
        },
        {
            "name": "Aloe Vera Leaf Extract",
            "cas_number": "84603-48-5",
            "safety_rating": "SAFE",
            "hazards": "Rare contact sensitization (0.1% incidence); latex-derived products may cause laxative effect if ingested; allergic reactions in sensitive individuals",
            "sources": "PubChem, Traditional medicine, Phytotherapy Research, Journal of Alternative and Complementary Medicine",
            "description": "Natural extract from aloe plant (Aloe barbadensis). Used in moisturizers, serums, and after-sun products at 1-10% concentration. Rich in polysaccharides, compounds with proven healing and anti-inflammatory properties. Safe for topical use; excellent soothing ingredient for sensitive and irritated skin."
        },
        {
            "name": "Formaldehyde",
            "cas_number": "50-00-0",
            "safety_rating": "HARMFUL",
            "hazards": "Group 1 carcinogen; respiratory irritation and sensitization; allergic contact dermatitis (1-2% of population); nasal and throat cancers linked to occupational exposure",
            "sources": "IARC Group 1, OSHA, EWG, FDA Restrictions, Toxicology Letters",
            "description": "Potent preservative and disinfectant. Listed as known human carcinogen by IARC. Banned in EU cosmetics since 2003. In US, allowed only in nail products at low levels. Off-gassing from nail polish and keratin treatments poses inhalation risk. Formaldehyde releasers (DMH, DMDM hydantoin) also restricted."
        },
        # Additional Sunscreen and UV Protection Ingredients
        {
            "name": "Zinc Oxide",
            "cas_number": "1314-13-2",
            "safety_rating": "SAFE",
            "hazards": "None identified in topical form; nano-particles inhalation risk if airborne; non-systemic absorption",
            "sources": "FDA GRAS, Cosmetic Ingredient Review, Scientific Committee on Consumer Safety (SCCS)",
            "description": "Physical UV blocker forming protective mineral barrier. Used in sunscreens and powder makeup at 2-20%. Non-nano form safe on intact skin with no systemic absorption. Broad-spectrum UVA and UVB protection. Preferred for sensitive and baby skin. Safe alternative to chemical filters."
        },
        {
            "name": "Octinoxate (Octyl Methoxycinnamate)",
            "cas_number": "6109-58-0",
            "safety_rating": "CAUTION",
            "hazards": "Weak estrogenic activity; potential skin penetration and systemic absorption (up to 0.5%); phototoxicity risk; photoallergic dermatitis in sensitive individuals",
            "sources": "FDA Sunscreen Rule Review, Environmental Health Perspectives, Archives of Toxicology",
            "description": "UVB filter historically used in sunscreens at 2-7.5%. Weak endocrine disruptor with quantifiable systemic absorption. FDA requesting additional safety data. EU permits at 10%. Causes photosensitization in some individuals. Being phased out due to environmental and safety concerns."
        },
        {
            "name": "Avobenzone (Butyl Methoxydibenzoylmethane)",
            "cas_number": "70356-09-1",
            "safety_rating": "CAUTION",
            "hazards": "UVA filter instability in sunlight; generates free radicals under UV; systemic absorption possible (0.3%); photodegradation products may cause irritation",
            "sources": "FDA Sunscreen Rule, Photochemistry and Photobiology, Regulatory Toxicology and Pharmacology",
            "description": "UVA filter in over 70% of sunscreens at 2-3%. Absorbs longer-wavelength UVA rays but degrades quickly. Requires stabilizing agents (octocrylene, dimerization products). Generates reactive oxygen species when exposed to UV. Systemic absorption confirmed but no adverse effects at cosmetic use levels."
        },
        {
            "name": "Oxybenzone (Benzophenone-3)",
            "cas_number": "131-57-7",
            "safety_rating": "HARMFUL",
            "hazards": "Endocrine disruption (estrogenic and androgenic activity); potential developmental/reproductive toxicity; systemic absorption 1-2%; accumulation in body tissues",
            "sources": "EPA Report, Reproductive Toxicology, Environmental Health Perspectives, Hawaii 2021 Ban",
            "description": "Chemical UV filter used at 1-6% in sunscreens. Significant systemic absorption and bioaccumulation. Endocrine disruptor with estrogenic effects. Banned in Hawaii 2021 for coral reef protection. Phased out in many countries. Readily absorbed through skin."
        },
        {
            "name": "Homosalate",
            "cas_number": "118-56-9",
            "safety_rating": "CAUTION",
            "hazards": "Endocrine disruption potential; systemic absorption 0.1-1%; weak estrogenic activity; photodegradation products unknown",
            "sources": "FDA Sunscreen Rule Review, Endocrine Society, Journal of Applied Toxicology",
            "description": "UVB filter used at 1-15% in sunscreens. Readily absorbed through skin with measurable plasma concentrations after topical application. Limited safety data for long-term use. FDA requesting additional studies on reproductive/developmental effects."
        },
        # Moisturizing and Skin-Hydrating Ingredients
        {
            "name": "Hyaluronic Acid",
            "cas_number": "9004-61-9",
            "safety_rating": "SAFE",
            "hazards": "None identified; high molecular weight form does not penetrate skin; ultra-low molecular weight may cause irritation if sensitized skin",
            "sources": "FDA Database, Biomacromolecules, International Journal of Molecular Sciences",
            "description": "Natural humectant found in skin, achieving up to 1000x its weight in water. Used in serums, moisturizers at 0.5-2%. Absorbs water from environment and deep skin layers. Molecular weight determines penetration depth. Large molecules hydrate surface; smaller ones penetrate deeper."
        },
        {
            "name": "Ceramides",
            "cas_number": "Not Applicable",
            "safety_rating": "SAFE",
            "hazards": "None reported; rare contact sensitization to plant-derived forms",
            "sources": "Cosmetic Ingredient Review, Journal of Cosmetic Dermatology, Experimental Dermatology",
            "description": "Lipid molecules naturally present in skin (50% of skin barrier lipids). Plant or synthetic ceramides used at 2-5% in moisturizers and creams. Restore skin barrier function. Non-irritating and safe for sensitive skin. Essential for maintaining moisture barrier integrity."
        },
        {
            "name": "Lanolin",
            "cas_number": "8006-54-0",
            "safety_rating": "CAUTION",
            "hazards": "Contact sensitization in 0.5-3% of individuals; may contain pesticide residues from wool processing; comedogenic in some skin types",
            "sources": "Cosmetic Ingredient Review, Contact Dermatitis, Cosmetics and Toiletries Magazine",
            "description": "Waxy substance from sheep wool used in balms and creams at 1-20%. Highly emollient with good skin barrier repair. Can cause allergic reactions or clogged pores in sensitive individuals. Impure forms may contain contaminants. Controversial but generally safe when purified."
        },
        {
            "name": "Shea Butter",
            "cas_number": "Not Applicable",
            "safety_rating": "SAFE",
            "hazards": "Minimal; rare contact dermatitis in allergic individuals; comedogenic for acne-prone skin",
            "sources": "Traditional cosmetics, Safety Review CIR, Journal of Cosmetic Science",
            "description": "Natural fat from shea nut used in creams and balms. Rich in fatty acids and vitamin A. Excellent emollient and nourishing ingredient. Well-tolerated by most skin types. May trigger acne if overly concentrated in acne-prone individuals."
        },
        {
            "name": "Petrolatum",
            "cas_number": "8009-03-8",
            "safety_rating": "SAFE",
            "hazards": "None identified; comedogenic in sensitive skin types; high oleic acid content may contribute to barrier dysfunction in some conditions",
            "sources": "FDA GRAS, Cosmetic Ingredient Review, Dermatologic Therapy",
            "description": "Refined petroleum by-product used in lip balms, creams at 1-100%. Forms occlusive barrier trapping moisture. Non-irritating and non-comedogenic in most people but may trigger reactions in extremely sensitive skin. Cost-effective occlusive."
        },
        # Preservative and Anti-Microbial Agents
        {
            "name": "Sodium Benzoate",
            "cas_number": "532-32-1",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic levels (0.1-0.5%); rare contact sensitization; can convert to benzoic acid depending on pH",
            "sources": "FDA GRAS, European Food Safety Authority, Cosmetic Ingredient Review",
            "description": "Preservative used in skincare at 0.1-0.5%. Effective against bacteria and fungi. GRAS by FDA. Naturally found in berries. No reproductive, developmental, or systemic toxicity at cosmetic use levels. Well-tolerated by most skin types."
        },
        {
            "name": "Potassium Sorbate",
            "cas_number": "24634-61-5",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic levels (0.1-0.6%); rare contact sensitization; preservative effectiveness decreases with pH shift",
            "sources": "FDA GRAS, European Food Safety Authority, Cosmetic Ingredient Review",
            "description": "Preservative against molds and yeasts in moisturizers, serums at 0.1-0.6%. GRAS designation. Natural form found in rowan berries. No systemic toxicity or reproductive effects. Safe for sensitive skin. Often combined with benzoates for broad-spectrum activity."
        },
        {
            "name": "Phenoxyethanol",
            "cas_number": "122-99-6",
            "safety_rating": "CAUTION",
            "hazards": "Contact sensitization in < 0.5% of population; potential systemic absorption with repeated high-concentration use; developmental toxicity at high levels",
            "sources": "Cosmetic Ingredient Review, Contact Dermatitis, European Medicines Agency",
            "description": "Preservative and solvent used at 0.5-1% in skincare products. Effective antimicrobial. EU limits to 1%. Systemic absorption possible with prolonged exposure but clinical significance unclear at cosmetic use levels. Safe when properly formulated."
        },
        {
            "name": "EDTA (Ethylenediaminetetraacetic Acid) and Salts",
            "cas_number": "60-00-4",
            "safety_rating": "CAUTION",
            "hazards": "Potential to chelate essential metals in extended exposure; systemic absorption if damaged skin barrier; dermal irritation at high concentrations",
            "sources": "Cosmetic Ingredient Review, FDA Database, ATSDR",
            "description": "Chelating agent used at 0.05-0.2% in cosmetics to prevent oxidation and improve stability. Prevents growth of bacteria relying on metal ions. Not absorbed through intact skin. Used safely for decades in cosmetics. Concerns arise only with very high concentrations or prolonged contact."
        },
        # Emulsifiers and Stabilizers
        {
            "name": "Cetyl Alcohol",
            "cas_number": "36653-82-4",
            "safety_rating": "SAFE",
            "hazards": "None identified; very rarely contact sensitization; non-comedogenic",
            "sources": "Cosmetic Ingredient Review, FDA Database, Safety Assessment",
            "description": "Fatty alcohol used at 2-10% in creams and lotions as emulsifier and thickener. World Health Organization recognizes as safe. Not related to ethanol or isopropyl alcohol. Mild emollient with skin conditioning properties. Non-irritating across all skin types."
        },
        {
            "name": "Stearic Acid",
            "cas_number": "57-11-4",
            "safety_rating": "SAFE",
            "hazards": "None identified; non-irritating; naturally found in vegetable and animal fats",
            "sources": "Cosmetic Ingredient Review, FDA GRAS, PubChem Safety Review",
            "description": "Long-chain fatty acid used at 2-15% as emulsifier and thickener. GRAS designation. Improves texture and spreadability of creams. Mildly occlusive. Safe for all skin types including sensitive."
        },
        {
            "name": "Polysorbate 80",
            "cas_number": "9005-65-6",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic levels (up to 5%); traces of ethylene oxide may be present as manufacturing residue; safe for injection in drugs",
            "sources": "Cosmetic Ingredient Review, FDA Database, European Medicines Agency",
            "description": "Non-ionic emulsifier derived from sorbitan and polyethylene glycol. Used at 0.5-5% in creams, serums, sunscreens. Excellent solubilizer for essential oils and fragrance. Well-tolerated, non-irritating. FDA approved for both topical and injectable medicines."
        },
        {
            "name": "Lecithin",
            "cas_number": "8002-43-5",
            "safety_rating": "SAFE",
            "hazards": "None identified; rare contact sensitization in allergic individuals; naturally abundant in eggs, soy, sunflower",
            "sources": "Cosmetic Ingredient Review, FDA GRAS, Journal of Agricultural and Food Chemistry",
            "description": "Natural phospholipid from soy, egg, or sunflower. Excellent emulsifier and skin conditioning agent at 0.1-5%. Enhances skin barrier function. GRAS designation. Non-irritating across all skin types. Biocompatible with skin lipids."
        },
        # Antioxidants and Anti-Aging Ingredients
        {
            "name": "Retinol (Vitamin A)",
            "cas_number": "68-26-8",
            "safety_rating": "CAUTION",
            "hazards": "Teratogenicity risk at high systemic levels during pregnancy; photosensitivity; irritation, redness, peeling (retinization) during adjustment period; photodegradation",
            "sources": "FDA Pregnancy Category X, Journal of Cosmetic Dermatology, Dermatologic Surgery",
            "description": "Vitamin A derivative and retinoid used at 0.3-1% in anti-aging serums and creams. Powerful collagen booster and skin renewer. Not safe during pregnancy. Causes initial irritation requiring gradual acclimation. Must use sunscreen (SPF 30+). Potent but requires careful use."
        },
        {
            "name": "Ferulic Acid",
            "cas_number": "1135-24-6",
            "safety_rating": "SAFE",
            "hazards": "None identified at cosmetic concentrations; rare contact sensitization",
            "sources": "Cosmetic Ingredient Review, Molecules Journal, Journal of Cosmetic Dermatology",
            "description": "Plant-derived antioxidant from grains at 0.5-2% in serums. Potentiates vitamin C and vitamin E. Protects against oxidative stress from UV and pollution. Non-mucosalirritant. Synergistic effects when combined with other antioxidants."
        },
        {
            "name": "Niacinamide (Vitamin B3)",
            "cas_number": "98-92-0",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations (2-10%); can cause temporary flushing if ingested at high levels; excellent tolerability",
            "sources": "Cosmetic Ingredient Review, Dermatologic Therapy, Journal of Cosmetic Dermatology",
            "description": "Water-soluble B vitamin used at 2-10% in moisturizers and serums. Strengthens skin barrier, reduces sebum production, minimizes pores. Anti-inflammatory. Non-irritating for all skin types including sensitive. Safe to combine with other actives."
        },
        {
            "name": "Alpha-Tocopherol (Vitamin E)",
            "cas_number": "59-02-9",
            "safety_rating": "SAFE",
            "hazards": "Rare contact sensitization; oxidizes and loses efficacy in light and air; tocopheryl acetate form less stable",
            "sources": "Cosmetic Ingredient Review, FDA GRAS, Journal of Cosmetic Science",
            "description": "Fat-soluble antioxidant at 0.5-2% in serums, oils, and creams. Protects against oxidative damage. Mildly occlusive. Synergizes with vitamin C and ferulic acid for enhanced protection. Natural form superior to synthetic. Requires proper stabilization."
        },
        {
            "name": "Resveratrol",
            "cas_number": "501-36-0",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations; limited skin penetration due to polyphenol structure; photodegradation limits stability",
            "sources": "PubChem, Cosmetic Ingredient Review, Journal of Agricultural and Food Chemistry",
            "description": "Polyphenolic compound from red grapes at 0.1-1% in serums and creams. Potent antioxidant with anti-inflammatory properties. Limited bioavailability. Works synergistically with other antioxidants. Requires light-protective packaging for stability."
        },
        # Fragrance and Natural Extract Ingredients
        {
            "name": "Limonene",
            "cas_number": "138-86-3",
            "safety_rating": "CAUTION",
            "hazards": "Contact allergen in 1-2% of sensitized population; oxidizes to allergenic compounds; phototoxicity and photosensitization in high concentrations",
            "sources": "Contact Dermatitis, International Journal of Occupational and Environmental Health, EWG",
            "description": "Volatile terpene found in citrus oils. Used as fragrance component at 0.1-1%. Can cause dermatitis through oxidation to allergenic compounds. Phototoxic only at high concentrations. Most significant sensitizer among terpenes. Antioxidants (BHA, BHT) extend stability."
        },
        {
            "name": "Linalool",
            "cas_number": "78-70-6",
            "safety_rating": "CAUTION",
            "hazards": "Contact allergen activatable through oxidation; sensitizing rate 0.5-3% in fragrance-sensitive populations; photo-sensitization risk",
            "sources": "Contact Dermatitis, Environmental Health Perspectives, Dermatologic Clinics",
            "description": "Volatile terpene alcohol from lavender and floral oils. Pleasant fragrance component at 0.1-1%. Primary allergen becomes sensitizing when oxidized. Accumulates with repeated exposure. Frequency of sensitization increasing. Antioxidant preservation essential."
        },
        {
            "name": "Geraniol",
            "cas_number": "106-24-1",
            "safety_rating": "CAUTION",
            "hazards": "Contact allergen; delayed sensitization through oxidation products; fragrance allergen; photoallergic contact dermatitis potential",
            "sources": "Fragrance Ingredients Review, Contact Dermatitis, International Journal of Cosmetic Science",
            "description": "Monoterpene alcohol in rose and geranium oils. Used at 0.1-1% for fragrance. Becomes allergenic through oxidation and polymerization. Accounts for 0.5-3% of fragrance-allergic individuals. Sensitization appears gradual with cumulative exposure."
        },
        # Silicones and Functional Polymers
        {
            "name": "Dimethicone",
            "cas_number": "9016-00-6",
            "safety_rating": "SAFE",
            "hazards": "None identified; inert, non-absorbed through skin; non-comedogenic for most individuals; may accumulate on scalp if not thoroughly washed",
            "sources": "Cosmetic Ingredient Review, FDA Database, Journal of Cosmetic Science",
            "description": "Silicone polymer used at 1-15% in moisturizers, serums, and hair care. Excellent slip and smoothing agent. Forms breathable barrier. Hypoallergenic. Does not penetrate skin or accumulate systemically. Non-irritating across all skin types."
        },
        {
            "name": "Cyclomethicone",
            "cas_number": "69430-36-0",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations; volatile so may evaporate; environmental bioaccumulation concerns ongoing",
            "sources": "Cosmetic Ingredient Review, Environmental Health Perspectives, Journal of Cosmetic Science",
            "description": "Cyclic silicone used as solvent and carrier at 1-10% in serums and primers. Light, fast-absorbing feel. Enhances spreadability. Environmental persistence causes restricted use in some regions. Volatile compounds may contribute to air quality concerns."
        },
        # Surfactants and Cleansing Agents  
        {
            "name": "Cocamidopropyl Betaine",
            "cas_number": "61789-40-0",
            "safety_rating": "CAUTION",
            "hazards": "Contact allergen in 0.5-2% of individuals; irritation at high concentrations; contamination with quaternium-15 impurity historically problematic",
            "sources": "Contact Dermatitis, Cosmetic Ingredient Review, American Academy of Dermatology",
            "description": "Mild amphoteric surfactant from coconut oil used at 1-5% in cleansers and shampoos. Less irritating than SLS. Allergen rates increasing due to manufacturing process and impurities. Proper formulation and impurity control essential for safety."
        },
        {
            "name": "Decyl Glucoside",
            "cas_number": "68515-73-1",
            "safety_rating": "SAFE",
            "hazards": "None identified; mild to skin; biodegradable",
            "sources": "Cosmetic Ingredient Review, Green Chemistry Principles, Safety Assessment",
            "description": "Mild non-ionic surfactant from glucose and coconut oil used at 3-20% in gentle cleansers and baby products. Biodegradable and environmentally friendly. Non-toxic to aquatic life. Excellent for sensitive skin. Slightly more expensive than conventional surfactants."
        },
        # Humectants and Hydrating Agents
        {
            "name": "Butylene Glycol",
            "cas_number": "107-88-0",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations (1-20%); rare contact sensitization; may cause irritation if concentration exceeds 20%",
            "sources": "Cosmetic Ingredient Review, Safety Data Sheets, Toxicology Reports",
            "description": "Humectant, solvent, and preservative booster at 1-20% in serums, toners, and creams. Draws moisture into skin. Mildly antimicrobial enhancing preservative efficacy. Well-tolerated. Non-sticky feel. Synergizes with other hydrating ingredients."
        },
        {
            "name": "Propylene Glycol",
            "cas_number": "57-55-6",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations (5-20%); may cause irritation at very high levels; contact dermatitis extremely rare",
            "sources": "Cosmetic Ingredient Review, FDA GRAS, Safety Database",
            "description": "Humectant and solvent used at 5-20% in skincare. GRAS by FDA. Hygroscopic - draws moisture from air into skin. Enhances penetration of other actives. Mildly antimicrobial. Cost-effective and well-tolerated across all skin types."
        },
        # Botanical and Plant-Derived Ingredients
        {
            "name": "Green Tea Extract (EGCG)",
            "cas_number": "989-51-5",
            "safety_rating": "SAFE",
            "hazards": "None at cosmetic concentrations (0.1-2%); rare contact sensitization from tannins",
            "sources": "Phytotherapy Research, Journal of Cosmetic Dermatology, Molecules",
            "description": "Polyphenol-rich extract from Camellia sinensis at 0.1-2% in serums and moisturizers. Powerful antioxidant (100x more than vitamin C) and anti-inflammatory. Reduces sebum production. Non-irritating. Provides sun protection benefits. Requires stabilization for potency maintenance."
        },
        {
            "name": "Witch Hazel Extract",
            "cas_number": "84603-74-5",
            "safety_rating": "SAFE",
            "hazards": "None identified; mild astringent action; may cause slight drying in frequent use",
            "sources": "Phytotherapy Research, Traditional herbalism, Cosmetic Ingredient Review",
            "description": "Astringent extract from Hamamelis virginiana bark at 5-15% in astringent toners. Rich in tannins with skin-tightening properties. Anti-inflammatory and sebum-regulating. Excellent for oily and acne-prone skin. May over-dry if overused in sensitive skin."
        },
        {
            "name": "Jojoba Oil",
            "cas_number": "61789-97-7",
            "safety_rating": "SAFE",
            "hazards": "None identified; non-comedogenic for most; may be comedogenic in extremely sensitive individuals",
            "sources": "Cosmetic Ingredient Review, Journal of Cosmetic Science, Molecules",
            "description": "Liquid wax ester from jojoba seed similar in composition to skin sebum at 1-10% in serums and oils. Excellent emollient matching skin pH. Non-comedogenic. Non-irritating. Absorbs well. Ideal for sensitive and acne-prone skin."
        },
        {
            "name": "Rosehip Oil",
            "cas_number": "8002-69-5",
            "safety_rating": "SAFE",
            "hazards": "Rare contact sensitization; oxidizes easily requiring dark storage; may cause photosensitivity at very high concentrations",
            "sources": "Phytotherapy Research, Journal of the American Oil Chemists' Society, Safety Review",
            "description": "Oil rich in vitamin A, C, and essential fatty acids from Rosa canina at 2-10% in serums and oils. Anti-aging and anti-inflammatory. Brightens and smooths complexion. Requires antioxidant preservation. Best used in evening as slight photosensitivity possible."
        }
    ]
    
    kb.add_chemicals(initial_chemicals)
