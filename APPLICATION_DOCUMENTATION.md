# IngredientIQ - RAG-Powered Ingredient Safety Analysis

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Node.js](https://img.shields.io/badge/node.js-16+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

IngredientIQ is an AI-powered web application that analyzes product ingredients and classifies them as **Safe**, **Caution**, or **Harmful** using Retrieval-Augmented Generation (RAG) technology. The classification is backed by evidence from trusted chemical and toxicology databases.

## 🎯 Key Features

- **RAG-Enhanced Analysis**: Retrieves real chemical safety data before generating classifications
- **Multi-Source Evidence**: Combines data from PubChem, EWG, FDA, IARC, and Open Food Facts
- **Text & Image Input**: Search by product name or upload product label photos
- **Vision OCR**: Automatically extracts ingredients from images using Claude Vision
- **Color-Coded Safety Ratings**:
  - ✅ **SAFE** - No significant adverse effects at normal exposure
  - ⚠️ **CAUTION** - Potential risks at high doses; acceptable in small quantities
  - ❌ **HARMFUL** - Classified as toxic, carcinogenic, or otherwise hazardous
  - ❓ **UNKNOWN** - Insufficient data in knowledge base

- **Detailed Citations**: Every classification includes sources and reasoning
- **Product Scoring**: 0-100 overall safety score with ingredient breakdown
- **MCP Integration**: Tools for live API lookups (fallback when knowledge base gaps exist)

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│     React/Next.js Frontend          │
│  (Product Search + Image Upload)    │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│     FastAPI Backend Server          │
│  (LangChain + Claude Orchestration) │
└────────────────┬────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   ┌─────────────┐   ┌──────────────┐
   │ RAG Pipeline│   │ MCP Tools    │
   │             │   │              │
   │ ChromaDB    │   │ • Product    │
   │ Embeddings  │   │   Lookup     │
   │ Claude LLM  │   │ • PubChem    │
   │             │   │   Search     │
   └─────────────┘   │ • EWG API    │
                     │ • OCR Extract│
                     └──────────────┘
```

### RAG Pipeline Flow

1. **User Input** → Product name or ingredients
2. **Retrieval** → Vector search in ChromaDB for matching chemicals
3. **Context Enrichment** → Top-5 matches formatted with full metadata
4. **LLM Analysis** → Claude analyzes with evidence-based context
5. **Classification** → SAFE/CAUTION/HARMFUL with reasoning
6. **Fallback** → Live API calls for unknown ingredients
7. **Response** → Structured report with citations

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- API Keys:
  - [Anthropic Claude API](https://console.anthropic.com)
  - (Optional) OpenAI API key

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Run server
python main.py
# Server available at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
# Available at http://localhost:3000
```

### Verify Installation

```bash
# Check backend health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs

# Open application
open http://localhost:3000
```

## 💻 API Usage

### Analyze Product by Name

```bash
curl -X POST http://localhost:8000/api/v1/analyze-product \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Neutrogena Ultra Sheer Sunscreen"
  }'
```

**Response:**

```json
{
  "overall_rating": "CAUTION",
  "overall_score": 72.5,
  "ingredient_count": 8,
  "safety_summary": {
    "SAFE": 3,
    "CAUTION": 4,
    "HARMFUL": 0,
    "UNKNOWN": 1
  },
  "ingredients": [
    {
      "ingredient_name": "Zinc Oxide",
      "safety_rating": "SAFE",
      "reasoning": "FDA-approved UV filter, widely used in sunscreens...",
      "hazards": [],
      "sources": ["FDA", "PubChem"],
      "confidence_score": 0.95
    },
    ...
  ]
}
```

### Analyze Raw Ingredients

```bash
curl -X POST http://localhost:8000/api/v1/analyze-ingredients \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": [
      "sodium lauryl sulfate",
      "glycerin",
      "titanium dioxide"
    ]
  }'
```

### Upload Product Image

```bash
curl -X POST http://localhost:8000/api/v1/analyze-image \
  -F "file=@product_label.jpg"
```

### Search Individual Ingredient

```bash
curl http://localhost:8000/api/v1/ingredient-search?ingredient_name=benzene
```

## 📊 Knowledge Base

The knowledge base is pre-seeded with 10 verified chemicals including:

| Chemical              | Rating     | Reason                                           |
| --------------------- | ---------- | ------------------------------------------------ |
| Glycerin              | ✅ SAFE    | GRAS-approved, widely used humectant             |
| Sodium Lauryl Sulfate | ⚠️ CAUTION | Can cause skin irritation at high concentrations |
| Benzene               | ❌ HARMFUL | Group 1 carcinogen per IARC                      |
| Triclosan             | ❌ HARMFUL | Endocrine disruptor, banned in consumer soaps    |
| Vitamin C             | ✅ SAFE    | Essential nutrient, safe at cosmetic levels      |

### Expanding the Knowledge Base

Edit `backend/rag/knowledge_base.py` and add chemicals to the `seed_knowledge_base()` function:

```python
{
    "name": "Chemical Name",
    "cas_number": "12345-67-8",
    "safety_rating": "SAFE|CAUTION|HARMFUL|UNKNOWN",
    "hazards": "Semicolon-separated list of hazards",
    "sources": "Comma-separated source citations",
    "description": "Full chemical description and safety notes"
}
```

## 🛠️ Tech Stack

### Backend

- **Framework**: FastAPI (Python)
- **LLM Orchestration**: LangChain
- **Vector Database**: ChromaDB (local) or Pinecone (production)
- **LLM**: Anthropic Claude or OpenAI GPT
- **Embeddings**: OpenAI text-embedding-3-small or HuggingFace

### Frontend

- **Framework**: Next.js 14 (React)
- **Styling**: TailwindCSS
- **Language**: TypeScript
- **HTTP Client**: Axios / Fetch API

### Data Sources

- **Product Database**: Open Food Facts API
- **Chemical Data**: PubChem REST API
- **Safety Ratings**: EWG Skin Deep (scraping or CSV)
- **Regulatory**: FDA GRAS List, IARC Monographs
- **Standards**: GHS (Globally Harmonized System)

## 📁 Project Structure

```
.
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── config.py               # Configuration management
│   ├── requirements.txt         # Python dependencies
│   ├── rag/                    # RAG pipeline
│   │   ├── knowledge_base.py   # ChromaDB management
│   │   └── rag_pipeline.py     # Analysis pipeline
│   ├── llm/                    # LLM utilities
│   │   └── llm_factory.py      # LLM/Embedding creation
│   └── mcp_server/             # MCP tools
│       └── tools.py            # External API tools
│
├── frontend/
│   ├── package.json            # NPM dependencies
│   ├── next.config.js          # Next.js config
│   ├── tailwind.config.ts      # Tailwind config
│   ├── app/
│   │   ├── page.tsx            # Main page
│   │   ├── layout.tsx          # Root layout
│   │   └── globals.css         # Global styles
│   ├── components/             # React components
│   │   ├── ProductSearch.tsx
│   │   ├── ImageUpload.tsx
│   │   ├── ProductAnalysisResults.tsx
│   │   ├── IngredientCard.tsx
│   │   └── SafetyBadge.tsx
│   └── lib/                    # Utilities
│       └── api.ts              # API client
│
├── product-spec.md             # Product specification
├── SETUP.md                    # Setup guide (this file)
└── README.md                   # Feature documentation
```

## 🔐 Data Privacy

- All analysis happens server-side
- No ingredient data is stored or sold
- Knowledge base is regenerated on each deployment
- Cloud deployments should use encrypted databases
- Personal data handling complies with GDPR/CCPA

## 🚀 Deployment

### Docker Composition

```bash
# Build backend
docker build -t ingredientiq-backend ./backend

# Build frontend
docker build -t ingredientiq-frontend ./frontend

# Run with docker-compose
docker-compose up
```

### Cloud Deployment (Quick Notes)

**Backend (Railway/AWS Lambda):**

- Environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Vector DB: Use Pinecone or cloud ChromaDB instance
- Python version: 3.11+

**Frontend (Vercel/Netlify):**

- Build command: `npm run build`
- Output directory: `.next`
- Environment: `NEXT_PUBLIC_API_URL=https://your-backend.com`

## 🐛 Troubleshooting

**Backend won't start:**

```bash
# Check Python version
python --version  # Should be 3.9+

# Verify dependencies
pip list | grep langchain

# Check API keys
cat .env
```

**Frontend won't connect:**

```bash
# Verify backend is running
curl http://localhost:8000/health

# Check CORS settings in config.py
# Update NEXT_PUBLIC_API_URL in .env.local
```

**Knowledge base not working:**

```bash
# Clear and reseed
python -c "
from rag.knowledge_base import ChemicalKnowledgeBase, seed_knowledge_base
kb = ChemicalKnowledgeBase()
kb.clear()
seed_knowledge_base(kb)
print(f'{kb.count_chemicals()} chemicals seeded')
"
```

## 📚 Learning Resources

- [RAG Application Development](https://learn.deeplearning.ai/courses/rag-application-development) - DeepLearning.AI
- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Vector Database](https://docs.trychroma.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Next.js 14 Documentation](https://nextjs.org/docs)

## 🎓 Learning Goals

This project demonstrates:

1. **RAG Architecture** - Grounding LLMs in external knowledge bases
2. **Vector Embeddings** - Semantic search using ChromaDB
3. **LLM Orchestration** - Combining multiple AI tools with LangChain
4. **MCP Pattern** - Exposing external APIs to language models
5. **Full-Stack AI** - End-to-end production-ready AI application
6. **Data Integration** - Working with multiple public APIs

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Integrate real EWG Skin Deep data
- [ ] Add more chemical records to knowledge base
- [ ] Implement user accounts and watchlists
- [ ] Create mobile React Native app
- [ ] Build browser extension for live product scanning
- [ ] Add PDF export functionality
- [ ] Implement caching for faster results
- [ ] Add multilingual support

## 📜 License

MIT License - See LICENSE file for details

## 👋 Support

For questions or issues:

- Check [SETUP.md](./SETUP.md) for detailed setup instructions
- Review API docs at `/docs` endpoint
- Check GitHub issues for known problems

---

**Built with ❤️ for ingredient safety and informed consumer choices**

_IngredientIQ v1.0 | RAG + MCP Architecture | Powered by Claude AI_
