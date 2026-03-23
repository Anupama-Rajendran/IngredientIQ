"""
Main Evaluation Pipeline for IngredientIQ

Run comprehensive RAGAS evaluations on the RAG system with:
- Separate LLM for evaluation (unbiased)
- Historical score tracking
- Comprehensive reporting
"""

import sys
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / "backend" / ".env")

from evals.ragas_evaluator import RAGASEvaluator, load_evaluation_history, load_baseline, save_baseline
from evals.eval_dataset import (
    get_ingredient_test_dataset,
    get_product_test_dataset,
    get_combined_test_dataset
)
from evals.report_generator import generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def collect_test_results(
    evaluator: RAGASEvaluator,
    test_data: list
) -> Dict[str, Any]:
    """
    Collect detailed test results for reporting
    
    Args:
        evaluator: RAGASEvaluator instance
        test_data: Test dataset
    
    Returns:
        Dictionary with test results
    """
    results = {
        "ingredient_tests": [],
        "product_tests": [],
        "failed_tests": [],
    }
    
    # Categorize tests
    for test in test_data:
        question = test.get("question", "")
        
        is_product = "neutrogena" in question.lower() or "cerave" in question.lower()
        
        if is_product:
            results["product_tests"].append(test)
        else:
            results["ingredient_tests"].append(test)
    
    return results


def run_evaluation(
    test_set: str = "combined",
    eval_llm: str = "gpt-3.5-turbo",
    save_results: bool = True,
    rate_limit_delay: float = 1.0
) -> None:
    """
    Run complete RAGAS evaluation pipeline
    
    Args:
        test_set: "ingredient", "product", or "combined"
        eval_llm: LLM to use for evaluation (separate from production)
        save_results: Whether to save scores to history
        rate_limit_delay: Delay in seconds between API calls (default: 1.0)
    """
    logger.info(f"Starting IngredientIQ RAGAS Evaluation")
    logger.info(f"Test Set: {test_set}")
    logger.info(f"Evaluation LLM: {eval_llm}")
    if rate_limit_delay > 0:
        logger.info(f"Rate Limit Delay: {rate_limit_delay}s between API calls")
    logger.info("-" * 60)
    
    # Load test data
    if test_set == "ingredient":
        test_data = get_ingredient_test_dataset()
    elif test_set == "product":
        test_data = get_product_test_dataset()
    else:
        test_data = get_combined_test_dataset()
    
    logger.info(f"Loaded {len(test_data)} test cases")
    logger.info(f"\n[INFO] Estimated time: {len(test_data) * 20}-{len(test_data) * 30} seconds (~{(len(test_data) * 25) // 60} minutes)")
    
    # Initialize evaluator with separate LLM
    logger.info(f"Initializing evaluator with {eval_llm}...")
    evaluator = RAGASEvaluator(eval_llm=eval_llm, rate_limit_delay=rate_limit_delay)
    
    # Run evaluation
    logger.info("Running RAGAS evaluation...")
    score = evaluator.evaluate(test_data)
    
    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("RAGAS EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"\n{score.summary}\n")
    logger.info("=" * 60)
    
    # Load baseline for comparison (first real evaluation run)
    baseline = load_baseline()
    
    if baseline:
        logger.info("\nBASELINE COMPARISON:")
        logger.info(f"Faithfulness: {score.faithfulness:.3f} (baseline: {baseline.faithfulness:.3f})")
        logger.info(f"Answer Relevancy: {score.answer_relevancy:.3f} (baseline: {baseline.answer_relevancy:.3f})")
        logger.info(f"Context Precision: {score.context_precision:.3f} (baseline: {baseline.context_precision:.3f})")
        logger.info(f"Context Recall: {score.context_recall:.3f} (baseline: {baseline.context_recall:.3f})")
    else:
        logger.info("\nNo baseline yet. This will be your baseline for future comparisons.")
    
    # Save results to history
    if save_results:
        evaluator.save_results(score)
        logger.info("[OK] Scores saved to eval_results/scores.jsonl")
    
    # Save baseline if this is first real evaluation
    save_baseline(score)
    
    # Collect detailed test results
    test_results = collect_test_results(evaluator, test_data)
    
    # Generate report
    logger.info("\nGenerating evaluation report...")
    generate_report(score, test_results, baseline)
    
    logger.info("\n[OK] Evaluation pipeline complete!")
    return score


def compare_evaluations() -> None:
    """Compare all historical evaluations"""
    history = load_evaluation_history()
    
    if len(history) < 2:
        logger.warning("Need at least 2 evaluations to compare")
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("EVALUATION HISTORY")
    logger.info("=" * 60)
    
    for i, score in enumerate(history, 1):
        logger.info(f"\nEvaluation {i} - {score.timestamp}")
        logger.info(f"  Faithfulness: {score.faithfulness:.3f}")
        logger.info(f"  Answer Relevancy: {score.answer_relevancy:.3f}")
        logger.info(f"  Context Precision: {score.context_precision:.3f}")
        logger.info(f"  Context Recall: {score.context_recall:.3f}")
        logger.info(f"  Status: {'[PASSED]' if score.passed else '[FAILED]'}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="IngredientIQ RAGAS Evaluation Pipeline",
        epilog="""
EXAMPLES:

OpenAI Models:
  python evals/run_evaluation.py --eval-llm gpt-3.5-turbo  # Default
  python evals/run_evaluation.py --eval-llm gpt-4

Anthropic Claude (RECOMMENDED - No rate limits):
  python evals/run_evaluation.py --eval-llm claude-3-haiku-20240307
  python evals/run_evaluation.py --eval-llm claude-3-sonnet-20240229

Google Gemini:
  python evals/run_evaluation.py --eval-llm gemini-1.5-flash

Hugging Face Open Source:
  python evals/run_evaluation.py --eval-llm mistral-7b-instruct-v0.1
  python evals/run_evaluation.py --eval-llm llama-2-70b-chat
  python evals/run_evaluation.py --eval-llm falcon-40b-instruct

Best Combinations:
  # Fastest, no rate limits
  python evals/run_evaluation.py --test-set ingredient --eval-llm claude-3-haiku-20240307
  
  # Full evaluation
  python evals/run_evaluation.py --eval-llm claude-3-sonnet-20240229
  
  # With rate limiting
  python evals/run_evaluation.py --rate-limit-delay 2.0 --test-set ingredient
  
  # View history
  python evals/run_evaluation.py --compare
        """
    )
    parser.add_argument(
        "--test-set",
        choices=["ingredient", "product", "combined"],
        default="combined",
        help="Which test set to run (default: combined). Use 'ingredient' for faster testing."
    )
    parser.add_argument(
        "--eval-llm",
        default="gpt-3.5-turbo",
        help="""LLM to use for evaluation. Options:
        OpenAI: gpt-3.5-turbo, gpt-4
        Anthropic: claude-3-haiku-20240307, claude-3-sonnet-20240229
        Google: gemini-1.5-flash
        Hugging Face: mistral-7b-instruct-v0.1, llama-2-70b-chat, falcon-40b-instruct"""
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=1.0,
        help="Delay in seconds between API calls (default: 1.0). Increase if hitting rate limits."
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Show historical comparison of all evaluations"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to history"
    )
    
    args = parser.parse_args()
    
    try:
        if args.compare:
            compare_evaluations()
        else:
            run_evaluation(
                test_set=args.test_set,
                eval_llm=args.eval_llm,
                save_results=not args.no_save,
                rate_limit_delay=args.rate_limit_delay
            )
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
