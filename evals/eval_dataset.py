"""
Evaluation Dataset for IngredientIQ RAG - Dynamic Version
Uses RAG pipeline to generate test cases dynamically
"""
from typing import List, Dict, Any, Optional
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    from rag.knowledge_base import ChemicalKnowledgeBase
    from rag.rag_pipeline import IngredientSafetyRAG
    from config import settings
    from llm.llm_factory import LLMFactory
except ImportError as e:
    logger.warning(f"Could not import RAG: {e}")
    ChemicalKnowledgeBase = None
    IngredientSafetyRAG = None
    settings = None
    LLMFactory = None


def _get_rag_pipeline() -> Optional[IngredientSafetyRAG]:
    """Initialize RAG pipeline if components available."""
    if not all([ChemicalKnowledgeBase, LLMFactory, settings]):
        logger.error("Missing required components for RAG pipeline")
        return None
    try:
        logger.debug(f"Initializing KB from {settings.VECTOR_DB_PATH}")
        kb = ChemicalKnowledgeBase(settings.VECTOR_DB_PATH)
        count = kb.count_chemicals()
        logger.debug(f"KB loaded with {count} chemicals")
        
        logger.debug("Creating LLM")
        llm = LLMFactory.create_llm()
        logger.debug(f"LLM created: {type(llm).__name__}")
        
        logger.debug("Creating RAG pipeline")
        rag = IngredientSafetyRAG(kb, llm=llm)
        logger.debug("RAG pipeline initialized successfully")
        return rag
    except Exception as e:
        logger.error(f"RAG init failed: {e}", exc_info=True)
        return None


def _generate_rag_answer(rag: Optional[IngredientSafetyRAG], question: str) -> Dict[str, Any]:
    """Generate answer and retrieve contexts via RAG pipeline."""
    if not rag:
        logger.warning(f"RAG pipeline is None - cannot retrieve contexts")
        return {"contexts": [], "answer": ""}
    try:
        logger.debug(f"Retrieving context for: {question[:50]}...")
        docs = rag.retrieve_context(question, top_k=4)
        logger.debug(f"Retrieved {len(docs)} documents")
        
        if not docs:
            logger.warning(f"No documents retrieved for: {question[:50]}...")
            return {"contexts": [], "answer": "No data found"}
        
        ctxs = [d.get('document', '') for d in docs]
        ctx_str = "\n\n".join(ctxs)
        logger.debug(f"Context string length: {len(ctx_str)} chars")
        
        from langchain_core.prompts import PromptTemplate
        p = PromptTemplate(
            template=rag.safety_prompt_template,
            input_variables=["context", "question"]
        )
        result = (p | rag.llm).invoke({"context": ctx_str, "question": question})
        ans = result.content if hasattr(result, 'content') else str(result)
        logger.debug(f"Generated answer: {len(ans)} chars")
        
        return {"contexts": ctxs, "answer": ans}
    except Exception as e:
        logger.error(f"RAG failed for '{question[:50]}...': {e}", exc_info=True)
        return {"contexts": [], "answer": f"Error: {str(e)}"}


def get_ingredient_test_dataset() -> List[Dict[str, Any]]:
    """Get dynamic test dataset for ingredient evaluation."""
    questions = [
        "Is sodium lauryl sulfate safe at concentrations below 1% in rinse-off skincare products?",
        "What is the primary safety concern with titanium dioxide in powder sunscreen products?",
        "Is glycerin generally recognized as safe (GRAS) for topical application on skin?",
        "What is the regulatory status of benzene in consumer cosmetic products?",
        "Are parabens approved as preservatives in cosmetics at standard use levels (0.1-0.5%)?",
    ]
    
    ground_truths = [
        "SAFE - Sodium lauryl sulfate is safe below 1% in rinse-off products but causes skin irritation at higher concentrations.",
        "CAUTION - Nano-particles in powder form pose inhalation risks; topical use on intact skin is safe.",
        "SAFE - Glycerin is FDA-approved as GRAS and safe for all skin types.",
        "HARMFUL - Benzene is banned in cosmetics due to carcinogenic potential.",
        "CAUTION - Parabens are approved at standard levels but have potential endocrine effects at accumulated doses.",
    ]
    
    logger.info("Initializing RAG pipeline for ingredient evaluation...")
    rag = _get_rag_pipeline()
    
    test_cases = []
    for i, (q, gt) in enumerate(zip(questions, ground_truths)):
        logger.info(f"  [{i+1}/{len(questions)}] Generating: {q[:40]}...")
        result = _generate_rag_answer(rag, q)
        test_cases.append({
            "question": q,
            "contexts": result["contexts"],
            "answer": result["answer"],
            "ground_truth": gt
        })
    
    logger.info(f"✓ Generated {len(test_cases)} ingredient test cases")
    return test_cases


def get_product_test_dataset() -> List[Dict[str, Any]]:
    """Get dynamic test dataset for product-level evaluation.
    
    Note: Product-level evaluation requires MCP product ingredient lookup.
    Until MCP is integrated, this returns additional ingredient safety tests
    focused on common consumer product ingredients.
    """
    questions = [
        "Is niacinamide safe for sensitive skincare products?",
        "Are ceramides suitable for dry and sensitive skin formulations?",
    ]
    
    ground_truths = [
        "SAFE - Niacinamide is FDA-approved, non-comedogenic, and suitable for sensitive skin.",
        "SAFE - Ceramides restore skin barrier and are standard in dermatologist-recommended formulations.",
    ]
    
    logger.info("Initializing RAG pipeline for product ingredients evaluation...")
    rag = _get_rag_pipeline()
    
    test_cases = []
    for i, (q, gt) in enumerate(zip(questions, ground_truths)):
        logger.info(f"  [{i+1}/{len(questions)}] Generating: {q[:40]}...")
        result = _generate_rag_answer(rag, q)
        test_cases.append({
            "question": q,
            "contexts": result["contexts"],
            "answer": result["answer"],
            "ground_truth": gt
        })
    
    logger.info(f"✓ Generated {len(test_cases)} product ingredient test cases")
    return test_cases


def create_custom_test_case(
    question: str,
    contexts: List[str],
    answer: str,
    ground_truth: str
) -> Dict[str, Any]:
    """Create a custom test case."""
    return {
        "question": question,
        "contexts": contexts,
        "answer": answer,
        "ground_truth": ground_truth
    }


def get_combined_test_dataset() -> List[Dict[str, Any]]:
    """Get all test cases combined."""
    return get_ingredient_test_dataset() + get_product_test_dataset()
    return {
        "question": question,
        "contexts": contexts,
        "answer": answer,
        "ground_truth": ground_truth
    }


def get_combined_test_dataset() -> List[Dict[str, Any]]:
    """Get all test cases combined"""
    return get_ingredient_test_dataset() + get_product_test_dataset()
