"""
Regression Detection Script

Checks if current evaluation scores represent a regression from baseline.
Used in CI/CD pipelines to catch quality degradation.
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.ragas_evaluator import load_evaluation_history, RAGASScore


REGRESSION_THRESHOLDS = {
    "faithfulness": 0.02,      # Fail if drops > 2%
    "answer_relevancy": 0.02,  # Fail if drops > 2%
    "context_precision": 0.03, # Fail if drops > 3%
    "context_recall": 0.03,    # Fail if drops > 3%
}

CRITICAL_SCORES = {
    "faithfulness": 0.8,
    "answer_relevancy": 0.8,
    "context_precision": 0.7,
    "context_recall": 0.7,
}


def check_regression(
    history_file: str = "eval_results/scores.jsonl",
    strict: bool = False
) -> bool:
    """
    Check if latest evaluation represents a regression
    
    Args:
        history_file: Path to evaluation history
        strict: If True, fail on any drop from baseline
    
    Returns:
        True if passes, False if regression detected
    """
    history = load_evaluation_history(history_file)
    
    if len(history) < 2:
        print("✓ First evaluation - no regression check possible")
        return True
    
    current = history[-1]
    baseline = history[-2]
    
    print("\n" + "=" * 60)
    print("REGRESSION DETECTION")
    print("=" * 60)
    
    metrics = [
        ("Faithfulness", "faithfulness", current.faithfulness, baseline.faithfulness),
        ("Answer Relevancy", "answer_relevancy", current.answer_relevancy, baseline.answer_relevancy),
        ("Context Precision", "context_precision", current.context_precision, baseline.context_precision),
        ("Context Recall", "context_recall", current.context_recall, baseline.context_recall),
    ]
    
    regressions = []
    
    for display_name, key, current_val, baseline_val in metrics:
        delta = current_val - baseline_val
        threshold = REGRESSION_THRESHOLDS.get(key, 0.02)
        critical = CRITICAL_SCORES.get(key, 0.0)
        
        # Check both absolute regression and critical threshold
        is_regression = (
            delta < -threshold or  # Dropped more than threshold
            current_val < critical  # Below critical score
        )
        
        status = "✗ REGRESSION" if is_regression else "✓ OK"
        
        print(f"\n{display_name}:")
        print(f"  Current:  {current_val:.3f}")
        print(f"  Baseline: {baseline_val:.3f}")
        print(f"  Delta:    {delta:+.3f}")
        print(f"  Critical: {critical:.1f}")
        print(f"  Status:   {status}")
        
        if is_regression:
            regressions.append((display_name, delta, critical, current_val))
    
    print("\n" + "=" * 60)
    
    if regressions:
        print(f"\n✗ REGRESSION DETECTED ({len(regressions)} metric(s))")
        for metric, delta, critical, current in regressions:
            print(f"  - {metric}: {delta:+.3f} (below {critical}?)")
        
        return False
    else:
        print("\n✓ NO REGRESSIONS DETECTED")
        return True


def generate_regression_report(
    history_file: str = "eval_results/scores.jsonl",
) -> dict:
    """
    Generate detailed regression report
    
    Returns:
        Dictionary with regression analysis
    """
    history = load_evaluation_history(history_file)
    
    if len(history) < 2:
        return {"status": "insufficient_data"}
    
    current = history[-1]
    baseline = history[-2]
    
    report = {
        "status": "ok",
        "metrics": {},
        "regressions": [],
        "improvements": [],
    }
    
    metrics = {
        "faithfulness": (current.faithfulness, baseline.faithfulness),
        "answer_relevancy": (current.answer_relevancy, baseline.answer_relevancy),
        "context_precision": (current.context_precision, baseline.context_precision),
        "context_recall": (current.context_recall, baseline.context_recall),
    }
    
    for name, (current_val, baseline_val) in metrics.items():
        delta = current_val - baseline_val
        threshold = REGRESSION_THRESHOLDS.get(name, 0.02)
        critical = CRITICAL_SCORES.get(name, 0.0)
        
        report["metrics"][name] = {
            "current": current_val,
            "baseline": baseline_val,
            "delta": delta,
            "threshold": threshold,
            "critical": critical,
            "below_critical": current_val < critical,
        }
        
        if delta < -threshold or current_val < critical:
            report["regressions"].append(name)
            report["status"] = "regression"
        elif delta > threshold:
            report["improvements"].append(name)
    
    return report


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check for evaluation regressions"
    )
    parser.add_argument(
        "--history",
        default="eval_results/scores.jsonl",
        help="Path to evaluation history file"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any drop from baseline"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    if args.json:
        report = generate_regression_report(args.history)
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["status"] == "ok" else 1)
    else:
        passed = check_regression(args.history, args.strict)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
