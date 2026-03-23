"""
RAGAS Evaluator for IngredientIQ

Evaluates RAG pipeline using RAGAS metrics:
- Faithfulness < 0.8
- Answer Relevancy < 0.8
- Context Precision < 0.7
- Context Recall < 0.7
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
except ImportError as e:
    raise ImportError(
        "RAGAS not installed. Install with: pip install ragas datasets scikit-learn"
    ) from e

try:
    from langchain_openai import ChatOpenAI
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    # Fallback for older langchain versions
    from langchain.chat_models import ChatOpenAI
    from langchain.embeddings import OpenAIEmbeddings

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    # Fallback for older langchain versions
    from langchain.chat_models import ChatAnthropic

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
except ImportError:
    ChatHuggingFace = None
    HuggingFaceEndpoint = None

from datasets import Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RAGASScore:
    """RAGAS metric scores"""
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    timestamp: str
    test_size: int
    model_version: str = "claude-haiku-4-5-20251001"
    eval_llm: str = "gpt-3.5-turbo"  # Different LLM for evaluation
    
    @property
    def passed(self) -> bool:
        """Check if all scores meet minimum thresholds"""
        return (
            self.faithfulness >= 0.8 and
            self.answer_relevancy >= 0.8 and
            self.context_precision >= 0.7 and
            self.context_recall >= 0.7
        )
    
    @property
    def summary(self) -> str:
        """Get summary of scores"""
        status = "✓ PASSED" if self.passed else "✗ FAILED"
        return (
            f"{status}\n"
            f"  Faithfulness: {self.faithfulness:.3f} (threshold: 0.8)\n"
            f"  Answer Relevancy: {self.answer_relevancy:.3f} (threshold: 0.8)\n"
            f"  Context Precision: {self.context_precision:.3f} (threshold: 0.7)\n"
            f"  Context Recall: {self.context_recall:.3f} (threshold: 0.7)"
        )


class RAGASEvaluator:
    """Main evaluator class using RAGAS framework"""
    
    def __init__(
        self,
        eval_llm: str = "gpt-3.5-turbo",
        embedding_model: str = "text-embedding-3-small",
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize RAGAS evaluator with separate LLM for evaluation
        
        Args:
            eval_llm: LLM to use for evaluation. Options:
                OpenAI: gpt-3.5-turbo, gpt-4
                Anthropic: claude-3-haiku-20240307, claude-3-sonnet-20240229
                Google: gemini-pro, gemini-1.5-pro
                Hugging Face: mistral-7b, llama-2-70b, etc.
            embedding_model: Embedding model for evaluation
            rate_limit_delay: Delay in seconds between API calls (default: 1.0)
        """
        self.eval_llm = eval_llm
        self.embedding_model = embedding_model
        self.rate_limit_delay = rate_limit_delay
        
        logger.info(f"Initializing RAGAS evaluator with {eval_llm}...")
        if rate_limit_delay > 0:
            logger.info(f"Rate limiting: {rate_limit_delay}s delay between calls")
        
        # Initialize evaluation LLM (separate from production LLM)
        if "gpt" in eval_llm.lower():
            self.llm = ChatOpenAI(
                model=eval_llm,
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY"),
                max_retries=5,
                timeout=60.0,
            )
        elif "claude" in eval_llm.lower():
            self.llm = ChatAnthropic(
                model=eval_llm,
                temperature=0,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                max_retries=5,
                timeout=60.0,
            )
        elif "gemini" in eval_llm.lower():
            if ChatGoogleGenerativeAI is None:
                raise ImportError(
                    "Gemini support requires: pip install langchain-google-genai"
                )
            self.llm = ChatGoogleGenerativeAI(
                model=eval_llm,
                temperature=0,
                api_key=os.getenv("GOOGLE_API_KEY"),
            )
        elif any(hf_model in eval_llm.lower() for hf_model in ["mistral", "llama", "falcon", "zephyr"]):
            if HuggingFaceEndpoint is None:
                raise ImportError(
                    "Hugging Face support requires: pip install langchain-huggingface"
                )
            self.llm = HuggingFaceEndpoint(
                repo_id=eval_llm,
                huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
                temperature=0,
            )
        else:
            raise ValueError(
                f"Unsupported eval LLM: {eval_llm}\n"
                f"Supported: gpt-*, claude-*, gemini-*, mistral-*, llama-*, falcon-*, zephyr-*"
            )
        
        # Initialize embeddings with fallback strategy
        self.embeddings = None
        
        # Try OpenAI embeddings first (if quota available)
        if os.getenv("OPENAI_API_KEY"):
            try:
                from langchain_openai import OpenAIEmbeddings
                self.embeddings = OpenAIEmbeddings(
                    model=embedding_model,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    request_timeout=60.0,
                )
                logger.info(f"Using OpenAI embeddings: {embedding_model}")
            except Exception as e:
                if "quota" in str(e).lower() or "429" in str(e):
                    logger.warning(f"OpenAI quota exhausted, switching to local embeddings: {e}")
                else:
                    logger.warning(f"Failed to initialize OpenAI embeddings: {e}")
        
        # Fallback to local embeddings if OpenAI unavailable
        if self.embeddings is None:
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                logger.info("Initializing local HuggingFace embeddings (offline, no API required)...")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2",  # Small, fast, local model
                )
                logger.info("Local embeddings ready - Answer Relevancy will now work!")
            except Exception as e:
                logger.error(f"Failed to initialize fallback embeddings: {e}")
                logger.warning("RAGAS metrics may fail or return NaN without embeddings")
    
    def _apply_rate_limit(self):
        """Apply rate limiting delay between API calls"""
        if self.rate_limit_delay > 0:
            time.sleep(self.rate_limit_delay)
    
    def evaluate(
        self,
        test_data: List[Dict[str, Any]]
    ) -> RAGASScore:
        """
        Evaluate RAG system using RAGAS metrics
        
        Args:
            test_data: List of dicts with keys:
                - question: Input query
                - contexts: List of retrieved contexts
                - answer: Generated answer
                - ground_truth: Reference answer (optional)
        
        Returns:
            RAGASScore object with evaluated metrics
        """
        logger.info(f"Evaluating {len(test_data)} test cases with {self.eval_llm}...")
        logger.info("Note: First evaluation may take 1-3 minutes due to API calls")
        
        # Convert to Dataset format
        logger.debug(f"Converting {len(test_data)} test cases to RAGAS Dataset format")
        dataset_dict = {
            "question": [item["question"] for item in test_data],
            "contexts": [item["contexts"] for item in test_data],
            "answer": [item["answer"] for item in test_data],
            "ground_truth": [
                item.get("ground_truth", "") for item in test_data
            ]
        }
        
        # Log sample data structure
        logger.debug(f"Sample test case:")
        if test_data:
            logger.debug(f"  Q: {test_data[0]['question'][:50]}")
            logger.debug(f"  Contexts: {len(test_data[0]['contexts'])} items")
            logger.debug(f"  Answer: {len(test_data[0]['answer'])} chars")
            logger.debug(f"  Ground truth: {len(test_data[0].get('ground_truth', ''))} chars")
            if test_data[0]['contexts']:
                logger.debug(f"  Sample context[0]: {str(test_data[0]['contexts'][0])[:100]}...")
        
        dataset = Dataset.from_dict(dataset_dict)
        
        try:
            logger.info("Starting RAGAS evaluation (may take a few minutes)...")
            
            # Apply initial rate limit before evaluation
            self._apply_rate_limit()
            
            # Run evaluation with modern RAGAS API
            results = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                ],
                llm=self.llm,
                embeddings=self.embeddings,
                show_progress=True,
            )
            
            # Apply rate limit after evaluation
            self._apply_rate_limit()
            
            # Extract scores - handle various RAGAS result types
            logger.debug(f"Results type: {type(results)}")
            logger.debug(f"Results attributes: {dir(results)}")
            
            # Try to extract from EvaluationResult object first
            try:
                faithfulness_score = float(results.faithfulness_score)
                answer_relevancy_score = float(results.answer_relevancy_score)
                context_precision_score = float(results.context_precision_score)
                context_recall_score = float(results.context_recall_score)
                logger.info("Extracted scores from EvaluationResult.x_score attributes")
            except AttributeError:
                # Try alternative attribute names
                try:
                    faithfulness_score = float(results.faithfulness)
                    answer_relevancy_score = float(results.answer_relevancy)
                    context_precision_score = float(results.context_precision)
                    context_recall_score = float(results.context_recall)
                    logger.info("Extracted scores from EvaluationResult attributes")
                except (AttributeError, TypeError):
                    # Try dict-like access
                    if isinstance(results, dict):
                        faithfulness_score = float(results.get("faithfulness", 0.0))
                        answer_relevancy_score = float(results.get("answer_relevancy", 0.0))
                        context_precision_score = float(results.get("context_precision", 0.0))
                        context_recall_score = float(results.get("context_recall", 0.0))
                        logger.info("Extracted scores from dict")
                    else:
                        # Try to access as list (for pandas/numpy results)
                        try:
                            faithfulness_score = float(results["faithfulness"][0])
                            answer_relevancy_score = float(results["answer_relevancy"][0])
                            context_precision_score = float(results["context_precision"][0])
                            context_recall_score = float(results["context_recall"][0])
                            logger.info("Extracted scores from array/list results")
                        except (TypeError, KeyError, IndexError):
                            # Last resort - try .mean()
                            try:
                                faithfulness_score = float(results["faithfulness"].mean())
                                answer_relevancy_score = float(results["answer_relevancy"].mean())
                                context_precision_score = float(results["context_precision"].mean())
                                context_recall_score = float(results["context_recall"].mean())
                                logger.info("Extracted scores using .mean()")
                            except:
                                raise ValueError(f"Could not extract scores from results type: {type(results)}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"RAGAS evaluation failed with exception type: {type(e).__name__}")
            logger.error(f"Error message: {error_msg}")
            
            if "429" in error_msg or "rate" in error_msg.lower():
                logger.error(
                    f"Rate limit error from OpenAI API.\n"
                    f"Suggestions:\n"
                    f"  1. Try again in a few minutes\n"
                    f"  2. Use smaller test set: --test-set ingredient\n"
                    f"  3. Use Claude for evaluation: --eval-llm claude-3-haiku-20240307\n"
                    f"  Error: {e}"
                )
            else:
                logger.error(f"Full traceback:", exc_info=True)
                logger.error(f"Data passed to RAGAS:")
                logger.error(f"  - Questions: {len(dataset_dict['question'])} items")
                logger.error(f"  - Answers: {len(dataset_dict['answer'])} items")
                logger.error(f"  - Contexts: {len(dataset_dict['contexts'])} items")
                logger.error(f"  - Ground truths: {len(dataset_dict['ground_truth'])} items")
                if dataset_dict['contexts']:
                    logger.error(f"  - First context list length: {len(dataset_dict['contexts'][0])}")
            
            # Fallback to default scores if evaluation fails
            faithfulness_score = 0.5
            answer_relevancy_score = 0.5
            context_precision_score = 0.5
            context_recall_score = 0.5
        
        # Create score object
        score = RAGASScore(
            faithfulness=faithfulness_score,
            answer_relevancy=answer_relevancy_score,
            context_precision=context_precision_score,
            context_recall=context_recall_score,
            timestamp=datetime.now().isoformat(),
            test_size=len(test_data),
            eval_llm=self.eval_llm
        )
        
        logger.info(f"Evaluation complete:\n{score.summary}")
        return score
    
    def save_results(
        self,
        score: RAGASScore,
        output_file: str = "eval_results/scores.jsonl"
    ) -> None:
        """Save evaluation scores to file"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(score)) + "\n")
        
        logger.info(f"Scores saved to {output_file}")


def load_evaluation_history(
    history_file: str = "eval_results/scores.jsonl"
) -> List[RAGASScore]:
    """Load historical evaluation scores"""
    if not os.path.exists(history_file):
        return []
    
    scores = []
    with open(history_file, "r") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                scores.append(RAGASScore(**data))
    
    return scores


def load_baseline(baseline_file: str = "eval_results/baseline.json") -> Optional[RAGASScore]:
    """Load baseline scores (first real evaluation run)"""
    if not os.path.exists(baseline_file):
        return None
    
    try:
        with open(baseline_file, "r") as f:
            data = json.load(f)
            return RAGASScore(**data)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to load baseline from {baseline_file}")
        return None


def save_baseline(score: RAGASScore, baseline_file: str = "eval_results/baseline.json") -> None:
    """Save baseline scores (first real evaluation run)"""
    # Only save as baseline if it's real scores (not fallback 0.5)
    is_fallback = (
        score.faithfulness == 0.5 and 
        score.answer_relevancy == 0.5 and 
        score.context_precision == 0.5 and 
        score.context_recall == 0.5
    )
    
    if is_fallback:
        logger.warning("Not saving fallback scores (all 0.5) as baseline")
        return
    
    # Only save if baseline doesn't exist yet
    if os.path.exists(baseline_file):
        logger.debug(f"Baseline already exists at {baseline_file}, skipping")
        return
    
    os.makedirs(os.path.dirname(baseline_file), exist_ok=True)
    
    try:
        with open(baseline_file, "w") as f:
            json.dump(asdict(score), f, indent=2)
        logger.info(f"Baseline saved to {baseline_file}")
    except Exception as e:
        logger.error(f"Failed to save baseline: {e}")



def get_score_trends(
    history: List[RAGASScore]
) -> Dict[str, List[float]]:
    """Get trends for all metrics over time"""
    if not history:
        return {}
    
    return {
        "faithfulness": [s.faithfulness for s in history],
        "answer_relevancy": [s.answer_relevancy for s in history],
        "context_precision": [s.context_precision for s in history],
        "context_recall": [s.context_recall for s in history],
        "timestamps": [s.timestamp for s in history],
    }
