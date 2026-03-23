#!/usr/bin/env python3
"""Script to ingest chemical safety data into the knowledge base from multiple sources."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.rag.knowledge_base import ChemicalKnowledgeBase
from backend.rag.data_loaders import ChemicalDataAggregator
from backend.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main ingestion script."""
    logger.info("=" * 60)
    logger.info("Chemical Knowledge Base Ingestion Script")
    logger.info("=" * 60)
    
    # Initialize knowledge base
    logger.info(f"Initializing knowledge base at: {settings.VECTOR_DB_PATH}")
    kb = ChemicalKnowledgeBase(settings.VECTOR_DB_PATH)
    
    # Clear existing data
    if kb.count_chemicals() > 0:
        logger.warning(f"Knowledge base contains {kb.count_chemicals()} chemicals. Clearing...")
        kb.clear()
        logger.info("Knowledge base cleared.")
    
    # Load chemicals from all sources
    logger.info("\nLoading chemicals from multiple sources...")
    logger.info("-" * 60)
    
    chemicals = ChemicalDataAggregator.load_all_chemicals()
    
    if not chemicals:
        logger.error("Failed to load any chemicals from data sources!")
        return 1
    
    logger.info(f"\nLoaded {len(chemicals)} unique chemicals")
    logger.info("-" * 60)
    
    # Add to knowledge base
    logger.info(f"\nAdding {len(chemicals)} chemicals to knowledge base...")
    kb.add_chemicals(chemicals)
    
    # Verify
    final_count = kb.count_chemicals()
    logger.info(f"\n✓ Knowledge base now contains {final_count} chemicals")
    
    # Print sample chemicals
    logger.info("\nSample chemicals loaded:")
    logger.info("-" * 60)
    for chem in chemicals[:5]:
        logger.info(f"  • {chem['name']} ({chem.get('cas_number', 'N/A')})")
        logger.info(f"    Rating: {chem['safety_rating']}")
        logger.info(f"    Sources: {chem['sources']}")
    
    if len(chemicals) > 5:
        logger.info(f"  ... and {len(chemicals) - 5} more")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Knowledge base ingestion complete!")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
