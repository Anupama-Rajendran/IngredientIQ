# IngredientIQ - RAG-Powered Ingredient Safety Analysis

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)
![Node.js](https://img.shields.io/badge/node.js-16+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/status-production--ready-success?style=flat-square)

**An AI-powered web application that analyzes product ingredients using Retrieval-Augmented Generation (RAG) and Model Context Protocol (MCP).**

[Features](#features) • [Quick Start](#quick-start) • [API](#api) • [Architecture](#architecture) • [Documentation](#documentation)

</div>

---

## 🎯 Features

### 🔍 Multi-Input Analysis

- **Product Search** - Look up products by name (e.g., "Neutrogena Sunscreen")
- **Text Input** - Paste raw ingredient lists
- **Image Upload** - Upload product label photos with automatic OCR extraction

### 🧠 RAG-Enhanced Classification

- **Evidence-Based** - Each classification backed by retrieved chemical data
- **Structured Output** - JSON with reasoning, hazards, sources, and confidence scores
- **Multi-Source** - Data from PubChem, EWG, FDA, IARC, and Open Food Facts

### 🎨 Beautiful UI

- Color-coded safety badges (✅ SAFE, ⚠️ CAUTION, ❌ HARMFUL)
- Overall product safety score (0-100)
- Detailed ingredient cards with evidence
- Responsive design for desktop and mobile

### 🔧 Technical Innovation

- **RAG Pipeline** - Vector search + LLM analysis with context
- **MCP Tools** - External API tools for live data lookups
- **Vision OCR** - Claude Vision extracts text from images
- **Fallback Logic** - Gracefully handles unknown ingredients

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Python 3.9+
- Node.js 16+
- [Anthropic API Key](https://console.anthropic.com) (free tier available)

### 1️⃣ Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run server
python main.py
# 🎉 Backend running at http://localhost:8000
```

### 2️⃣ Frontend Setup (new terminal)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
# 🎉 Frontend running at http://localhost:3000
```

### 3️⃣ Access the Application

- **App**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### ✅ Verify Installation

```bash
# Run demo tests
python test_api.py
```

---

## 📊 Example Usage

### Search by Product Name

```
Input: "Neutrogena Ultra Sheer Sunscreen"
Output:
  Overall Rating: ⚠️ CAUTION
  Overall Score: 72.5/100

  Ingredients:
  ✅ Zinc Oxide (Safe - FDA-approved UV filter)
  ⚠️ Titanium Dioxide (Caution - Inhalation concerns)
  ❌ Formaldehyde (Harmful - Group 1 carcinogen)
  ...
```

### Upload Product Label

```
Input: Product image/photo
→ Claude Vision extracts ingredients
→ Same analysis pipeline
Output: Full product analysis
```

### Direct Ingredient Analysis

```
Input: ["glycerin", "benzene", "vitamin c"]
Output: Per-ingredient safety ratings with sources
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         React/Next.js Frontend              │
│      (Product Search + Image Upload)        │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│     FastAPI Backend (Python)                │
│  (LangChain + Claude Orchestration)         │
└────────────────────┬────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   ┌─────────────┐          ┌──────────────┐
   │ RAG Pipeline│          │ MCP Tools    │
   │             │          │              │
   │ ChromaDB +  │          │ • Lookup     │
   │ Embeddings  │          │   Products   │
   │ Claude LLM  │          │ • Search     │
   │             │          │   PubChem    │
   └─────────────┘          │ • OCR Extract│
                            └──────────────┘
```

### RAG Pipeline Flow

```
Ingredient Query
    ↓
Vector Search (ChromaDB)
    ↓
Top-5 Results Retrieved
    ↓
Context Formatted
    ↓
Claude Analyzes with Evidence
    ↓
Safety Classification + Reasoning
    ↓
Structured Response with Sources
```

---

## 📚 Knowledge Base

### Pre-Seeded Chemicals (10)

| Chemical              | Rating     | Reason                                  |
| --------------------- | ---------- | --------------------------------------- |
| Glycerin              | ✅ SAFE    | GRAS-approved, widely used              |
| Vitamin C             | ✅ SAFE    | Essential nutrient                      |
| Aloe Vera             | ✅ SAFE    | Traditional use, safe                   |
| Sodium Lauryl Sulfate | ⚠️ CAUTION | Skin irritation at high concentration   |
| Parabens              | ⚠️ CAUTION | Potential endocrine effects             |
| Titanium Dioxide      | ⚠️ CAUTION | Inhalation concerns with nano-particles |
| Benzene               | ❌ HARMFUL | IARC Group 1 Carcinogen                 |
| Triclosan             | ❌ HARMFUL | Endocrine disruptor                     |
| Phthalates            | ❌ HARMFUL | Reproductive toxicity                   |
| Formaldehyde          | ❌ HARMFUL | Known carcinogen                        |

### Expanding the Knowledge Base

Edit [backend/rag/knowledge_base.py](./backend/rag/knowledge_base.py) to add more chemicals to `seed_knowledge_base()` function.

---

## 🔌 API Endpoints

### Analyze Product

```bash
POST /api/v1/analyze-product
Content-Type: application/json

{
  "product_name": "Neutrogena Ultra Sheer Sunscreen"
}

Response: Product analysis with all ingredients
```

### Analyze Ingredients

```bash
POST /api/v1/analyze-ingredients

{
  "ingredients": ["sodium lauryl sulfate", "glycerin", "titanium dioxide"]
}

Response: Safety ratings for each ingredient
```

### Upload Image

```bash
POST /api/v1/analyze-image
Content-Type: multipart/form-data

file: product_label.jpg

Response: OCR extracted ingredients + analysis
```

### Search Ingredient

```bash
GET /api/v1/ingredient-search?ingredient_name=benzene

Response: Single ingredient analysis with evidence
```

### Other Endpoints

- `GET /health` - Health check
- `GET /api/v1/knowledge-base-stats` - KB statistics
- `GET /api/v1/tools` - List available MCP tools

**Full API Documentation**: http://localhost:8000/docs

---

## 📁 Project Structure

```
LabelLens/
├── backend/                 # FastAPI backend
│   ├── main.py             # Server + endpoints
│   ├── config.py           # Configuration
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example        # Config template
│   ├── rag/
│   │   ├── knowledge_base.py    # ChromaDB setup
│   │   └── rag_pipeline.py      # Analysis logic
│   ├── llm/
│   │   └── llm_factory.py       # LLM creation
│   └── mcp_server/
│       └── tools.py             # External tools
│
├── frontend/                # Next.js frontend
│   ├── app/
│   │   ├── page.tsx        # Main page
│   │   ├── layout.tsx      # Root layout
│   │   └── globals.css     # Styles
│   ├── components/
│   │   ├── ProductSearch.tsx
│   │   ├── ImageUpload.tsx
│   │   ├── ProductAnalysisResults.tsx
│   │   ├── IngredientCard.tsx
│   │   ├── SafetyBadge.tsx
│   │   └── IngredientAnalyzer.tsx
│   ├── lib/
│   │   └── api.ts          # API client
│   ├── public/             # Static assets
│   │   └── IngredientIQ_logo.svg
│   ├── package.json
│   ├── tailwind.config.ts  # Tailwind configuration
│   ├── tsconfig.json       # TypeScript config
│   └── next.config.js
│
├── SETUP.md               # Setup & installation guide
├── ARCHITECTURE.md        # Technical design & patterns
├── APPLICATION_DOCUMENTATION.md  # Feature guide & API reference
├── product-spec.md        # Original product specification
├── test_api.py            # API integration tests
├── start.sh               # Startup script
├── .gitignore
└── README.md              # This file
```

---

## 🧪 Testing

### Automated Tests

```bash
# Run all 6 demo tests
python test_api.py
```

Tests include:

- ✅ Backend health check
- ✅ Knowledge base statistics
- ✅ Single ingredient analysis
- ✅ Multiple ingredients analysis
- ✅ MCP tools listing
- ✅ Product lookup and analysis

### Manual Testing

```bash
# Health check
curl http://localhost:8000/health

# View interactive API docs
open http://localhost:8000/docs

# Analyze ingredients
curl -X POST http://localhost:8000/api/v1/analyze-ingredients \
  -H "Content-Type: application/json" \
  -d '{"ingredients": ["benzene", "glycerin"]}'
```

---

## � RAGAS Evaluation

IngredientIQ uses **RAGAS (Retrieval-Augmented Generation Assessment)** for comprehensive RAG pipeline evaluation with a separate LLM for unbiased evaluation.

### Evaluation Metrics

| Metric                | Threshold | Purpose                                                                      |
| --------------------- | --------- | ---------------------------------------------------------------------------- |
| **Faithfulness**      | ≥ 0.8     | Answers are factually consistent with retrieved contexts (no hallucinations) |
| **Answer Relevancy**  | ≥ 0.8     | Generated answers directly address the input question                        |
| **Context Precision** | ≥ 0.7     | Retrieved contexts are relevant to the query                                 |
| **Context Recall**    | ≥ 0.7     | All relevant contexts are successfully retrieved                             |

### Running Evaluations

```bash
# Run combined evaluation (ingredients + products)
python evals/run_evaluation.py

# Run specific test set
python evals/run_evaluation.py --test-set ingredient
python evals/run_evaluation.py --test-set product

# Use different LLM for evaluation (separate from production)
python evals/run_evaluation.py --eval-llm gpt-3.5-turbo

# Compare historical results
python evals/run_evaluation.py --compare
```

### Evaluation Reports

Each evaluation generates a comprehensive report including:

1. **Executive Summary** - Overall pass/fail status and key findings
2. **RAGAS Metric Scores** - Detailed metric breakdown with thresholds
3. **Input Breakdown** - Ingredient and product test categorization
4. **RAG vs Baseline Comparison** - Performance trends over time
5. **Failure Analysis** - Detailed investigation of any failed tests
6. **Trends** - Historical performance tracking
7. **Recommendations** - Specific improvements for failing metrics

Reports are saved to `eval_results/eval_report_YYYYMMDD_HHMMSS.md`

### Score Tracking

All evaluation scores are automatically tracked in `eval_results/scores.jsonl`:

```json
{
  "faithfulness": 0.85,
  "answer_relevancy": 0.82,
  "context_precision": 0.75,
  "context_recall": 0.76,
  "timestamp": "2024-03-20T10:30:45.123456",
  "test_size": 10,
  "eval_llm": "gpt-3.5-turbo"
}
```

### When to Re-evaluate

Run evaluations when:

- ✓ Prompt templates are modified
- ✓ Knowledge base content is updated
- ✓ Retrieval settings change (chunk size, similarity threshold)
- ✓ New features are implemented
- ✓ Monthly monitoring (scheduled)

---

## �🔐 Security & Privacy

- ✅ No user data stored
- ✅ API keys stored in environment only (not in code)
- ✅ CORS configured for safety
- ✅ All processing happens server-side
- ✅ Knowledge base is deterministic

---

## 📚 Documentation

| Document                                                       | Purpose                        | For              |
| -------------------------------------------------------------- | ------------------------------ | ---------------- |
| [SETUP.md](./SETUP.md)                                         | Installation guide             | Developers       |
| [ARCHITECTURE.md](./ARCHITECTURE.md)                           | Technical design               | Architects       |
| [EVALUATION.md](./EVALUATION.md)                               | RAGAS evaluation guide         | QA & Evaluation  |
| [APPLICATION_DOCUMENTATION.md](./APPLICATION_DOCUMENTATION.md) | Feature guide & API reference  | Users            |
| [product-spec.md](./product-spec.md)                           | Original product specification | Product managers |

---

## 🎓 Learning Resources

This project demonstrates:

1. **RAG (Retrieval-Augmented Generation)**
   - Vector embeddings and semantic search
   - Context-aware LLM analysis
   - Evidence-backed reasoning

2. **MCP (Model Context Protocol)**
   - Exposing tools to language models
   - Tool calling and invocation
   - Graceful fallbacks

3. **Full-Stack AI Development**
   - Backend orchestration with FastAPI
   - Frontend integration with Next.js
   - Vector database management
   - LLM integration patterns

4. **Production Patterns**
   - Configuration management
   - Error handling
   - API design
   - Security best practices

---

## 🚀 Deployment

### Local with Docker

```bash
docker-compose up
```

### Cloud Deployment

**Backend** → Railway / AWS Lambda

- Environment: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Database: Pinecone (cloud vector DB)

**Frontend** → Vercel / Netlify

- Build: `npm run build`
- Env: `NEXT_PUBLIC_API_URL=https://your-api.com`

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.9+

# Check dependencies
pip list | grep langchain

# Verify .env file
cat backend/.env
```

### Frontend won't connect

```bash
# Verify backend is running
curl http://localhost:8000/health

# Check logs for CORS issues
# Update NEXT_PUBLIC_API_URL in frontend/.env.local if needed
```

### Knowledge base not populated

```bash
# Check KB status
curl http://localhost:8000/api/v1/knowledge-base-stats

# Reseed KB
python -c "
from backend.rag.knowledge_base import ChemicalKnowledgeBase, seed_knowledge_base
kb = ChemicalKnowledgeBase()
kb.clear()
seed_knowledge_base(kb)
print(f'Seeded {kb.count_chemicals()} chemicals')
"
```

---

## 📦 Tech Stack

### Backend

- **FastAPI 0.104** - Python web framework
- **LangChain 0.0.348** - LLM orchestration
- **ChromaDB 0.4.17** - Vector database
- **Anthropic Claude** - LLM (primary)
- **OpenAI** - Alternative LLM + embeddings
- **Pydantic 2.5** - Data validation

### Frontend

- **Next.js 14** - React framework
- **TailwindCSS 3** - Styling
- **TypeScript 5** - Type safety
- **Axios** - HTTP client

### Data Sources

- **Open Food Facts** - Product database
- **PubChem** - Chemical data
- **EWG Skin Deep** - Safety ratings
- **FDA GRAS List** - Food safety
- **IARC** - Carcinogen classifications

---

## 📜 License

MIT License - See LICENSE for details

---

## ✅ Status

**✓ Complete and production-ready**

- All core features implemented
- Knowledge base pre-seeded
- API fully documented
- Frontend fully styled
- Ready for deployment

---

<div align="center">

**Built with ❤️ for ingredient safety and informed consumer choices**

_IngredientIQ v1.0 | RAG + MCP Architecture | Powered by Claude AI_

[⬆ Back to Top](#)

</div>
