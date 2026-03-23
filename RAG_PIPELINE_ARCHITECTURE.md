# Separate RAG Pipelines for Production and Evaluation

## Overview

The LabelLens RAG system now features two separate pipeline variants optimized for different use cases:

1. **ProductionRAG** - Real-time safety analysis with all data sources
2. **EvaluationRAG** - RAGAS evaluation with tunable parameters

This separation allows each variant to be optimized independently without compromise.

## Architecture

```
BaseIngredientSafetyRAG (Abstract Base Class)
├── Shared Logic
│   ├── _lookup_from_all_sources()
│   ├── retrieve_context()
│   ├── format_context()
│   ├── analyze_ingredient()
│   ├── analyze_product_ingredients()
│   └── ... (all core RAG methods)
├── Abstract Methods
│   ├── get_top_k()
│   ├── get_similarity_threshold()
│   └── log_retrieval()
│
├── ProductionRAG (for real-time use)
│   ├── Multi-source enabled
│   ├── top_k: 10
│   ├── threshold: 0.5
│   └── Minimal logging
│
└── EvaluationRAG (for RAGAS metrics)
    ├── Multi-source configurable
    ├── top_k, threshold overridable
    ├── Detailed logging
    └── Retrieval metrics tracking
```

## Usage

### Quick Start - Production

```python
from backend.rag.knowledge_base import ChemicalKnowledgeBase
from backend.rag.rag_factory import create_rag_pipeline

# Initialize knowledge base
kb = ChemicalKnowledgeBase()
kb.load_from_database()

# Create production RAG pipeline (all defaults)
rag = create_rag_pipeline(kb, variant="production")

# Use for real-time analysis
result = rag.analyze_ingredient("sodium lauryl sulfate")
print(f"Safety Rating: {result['safety_rating']}")
```

### Production Usage with Manager

```python
from backend.rag.rag_factory import RAGPipelineManager

manager = RAGPipelineManager(kb)

# Use production pipeline
prod_result = manager.production.analyze_ingredient("water")
```

### Evaluation Setup

#### KB-Only Mode (Default for RAGAS)
```python
from backend.rag.rag_factory import create_rag_pipeline

# Create evaluation pipeline with KB-only mode
# This disables PubChem/FDA/EWG/IARC live APIs for consistent evaluation
rag_eval = create_rag_pipeline(
    kb,
    variant="evaluation",
    enable_multi_source=False  # KB data only
)

result = rag_eval.analyze_ingredient("sodium lauryl sulfate")
```

#### KB + Live APIs for Evaluation
```python
# Create evaluation pipeline with live API fallback
rag_eval = create_rag_pipeline(
    kb,
    variant="evaluation",
    enable_multi_source=True  # Include PubChem, FDA, EWG, IARC
)
```

#### Testing Different Retrieval Parameters
```python
# Test with reduced retrieval window
rag_eval_conservative = create_rag_pipeline(
    kb,
    variant="evaluation",
    enable_multi_source=False,
    top_k_override=5,           # Retrieve only top 5 (default is 10)
    threshold_override=0.7      # Higher threshold (default is 0.5)
)

# Test with aggressive retrieval
rag_eval_aggressive = create_rag_pipeline(
    kb,
    variant="evaluation",
    enable_multi_source=False,
    top_k_override=20,          # Retrieve top 20
    threshold_override=0.3      # Lower threshold
)
```

### Using with RAGAS Evaluation

```python
from evals.ragas_evaluator import RAGAsEvaluator
from backend.rag.rag_factory import create_rag_pipeline

# Create evaluation-optimized RAG
rag_eval = create_rag_pipeline(
    kb,
    variant="evaluation",
    enable_multi_source=False
)

# Use with RAGAS
evaluator = RAGAsEvaluator(rag=rag_eval)
results = evaluator.evaluate(test_cases, llm=eval_llm)
```

## Configuration Reference

### ProductionRAG Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `enable_multi_source` | `True` | Always enabled - uses all available sources |
| `top_k` | `10` | Balanced retrieval for production use |
| `similarity_threshold` | `0.5` | Filters noise while keeping relevant results |
| `logging` | Info + Warning | Minimal overhead, only important events |

**Best for:** Real-time production API, highest accuracy needed, use all data sources

### EvaluationRAG Configuration

| Parameter | Default | Tunable | Purpose |
|-----------|---------|---------|---------|
| `enable_multi_source` | `False` | Yes | Disable APIs for consistent KB-only evaluation |
| `top_k` | `10` | Yes | Test Context Recall with different retrieval window sizes |
| `similarity_threshold` | `0.5` | Yes | Test Context Precision with different thresholds |
| `logging` | Debug | Built-in | Detailed metrics for debugging evaluation |

**Best for:** RAGAS evaluation, parameter experimentation, metrics debugging

## Design Decisions

### 1. Abstract Base Class Approach
- **Why**: Eliminates code duplication while allowing variant-specific behavior
- **Benefit**: All RAG logic updates benefit both variants automatically
- **Trade-off**: Slightly more complex inheritance structure

### 2. Disabled Multi-Source by Default in EvaluationRAG
- **Why**: API latency and variability affect RAGAS metrics consistency
- **Benefit**: Pure KB evaluation isolates retrieval quality from API reliability
- **Flexibility**: Can re-enable with `enable_multi_source=True` for other tests

### 3. Variant-Specific Parameter Methods
- **Why**: Each variant has different optimal thresholds and retrieval sizes
- **Benefit**: Clear separation of concerns, easy to test different configs
- **Override Support**: Evaluation variant allows overriding for experimentation

### 4. Detailed Logging in EvaluationRAG
- **Why**: Understand metric failures at debug level
- **Benefit**: Track similarity scores, retrieval counts, source-specific metrics
- **No Impact**: Can be disabled with logging configuration

## Backward Compatibility

For existing code using `IngredientSafetyRAG`:

```python
# Old code still works - automatically uses ProductionRAG
from backend.rag.rag_pipeline import IngredientSafetyRAG

rag = IngredientSafetyRAG(kb)  # Same as ProductionRAG
```

The `IngredientSafetyRAG` class is aliased to `ProductionRAG` for backward compatibility.

## Migration Guide

### Replace existing imports with factory pattern:

**Before:**
```python
from backend.rag.rag_pipeline import IngredientSafetyRAG
rag = IngredientSafetyRAG(kb)
```

**After (Production - same behavior):**
```python
from backend.rag.rag_factory import create_rag_pipeline
rag = create_rag_pipeline(kb, variant="production")
```

**New (Evaluation):**
```python
from backend.rag.rag_factory import create_rag_pipeline
rag = create_rag_pipeline(kb, variant="evaluation")
```

## Performance Characteristics

### ProductionRAG
- **Latency**: ~2-3s per ingredient (includes multi-source lookups)
- **Accuracy**: Highest (uses all sources)
- **Resource**: Network calls to PubChem, FDA, EWG, IARC
- **Best for**: User-facing API, requires maximum accuracy

### EvaluationRAG (KB-only)
- **Latency**: <100ms per ingredient (no network calls)
- **Consistency**: High (no API variability)
- **Resource**: Local KB only
- **Best for**: RAGAS metrics, benchmarking, consistent evaluation

### EvaluationRAG (with APIs)
- **Latency**: Similar to ProductionRAG
- **Consistency**: Lower (API variability)
- **Flexibility**: Can test with/without APIs
- **Best for**: Experimentation, understanding RAGAS metric impacts

## Troubleshooting

### Q: Why does EvaluationRAG have multi_source disabled by default?
**A:** To ensure consistent, repeatable RAGAS evaluation without network latency/failures affecting metrics.

### Q: How do I test RAGAS with live APIs?
**A:** Use `enable_multi_source=True` when creating evaluation pipeline:
```python
rag = create_rag_pipeline(kb, variant="evaluation", enable_multi_source=True)
```

### Q: Can I still use the old IngredientSafetyRAG class?
**A:** Yes - it's aliased to ProductionRAG. But using the factory pattern is recommended.

### Q: How do I track retrieval quality in evaluation?
**A:** Use EvaluationRAG's metrics tracking:
```python
rag_eval = create_rag_pipeline(kb, variant="evaluation")
analyses = [rag_eval.analyze_ingredient(ing) for ing in ingredients]
metrics = rag_eval.get_retrieval_metrics()
```

## Related Files

- `backend/rag/rag_pipeline.py` - RAG pipeline implementations
- `backend/rag/rag_factory.py` - Factory for creating pipelines
- `evals/ragas_evaluator.py` - RAGAS evaluation orchestration
- `EVAL_IMPROVEMENTS.md` - Documentation of evaluation metric improvements

## Future Enhancements

1. **Adaptive Parameters**: Adjust top_k and threshold based on query complexity
2. **Caching Layer**: Cache multi-source results for faster evaluation
3. **Batch Evaluation**: Optimized batch processing for large test sets
4. **Metrics Dashboard**: Real-time visualization of retrieval vs RAGAS metrics
