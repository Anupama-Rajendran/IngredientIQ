#!/usr/bin/env python
"""
Debug RAGAS Answer Relevancy NaN Issue
Diagnoses why Answer Relevancy metric returns NaN
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "backend" / ".env")

# Import RAG components
try:
    from rag.knowledge_base import ChemicalKnowledgeBase
    from rag.rag_pipeline import IngredientSafetyRAG
    from config import settings
    from llm.llm_factory import LLMFactory
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

# Import RAGAS
try:
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness, context_precision, context_recall
    from datasets import Dataset
except ImportError as e:
    logger.error(f"RAGAS import error: {e}")
    sys.exit(1)

print("=" * 70)
print("DEBUG: RAGAS Answer Relevancy NaN Issue")
print("=" * 70)

# Step 1: Initialize RAG pipeline
print("\n[STEP 1] Initializing RAG Pipeline...")
try:
    kb = ChemicalKnowledgeBase(settings.VECTOR_DB_PATH)
    logger.info(f"KB loaded: {kb.count_chemicals()} chemicals")
    
    llm = LLMFactory.create_llm()
    logger.info(f"LLM created: {type(llm).__name__}")
    
    rag = IngredientSafetyRAG(kb, llm=llm)
    logger.info("RAG pipeline ready")
except Exception as e:
    logger.error(f"RAG init failed: {e}", exc_info=True)
    sys.exit(1)

# Step 2: Test cases
test_cases = [
    {
        "question": "Is sodium lauryl sulfate safe in skincare?",
        "ground_truth": "Sodium lauryl sulfate can cause skin irritation in sensitive individuals."
    },
    {
        "question": "What is the safety profile of titanium dioxide?",
        "ground_truth": "Titanium dioxide is generally recognized as safe in sunscreens."
    },
]

# Step 3: Generate evaluation dataset
print("\n[STEP 2] Generating evaluation data with RAG...")
eval_data = []

for i, case in enumerate(test_cases):
    print(f"\n  Case {i+1}: {case['question'][:50]}...")
    try:
        # Retrieve contexts
        docs = rag.retrieve_context(case["question"], top_k=4)
        contexts = [d.get('document', '') for d in docs] if docs else []
        
        if not contexts:
            logger.warning(f"No contexts retrieved for case {i+1}")
            contexts = ["No relevant context found"]
        
        logger.debug(f"  Contexts: {len(contexts)} retrieved")
        
        # Generate answer
        from langchain_core.prompts import PromptTemplate
        p = PromptTemplate(
            template=rag.safety_prompt_template,
            input_variables=["context", "question"]
        )
        ctx_str = "\n\n".join(contexts)
        result = (p | rag.llm).invoke({"context": ctx_str, "question": case["question"]})
        answer = result.content if hasattr(result, 'content') else str(result)
        
        if not answer:
            logger.error(f"  Empty answer generated for case {i+1}")
            continue
        
        logger.info(f"  Answer: {len(answer)} chars")
        
        # Build evaluation record
        record = {
            "question": case["question"],
            "answer": answer,
            "contexts": contexts,
            "ground_truth": case["ground_truth"]
        }
        
        # Validate
        assert isinstance(record["question"], str), "question not str"
        assert isinstance(record["answer"], str) and len(record["answer"]) > 0, "answer invalid"
        assert isinstance(record["contexts"], list) and len(record["contexts"]) > 0, "contexts invalid"
        assert isinstance(record["ground_truth"], str) and len(record["ground_truth"]) > 0, "ground_truth invalid"
        assert all(isinstance(c, str) for c in record["contexts"]), "context items not str"
        
        logger.info(f"  [OK] Record {i+1} valid")
        eval_data.append(record)
        
    except Exception as e:
        logger.error(f"Case {i+1} failed: {e}", exc_info=True)
        continue

if not eval_data:
    logger.error("No valid evaluation data generated")
    sys.exit(1)

print(f"\n[OK] Generated {len(eval_data)} evaluation records")

# Step 4: Print sample data
print("\n[STEP 3] Sample Data (Case 1):")
print("-" * 70)
print(f"Question: {eval_data[0]['question']}")
print(f"Answer (first 200 chars): {eval_data[0]['answer'][:200]}...")
print(f"Contexts: {len(eval_data[0]['contexts'])} items")
print(f"Ground Truth: {eval_data[0]['ground_truth']}")
print("-" * 70)

# Step 5: Run RAGAS evaluation with detailed logging
print("\n[STEP 4] Running RAGAS Evaluation...")

try:
    # Create Dataset
    ds = Dataset.from_list(eval_data)
    logger.info(f"Dataset created: {len(ds)} records")
    logger.debug(f"Dataset columns: {ds.column_names}")
    
    # Evaluate each metric separately to isolate the NaN issue
    print("\nEvaluating each metric separately:")
    print("-" * 70)
    
    # Faithfulness
    print("\n1. Faithfulness metric:")
    try:
        faithfulness_results = evaluate(
            ds,
            metrics=[faithfulness],
            llm=None,  # Use default LLM
            embeddings=None,
            show_progress=False
        )
        logger.info(f"Faithfulness result type: {type(faithfulness_results)}")
        logger.info(f"Faithfulness result: {faithfulness_results}")
        if hasattr(faithfulness_results, 'faithfulness_score'):
            print(f"  Score: {faithfulness_results.faithfulness_score}")
        elif isinstance(faithfulness_results, dict):
            print(f"  Score: {faithfulness_results.get('faithfulness', 'N/A')}")
    except Exception as e:
        logger.error(f"Faithfulness failed: {e}", exc_info=True)
    
    # Answer Relevancy - THIS IS WHERE NaN APPEARS
    print("\n2. Answer Relevancy metric (CHECKING FOR NaN):")
    try:
        ar_results = evaluate(
            ds,
            metrics=[answer_relevancy],
            llm=None,
            embeddings=None,
            show_progress=False
        )
        logger.info(f"Answer Relevancy result type: {type(ar_results)}")
        logger.info(f"Answer Relevancy result: {ar_results}")
        
        if hasattr(ar_results, 'answer_relevancy_score'):
            score = ar_results.answer_relevancy_score
            print(f"  Score: {score}")
            if str(score) == 'nan':
                print("  [WARNING] NaN detected in answer_relevancy_score!")
                print("  Debugging info:")
                logger.debug(f"  Result attributes: {dir(ar_results)}")
        elif isinstance(ar_results, dict):
            score = ar_results.get('answer_relevancy', 'N/A')
            print(f"  Score: {score}")
            if str(score) == 'nan':
                print("  [WARNING] NaN detected!")
    except Exception as e:
        logger.error(f"Answer Relevancy failed: {e}", exc_info=True)
    
    # Context Precision
    print("\n3. Context Precision metric:")
    try:
        cp_results = evaluate(
            ds,
            metrics=[context_precision],
            llm=None,
            embeddings=None,
            show_progress=False
        )
        logger.info(f"Context Precision result: {cp_results}")
        if hasattr(cp_results, 'context_precision_score'):
            print(f"  Score: {cp_results.context_precision_score}")
    except Exception as e:
        logger.error(f"Context Precision failed: {e}", exc_info=True)
    
    # Context Recall  
    print("\n4. Context Recall metric:")
    try:
        cr_results = evaluate(
            ds,
            metrics=[context_recall],
            llm=None,
            embeddings=None,
            show_progress=False
        )
        logger.info(f"Context Recall result: {cr_results}")
        if hasattr(cr_results, 'context_recall_score'):
            print(f"  Score: {cr_results.context_recall_score}")
    except Exception as e:
        logger.error(f"Context Recall failed: {e}", exc_info=True)
    
    # ALL metrics together
    print("\n" + "=" * 70)
    print("Running all metrics together:")
    print("=" * 70)
    all_results = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=None,
        embeddings=None,
        show_progress=True
    )
    
    logger.info(f"All results type: {type(all_results)}")
    logger.info(f"All results: {all_results}")
    print(f"\nFinal Results:\n{all_results}")
    
    # Check for NaN values
    print("\nNaN Detection:")
    for col in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
        if hasattr(all_results, col):
            val = getattr(all_results, col)
            is_nan = str(val) == 'nan' or (isinstance(val, float) and val != val)  # NaN check
            status = "[NaN]" if is_nan else "[OK]"
            print(f"  {col}: {val} {status}")
    
except Exception as e:
    logger.error(f"RAGAS evaluation failed: {e}", exc_info=True)
    print(f"\n[ERROR] Error: {e}")

print("\n" + "=" * 70)
print("Debug complete. Check logs above for NaN cause.")
print("=" * 70)