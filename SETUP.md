## Quick Start Guide

### Prerequisites

- Python 3.9+
- Node.js 16+
- API Keys: Anthropic (Claude) or OpenAI

### Backend Setup

1. **Install Python Dependencies**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure Environment**

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   # ANTHROPIC_API_KEY=your_key_here
   # OPENAI_API_KEY=your_key_here
   ```

3. **Run Backend Server**
   ```bash
   python main.py
   # Server runs on http://localhost:8000
   # API docs available at http://localhost:8000/docs
   ```

### Frontend Setup

1. **Install Node Dependencies**

   ```bash
   cd frontend
   npm install
   ```

2. **Configure Environment** (if needed)

   ```bash
   # Frontend auto-configures to http://localhost:8000
   # Create .env.local if you need different backend URL
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Run Frontend**
   ```bash
   npm run dev
   # App runs on http://localhost:3000
   ```

### First Run

1. Backend will automatically seed the knowledge base with 10 chemical safety records
2. Open http://localhost:3000 in your browser
3. Try searching for "Neutrogena" or uploading a product label image
4. Check http://localhost:8000/docs for all available API endpoints

---

## Architecture Overview

### RAG (Retrieval-Augmented Generation) Pipeline

```
Ingredient Query
    ↓
[Knowledge Base Search] (ChromaDB)
    ↓
[Top-5 Matches Retrieved]
    ↓
[Claude LLM Analysis] with Context
    ↓
[Safety Classification]
    ├─ Rating: SAFE | CAUTION | HARMFUL | UNKNOWN
    ├─ Reasoning: Detailed explanation
    ├─ Hazards: List of identified risks
    ├─ Sources: Citation sources
    └─ Confidence Score: 0.0-1.0
    ↓
[Product Report Generated]
```

### MCP (Model Context Protocol) Tools

Available tools for the LLM to call:

| Tool                            | Purpose                 | Source              |
| ------------------------------- | ----------------------- | ------------------- |
| `lookup_product`                | Find product by name    | Open Food Facts API |
| `search_pubchem`                | Get chemical properties | PubChem API         |
| `parse_ingredients`             | Parse ingredient text   | Regex parser        |
| `get_ewg_rating`                | Get EWG Skin Deep score | EWG database        |
| `extract_ingredients_from_text` | OCR → ingredients       | NLP                 |

### Tech Stack

**Backend:**

- FastAPI (Python web framework)
- LangChain (LLM orchestration)
- ChromaDB (vector database)
- Claude/OpenAI (LLM provider)

**Frontend:**

- Next.js 14 (React framework)
- TailwindCSS (styling)
- TypeScript (type safety)

**Data Sources:**

- Open Food Facts (product database)
- PubChem (chemical data)
- EWG Skin Deep (safety ratings)
- FDA GRAS List (food safety)
- IARC Monographs (carcinogens)

---

## API Examples

### Analyze Product by Name

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-product" \
  -H "Content-Type: application/json" \
  -d '{"product_name": "Neutrogena Ultra Sheer Sunscreen"}'
```

### Analyze Raw Ingredients

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-ingredients" \
  -H "Content-Type: application/json" \
  -d '{"ingredients": ["sodium lauryl sulfate", "glycerin", "titanium dioxide"]}'
```

### Upload Product Image

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-image" \
  -F "file=@product_label.jpg"
```

### Search Single Ingredient

```bash
curl "http://localhost:8000/api/v1/ingredient-search?ingredient_name=benzene"
```

---

## Knowledge Base Management

### Add Custom Chemicals

Edit `backend/rag/knowledge_base.py` and add to `seed_knowledge_base()`:

```python
def seed_knowledge_base(kb: ChemicalKnowledgeBase) -> None:
    initial_chemicals = [
        {
            "name": "Chemical Name",
            "cas_number": "12345-67-8",
            "safety_rating": "SAFE|CAUTION|HARMFUL|UNKNOWN",
            "hazards": "List of hazards",
            "sources": "Source citations",
            "description": "Full description"
        },
        # ... more chemicals
    ]
    kb.add_chemicals(initial_chemicals)
```

Then restart the backend.

### Check KB Status

```bash
curl http://localhost:8000/api/v1/knowledge-base-stats
```

---

## Deployment

### Docker (Optional)

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend .
CMD ["python", "main.py"]
```

### Production Deployment

- **Backend:** Deploy to Railway, AWS Lambda, or Heroku
- **Frontend:** Deploy to Vercel, Netlify, or AWS S3 + CloudFront
- **Vector DB:** Use cloud-hosted ChromaDB or switch to Pinecone
- **LLM:** Use managed API (Anthropic, OpenAI)

---

## Troubleshooting

### Knowledge Base Not Seeded

```bash
# Clear and reseed KB
python -c "
from rag.knowledge_base import ChemicalKnowledgeBase, seed_knowledge_base
kb = ChemicalKnowledgeBase()
kb.clear()
seed_knowledge_base(kb)
print(f'Seeded {kb.count_chemicals()} chemicals')
"
```

### API Key Issues

- Verify `.env` file exists and is correctly formatted
- Ensure API keys are valid and have necessary permissions
- Check that environment variables are loaded: `cat .env`

### Frontend Won't Connect to Backend

- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS settings in `backend/config.py`
- Try setting `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local`

---

## Next Steps

1. **Expand Knowledge Base:** Integrate EWG Skin Deep and IARC database dumps
2. **Improve OCR:** Use specialized layout analysis for better label parsing
3. **User Accounts:** Add authentication and ingredient watchlists
4. **Mobile App:** Create React Native or Flutter mobile version
5. **Browser Extension:** Scan products while shopping online
6. **PDF Export:** Generate downloadable safety reports

---

## Resources

- [LangChain Docs](https://python.langchain.com/)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [Claude API](https://anthropic.com/api)
- [RAG Patterns](https://learn.deeplearning.ai/courses/rag-application-development)
- [Next.js Docs](https://nextjs.org/docs)

---

## License

MIT License - See LICENSE file for details
