"""
Evaluation Report Generator

Generates comprehensive evaluation reports with:
1. Executive Summary
2. RAGAS Metric Scores
3. Input and Pre-ingredient Breakdown
4. RAG vs Baseline Comparison
5. Failure Analysis
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import sys
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.ragas_evaluator import RAGASScore, load_evaluation_history, get_score_trends


class EvaluationReportGenerator:
    """Generate comprehensive evaluation reports"""
    
    def __init__(self, output_dir: str = "eval_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_full_report(
        self,
        current_score: RAGASScore,
        test_results: Dict[str, Any],
        baseline_score: Optional[RAGASScore] = None,
        report_name: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive evaluation report
        
        Args:
            current_score: Current RAGAS scores
            test_results: Detailed test results
            baseline_score: Previous baseline for comparison
            report_name: Custom report name
        
        Returns:
            Path to generated report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = report_name or f"eval_report_{timestamp}.md"
        report_path = os.path.join(self.output_dir, report_name)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self._generate_header())
            f.write(self._generate_executive_summary(current_score, baseline_score))
            f.write(self._generate_ragas_metrics(current_score))
            f.write(self._generate_ingredient_breakdown(test_results))
            f.write(self._generate_rag_baseline_comparison(current_score, baseline_score))
            f.write(self._generate_failure_analysis(current_score, test_results))
            f.write(self._generate_trends())
            f.write(self._generate_recommendations(current_score))
        
        return report_path
    
    def _generate_header(self) -> str:
        """Generate report header"""
        return f"""# IngredientIQ RAG Evaluation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""
    
    def _generate_executive_summary(
        self,
        current_score: RAGASScore,
        baseline_score: Optional[RAGASScore] = None
    ) -> str:
        """Generate executive summary section"""
        status = "✓ PASSED" if current_score.passed else "✗ FAILED"
        
        summary = f"""## 1. Executive Summary

**Overall Status:** {status}

**Test Configuration:**
- Model: {current_score.model_version}
- Evaluation LLM: {current_score.eval_llm} (different from production)
- Test Cases: {current_score.test_size}
- Timestamp: {current_score.timestamp}

**Key Findings:**
- All metrics are tracked to ensure RAG quality
- Evaluation uses separate GPT-3.5 to avoid bias from production LLM
- Scores meet or exceed thresholds: {self._get_threshold_status(current_score)}

"""
        
        if baseline_score:
            summary += self._generate_comparison_summary(current_score, baseline_score)
        
        return summary
    
    def _get_threshold_status(self, score: RAGASScore) -> str:
        """Get threshold status for all metrics"""
        checks = [
            ("Faithfulness", score.faithfulness, 0.8),
            ("Answer Relevancy", score.answer_relevancy, 0.8),
            ("Context Precision", score.context_precision, 0.7),
            ("Context Recall", score.context_recall, 0.7),
        ]
        
        statuses = []
        for name, value, threshold in checks:
            status = "✓" if value >= threshold else "✗"
            statuses.append(f"{status} {name}")
        
        return ", ".join(statuses)
    
    def _generate_comparison_summary(
        self,
        current: RAGASScore,
        baseline: RAGASScore
    ) -> str:
        """Generate baseline comparison summary"""
        changes = {
            "Faithfulness": current.faithfulness - baseline.faithfulness,
            "Answer Relevancy": current.answer_relevancy - baseline.answer_relevancy,
            "Context Precision": current.context_precision - baseline.context_precision,
            "Context Recall": current.context_recall - baseline.context_recall,
        }
        
        summary = "**Changes from Baseline:**\n"
        for metric, change in changes.items():
            direction = "↑" if change > 0 else "↓" if change < 0 else "→"
            summary += f"- {metric}: {change:+.3f} {direction}\n"
        
        return summary + "\n"
    
    def _generate_ragas_metrics(self, score: RAGASScore) -> str:
        """Generate RAGAS metrics section"""
        return f"""## 2. RAGAS Metric Scores

| Metric | Score | Threshold | Status |
|--------|-------|-----------|--------|
| Faithfulness | {score.faithfulness:.3f} | 0.8 | {'✓ Pass' if score.faithfulness >= 0.8 else '✗ Fail'} |
| Answer Relevancy | {score.answer_relevancy:.3f} | 0.8 | {'✓ Pass' if score.answer_relevancy >= 0.8 else '✗ Fail'} |
| Context Precision | {score.context_precision:.3f} | 0.7 | {'✓ Pass' if score.context_precision >= 0.7 else '✗ Fail'} |
| Context Recall | {score.context_recall:.3f} | 0.7 | {'✓ Pass' if score.context_recall >= 0.7 else '✗ Fail'} |

**Metric Definitions:**

- **Faithfulness** (threshold: 0.8): Measures whether the generated answer is factually consistent with the retrieved context. Uses NLI (Natural Language Inference) to detect contradictions.

- **Answer Relevancy** (threshold: 0.8): Measures how relevant and focused the answer is to the input question. Checks for information density and completeness.

- **Context Precision** (threshold: 0.7): Measures the percentage of retrieved context that is relevant to the question. Lower is better for retrieval efficiency.

- **Context Recall** (threshold: 0.7): Measures how much of the relevant context was successfully retrieved. Higher is better for completeness.

"""
    
    def _generate_ingredient_breakdown(
        self,
        test_results: Dict[str, Any]
    ) -> str:
        """Generate ingredient breakdown section"""
        breakdown = """## 3. Input and Pre-ingredient Breakdown

**Test Cases by Category:**

"""
        
        if "ingredient_tests" in test_results:
            breakdown += "### Ingredient Tests\n"
            for i, test in enumerate(test_results["ingredient_tests"], 1):
                breakdown += f"{i}. **{test['question']}**\n"
                breakdown += f"   - Contexts Retrieved: {len(test.get('contexts', []))}\n"
                breakdown += f"   - Answer Length: {len(test.get('answer', ''))} chars\n"
                breakdown += f"   - Classification: {test.get('classification', 'N/A')}\n\n"
        
        if "product_tests" in test_results:
            breakdown += "### Product Tests\n"
            for i, test in enumerate(test_results["product_tests"], 1):
                breakdown += f"{i}. **{test['question']}**\n"
                breakdown += f"   - Ingredients Analyzed: {len(test.get('ingredients_analyzed', []))}\n"
                breakdown += f"   - Overall Score: {test.get('overall_score', 'N/A')}/100\n\n"
        
        return breakdown
    
    def _generate_rag_baseline_comparison(
        self,
        current_score: RAGASScore,
        baseline_score: Optional[RAGASScore] = None
    ) -> str:
        """Generate RAG vs Baseline comparison section"""
        if not baseline_score:
            return """## 4. RAG vs Baseline Comparison

*No baseline comparison available. Run evaluation multiple times to track improvements.*

"""
        
        comparison = """## 4. RAG vs Baseline Comparison

| Metric | Current | Baseline | Delta | Trend |
|--------|---------|----------|-------|-------|
"""
        
        metrics = [
            ("Faithfulness", current_score.faithfulness, baseline_score.faithfulness),
            ("Answer Relevancy", current_score.answer_relevancy, baseline_score.answer_relevancy),
            ("Context Precision", current_score.context_precision, baseline_score.context_precision),
            ("Context Recall", current_score.context_recall, baseline_score.context_recall),
        ]
        
        for name, current, baseline in metrics:
            delta = current - baseline
            trend = "↑ Improving" if delta > 0.05 else "↓ Degrading" if delta < -0.05 else "→ Stable"
            comparison += f"| {name} | {current:.3f} | {baseline:.3f} | {delta:+.3f} | {trend} |\n"
        
        comparison += "\n"
        return comparison
    
    def _generate_failure_analysis(
        self,
        current_score: RAGASScore,
        test_results: Dict[str, Any]
    ) -> str:
        """Generate failure analysis section"""
        failures = """## 5. Failure Analysis

"""
        
        # Check if any metrics are below thresholds
        failed_metrics = []
        if current_score.faithfulness < 0.8:
            failed_metrics.append(f"Faithfulness: {current_score.faithfulness:.3f} (threshold: 0.8)")
        if current_score.answer_relevancy < 0.8:
            failed_metrics.append(f"Answer Relevancy: {current_score.answer_relevancy:.3f} (threshold: 0.8)")
        if current_score.context_precision < 0.7:
            failed_metrics.append(f"Context Precision: {current_score.context_precision:.3f} (threshold: 0.7)")
        if current_score.context_recall < 0.7:
            failed_metrics.append(f"Context Recall: {current_score.context_recall:.3f} (threshold: 0.7)")
        
        if failed_metrics:
            failures += f"**Failed Metrics:** {len(failed_metrics)}\n\n"
            for metric in failed_metrics:
                failures += f"- {metric}\n"
            failures += "\n**Recommendations:**\n\n"
            if current_score.faithfulness < 0.8:
                failures += "- **Faithfulness:** Ensure retrieved contexts are accurate and LLM doesn't hallucinate. Review knowledge base quality.\n"
            if current_score.answer_relevancy < 0.8:
                failures += "- **Answer Relevancy:** Refine prompts to ensure focused, direct answers. Review question clarity.\n"
            if current_score.context_precision < 0.7:
                failures += "- **Context Precision:** Improve retrieval accuracy. Increase similarity threshold or refine embeddings.\n"
            if current_score.context_recall < 0.7:
                failures += "- **Context Recall:** Expand knowledge base or adjust retrieval parameters (top_k, chunk_size).\n"
        else:
            failures += "✓ **All metrics passed!** All RAGAS scores meet or exceed threshold requirements.\n\n"
        
        return failures
    
    def _generate_trends(self) -> str:
        """Generate trends section"""
        history = load_evaluation_history()
        
        if len(history) < 2:
            return """## Evaluation Trends

*Trends will be available after multiple evaluation runs. Current run is the baseline.*

"""
        
        trends_text = """## Evaluation Trends

**Historical Performance:**

"""
        
        score_trends = get_score_trends(history)
        
        if score_trends:
            trends_text += f"- Total Evaluation Runs: {len(history)}\n"
            trends_text += f"- Date Range: {score_trends['timestamps'][0]} to {score_trends['timestamps'][-1]}\n\n"
            
            # Calculate averages
            avg_faith = sum(score_trends["faithfulness"]) / len(score_trends["faithfulness"])
            avg_answer = sum(score_trends["answer_relevancy"]) / len(score_trends["answer_relevancy"])
            avg_precision = sum(score_trends["context_precision"]) / len(score_trends["context_precision"])
            avg_recall = sum(score_trends["context_recall"]) / len(score_trends["context_recall"])
            
            trends_text += "**Average Scores Across All Runs:**\n"
            trends_text += f"- Faithfulness: {avg_faith:.3f}\n"
            trends_text += f"- Answer Relevancy: {avg_answer:.3f}\n"
            trends_text += f"- Context Precision: {avg_precision:.3f}\n"
            trends_text += f"- Context Recall: {avg_recall:.3f}\n\n"
        
        return trends_text
    
    def _generate_recommendations(self, score: RAGASScore) -> str:
        """Generate recommendations section"""
        recommendations = """## Recommendations

"""
        
        rec_list = []
        
        if score.faithfulness < 0.8:
            rec_list.append(
                "**Improve Faithfulness:** Review retrieved contexts for accuracy. "
                "Consider updating knowledge base or improving retrieval precision."
            )
        
        if score.answer_relevancy < 0.8:
            rec_list.append(
                "**Enhance Answer Relevancy:** Refine prompts to ensure focused answers. "
                "Review test cases for ambiguous questions."
            )
        
        if score.context_precision < 0.7:
            rec_list.append(
                "**Improve Context Precision:** Optimize retrieval settings. "
                "Consider increasing similarity threshold or improving embeddings."
            )
        
        if score.context_recall < 0.7:
            rec_list.append(
                "**Boost Context Recall:** Expand knowledge base or adjust retrieval parameters. "
                "Ensure chunking strategy captures all relevant information."
            )
        
        if score.passed:
            rec_list.insert(0, "✓ **All metrics pass thresholds.** Continue monitoring for regressions.")
        
        for i, rec in enumerate(rec_list, 1):
            recommendations += f"{i}. {rec}\n\n"
        
        recommendations += """---

**Next Steps:**
1. Address any failing metrics using recommendations above
2. Re-run evaluation after making changes
3. Track trends over time to monitor progress
4. Schedule periodic evaluations (weekly/monthly)
5. Document all changes to prompts, knowledge base, and retrieval settings

"""
        
        return recommendations


def generate_report(
    current_score: RAGASScore,
    test_results: Dict[str, Any],
    baseline_score: Optional[RAGASScore] = None
) -> None:
    """
    Generate and save evaluation report
    
    Args:
        current_score: Current RAGAS evaluation scores
        test_results: Detailed test results
        baseline_score: Previous scores for comparison
    """
    generator = EvaluationReportGenerator()
    report_path = generator.generate_full_report(
        current_score,
        test_results,
        baseline_score
    )
    print(f"[OK] Report saved to: {report_path}")
