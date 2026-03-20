# IngredientIQ Architecture & Design Document

## System Overview

IngredientIQ is a production-ready AI application that demonstrates advanced LLM patterns: RAG (Retrieval-Augmented Generation) and MCP (Model Context Protocol).

The system answers: **"Is this ingredient safe?"** by combining:

1. **Grounded Knowledge** - Facts from chemical databases (not hallucinations)
2. **Reasoning** - Claude LLM analyzes with evidence
3. **Citations** - Sources backing each classification
4. **Fallback** - Live API lookups when needed

---

## Architecture Layers

### 1. Presentation Layer (Frontend)

**Technology:** Next.js 14, React 18, TailwindCSS, TypeScript

```
User Interface
├── Product Search
│   └── TextField → "Neutrogena Sunscreen" → API Call
├── Image Upload
│   └── File → Base64 → Claude Vision → Ingredients
└── Results View
    ├── Overall Score Card
    ├── Safety Badges
    ├── Ingredient Cards
    │   ├── Rating
    │   ├── Reasoning
    │   ├── Hazards List
    │   ├── Sources List
    │   └── Confidence Meter
    └── Export Actions
```

**Key Files:**

- `app/page.tsx` - Main application shell
- `components/ProductSearch.tsx` - Text input handler
- `components/ImageUpload.tsx` - File handling + preview
- `components/ProductAnalysisResults.tsx` - Results display
- `components/IngredientCard.tsx` - Per-ingredient detail
- `lib/api.ts` - HTTP client for backend API

**Data Flow:**

```
User Input → Component State → API Call → Response → UI Update
```

---

### 2. API Layer (FastAPI Backend)

**Technology:** Python 3.11, FastAPI, Pydantic, CORS middleware

**Endpoints:**

| Endpoint                       | Method | Purpose                               |
| ------------------------------ | ------ | ------------------------------------- |
| `/health`                      | GET    | Health check                          |
| `/api/v1/analyze-product`      | POST   | Product name → ingredients → analysis |
| `/api/v1/analyze-ingredients`  | POST   | Raw ingredients list → analysis       |
| `/api/v1/analyze-image`        | POST   | Image upload → OCR → analysis         |
| `/api/v1/ingredient-search`    | GET    | Single ingredient lookup              |
| `/api/v1/tools`                | GET    | List MCP tools                        |
| `/api/v1/knowledge-base-stats` | GET    | KB metrics                            |

**Request/Response Cycle:**

```
HTTP Request
    ↓
FastAPI Router
    ↓
Request Validation (Pydantic)
    ↓
Business Logic Handler
    ↓
RAG/MCP Processing
    ↓
Response Serialization
    ↓
HTTP Response (JSON)
```

**Key Files:**

- `main.py` - FastAPI application + endpoints
- `config.py` - Environment & settings management

---

### 3. RAG Pipeline Layer

**Technology:** LangChain, ChromaDB, OpenAI Embeddings, Claude LLM

The RAG (Retrieval-Augmented Generation) pipeline is the core innovation:

#### Step 1: Knowledge Base Ingestion

```
Raw Chemical Data
    ↓
Chunking (1000 chars, 200 overlap)
    ↓
Embedding Generation (text-embedding-3-small)
    ↓
Vector Storage (ChromaDB)
```

**What's Stored:**

- Chemical name (exact + normalized)
- CAS registry number
- Safety rating (SAFE/CAUTION/HARMFUL/UNKNOWN)
- Hazard descriptions
- Source citations
- Full chemical description

#### Step 2: Query Processing

```
"Is sodium lauryl sulfate safe?"
    ↓
Embedding: text-embedding-3-small
    ↓
Similarity Search: ChromaDB
    ↓
Top-5 Results Retrieved
```

#### Step 3: Context Formatting

```
[Retrieved Docs]
    ↓
Format as Human-Readable Context
```

Example formatted context:

```
Record 1:
- Chemical Name: Sodium Lauryl Sulfate
- CAS Number: 151-21-3
- Safety Rating: CAUTION
- Hazards: Skin irritation at high concentrations
- Sources: EWG Skin Deep, PubChem
- Similarity Score: 98%
```

#### Step 4: LLM Analysis with Evidence

```
Prompt:
  "Based on database records, classify this ingredient..."

  [Context: Database matches]

  JSON Response:
  {
    "ingredient_name": "sodium lauryl sulfate",
    "safety_rating": "CAUTION",
    "reasoning": "Common surfactant... can cause irritation...",
    "hazards": ["skin irritation"],
    "sources": ["EWG Skin Deep", "PubChem"],
    "confidence_score": 0.87
  }
```

#### Step 5: Aggregation

```
Per-Ingredient Results
    ↓
Calculate Overall Score
    ↓
Determine Product Rating
    ↓
Package Evidence
    ↓
Return Structured Response
```

**Safety Score Calculation:**

```
Score = (SAFE_count * 100 + CAUTION_count * 60 + HARMFUL_count * 0) / (total * 100)
```

**Key Files:**

- `rag/knowledge_base.py` - ChromaDB management
- `rag/rag_pipeline.py` - Analysis logic

---

### 4. MCP Tools Layer

**Technology:** Model Context Protocol, External APIs

MCP tools enable the LLM to take actions beyond text analysis:

| Tool                            | Purpose                              | Fallback        |
| ------------------------------- | ------------------------------------ | --------------- |
| `lookup_product`                | Find ingredients via Open Food Facts | Manual entry    |
| `search_pubchem`                | Get chemical properties              | Return UNKNOWN  |
| `parse_ingredients`             | Extract from raw text                | Regex fallback  |
| `get_ewg_rating`                | Look up EWG safety score             | Skip EWG source |
| `extract_ingredients_from_text` | OCR → ingredient list                | Manual entry    |

**How LLM Uses Tools:**

```
If ingredient not found in KB:
    ↓
Call search_pubchem(ingredient_name)
    ↓
Get live chemical data
    ↓
Use for classification
    ↓
Add to response as "live lookup"
```

**Key Files:**

- `mcp_server/tools.py` - Tool implementations

---

### 5. LLM Integration Layer

**Technology:** Anthropic Claude / OpenAI GPT, LangChain

**Supported Models:**

- Claude 3 Sonnet (default, recommended)
- Claude 3 Opus (more powerful)
- GPT-4 (alternative)
- GPT-3.5-turbo (budget)

**LLM Configuration:**

```python
model = LLMFactory.create_llm(
    provider="anthropic",
    model="claude-3-sonnet-20240229"
)

# Used in RAG pipeline
llm.invoke(prompt_with_context)
```

**Prompting Strategy:**

```
1. System Context: You are a chemical safety expert
2. Instructions: Analyze using database info only
3. Format: Required JSON structure
4. Examples: None (demonstrates reasoning)
5. Evidence: Required sources cited
```

**Key Files:**

- `llm/llm_factory.py` - LLM/Embedding creation

---

## Data Flow Examples

### Scenario 1: Product Search → Analysis

```
User Types: "Neutrogena Ultra Sheer Sunscreen"
    ↓
ProductSearch.tsx sends POST /api/v1/analyze-product
    ↓
FastAPI route processes
    ↓
MCP Tool: ProductLookupTool.lookup_product()
    ↓
Open Food Facts API returns ingredients:
  ["Zinc Oxide", "Octinoxate", "Glycerin", ...]
    ↓
For each ingredient:
    Loop → RAG Pipeline:
      Retrieve: Search ChromaDB
      Format: Context string
      Analyze: Claude evaluates
      Return: {rating, reasoning, sources, confidence}
    ↓
Aggregate results
    ↓
Calculate overall score
    ↓
Return ProductAnalysisResponse
    ↓
Frontend renders ProductAnalysisResults
```

### Scenario 2: Image Upload → Analysis

```
User Uploads: product_label.jpg
    ↓
ImageUpload.tsx sends multipart POST /api/v1/analyze-image
    ↓
FastAPI receives file bytes
    ↓
Call _extract_ingredients_from_image():
  ├─ Base64 encode image
  ├─ Send to Claude Vision API
  ├─ Extract text with OCR
  └─ Parse into ingredient list
    ↓
Extracted: ["sodium lauryl sulfate", "glycerin", ...]
    ↓
Same RAG pipeline as Scenario 1
```

### Scenario 3: Ingredient Not In KB

```
Query: "Sodium lauryl sulfate"
    ↓
ChromaDB search returns score 0.65 (below confidence threshold)
    ↓
Classification returns UNKNOWN from fallback
    ↓
LLM detects low confidence
    ↓
MCP Tool triggered: search_pubchem("sodium lauryl sulfate")
    ↓
Live API returns chemical properties
    ↓
LLM re-analyzes with live data
    ↓
Return CAUTION with PubChem source
```

---

## Knowledge Base Architecture

### Storage

**ChromaDB (Vector Database)**

```
venv/lib/python3.x/site-packages/chromadb/
└── data/
    └── chroma/
        ├── 00/              # Embedding vectors
        ├── 01/
        └── index.bin        # Vector index
```

**Collection Schema**

```
Collection: "chemical_safety"

Document {
  id: "chem_151-21-3"
  text: "Chemical: Sodium Lauryl Sulfate..."
  metadata: {
    "name": "Sodium Lauryl Sulfate",
    "cas_number": "151-21-3",
    "safety_rating": "CAUTION",
    "hazards": "Skin irritation...",
    "sources": "EWG Skin Deep, PubChem"
  }
}
```

### Embedding Strategy

**Model:** OpenAI text-embedding-3-small

- 1536 dimensions
- Optimized for semantic search
- Requires OPENAI_API_KEY

**Similarity Metric:** Cosine distance

```
distance(vec1, vec2) = 1 - (dot_product / (norm1 * norm2))
similarity_score = 1 - distance
```

### Scaling Considerations

**Local Development (Current):**

- ChromaDB local storage
- In-memory vector index
- ~10-100 chemicals practical limit

**Production Scaling:**

- Switch to Pinecone (cloud vector DB)
- Use hierarchical namespacing for product types
- Cache frequent queries
- Implement incremental ingestion

---

## Security & Privacy

### API Security

```
CORS whitelist: ["http://localhost:3000", ...]
No authentication required (demo)
Production: Add JWT/OAuth2
```

### Data Privacy

```
No user data stored
No ingredient history persisted
Knowledge base is deterministic (same for all users)
Image files deleted after processing
```

### API Key Management

```
Environment variables only (not in code)
.env NOT committed to git
.env.example shows required keys
Deploy with managed secrets (GitHub Actions, etc.)
```

---

## Error Handling

### Frontend Errors

```
try {
  const results = await api.analyzeProduct(name);
  setAnalysisResults(results);
} catch (error) {
  onError(`Failed: ${error}`);
  // Retry logic, fallback UI
}
```

### Backend Errors

```python
@app.post("/api/v1/analyze-product")
async def analyze_product(request: ProductSearchRequest):
    try:
        product = ProductLookupTool.lookup_product(...)
        if not product:
            raise HTTPException(404, "Product not found")
        # ...
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")
```

---

## Performance Considerations

### Latency Budget

```
Product Search (end-to-end):
├── Open Food Facts API: ~200ms
├── Per ingredient RAG:
│   ├── ChromaDB retrieval: ~10ms
│   ├── Claude analysis: ~2000ms (bottleneck)
│   └── Per ingredient avg: ~2200ms
├── 8 ingredients × 2.2s: ~17.6s
└── Total: ~18s

Image Upload:
├── File upload: ~500ms
├── Claude Vision OCR: ~2000ms
├── Ingredient extraction: ~500ms
├── Analysis (same as above): ~17.6s
└── Total: ~20s
```

### Optimization Strategies

1. **Parallel ingredient analysis** - Analyze 3-4 simultaneously
2. **Caching** - Store known ingredient results
3. **Batch operations** - Analyze multiple products
4. **Async processing** - Queue long tasks

---

## Deployment Architecture

### Local Development

```
bash start.sh
├─ Starts backend on port 8000
├─ Starts frontend on port 3000
└─ Knowledge base auto-seeds
```

### Docker

```
dockerfile (Backend)
├─ Python 3.11 slim
├─ Install requirements
├─ Expose port 8000
└─ CMD [python main.py]

dockerfile (Frontend)
├─ Node 18 builder
├─ npm build
├─ Nginx proxy
└─ Expose port 3000
```

### Cloud Deployment

```
Backend → Railway / AWS Lambda
├─ Environment vars: API keys
├─ Persistent storage: Pinecone or S3
└─ Logging: Cloud logging service

Frontend → Vercel / Netlify
├─ Build: npm run build
├─ Output: .next directory
├─ Environment: NEXT_PUBLIC_API_URL
└─ CDN: Global edge cache
```

---

## Future Enhancements

### Phase 2: Advanced RAG

- [ ] Multi-document chunking strategies
- [ ] Hybrid search (keyword + semantic)
- [ ] Query expansion and rewriting
- [ ] Re-ranking retrieved documents

### Phase 3: Extended MCP Tools

- [ ] Barcode scanner (mobile)
- [ ] Real-time PubChem integration
- [ ] EWG Skin Deep direct API
- [ ] User product history

### Phase 4: Production Features

- [ ] User authentication
- [ ] Ingredient watchlists
- [ ] PDF report generation
- [ ] Email notifications
- [ ] Browser extension
- [ ] Mobile app (React Native)
- [ ] Analytics dashboard

### Phase 5: ML Improvements

- [ ] Fine-tuned model on safety data
- [ ] Auto-classification confidence calibration
- [ ] Duplicate ingredient detection
- [ ] Multilingual support

---

## Testing Strategy

### Unit Tests

```python
# test_rag_pipeline.py
def test_analyze_ingredient():
    kb = ChemicalKnowledgeBase()
    rag = IngredientSafetyRAG(kb)
    result = rag.analyze_ingredient("benzene")
    assert result['safety_rating'] == 'HARMFUL'
```

### Integration Tests

```python
# test_api.py
def test_analyze_product_endpoint():
    response = client.post("/api/v1/analyze-product",
                          json={"product_name": "Dove soap"})
    assert response.status_code == 200
    assert 'overall_rating' in response.json()
```

### E2E Tests

```typescript
// e2e/analysis.test.ts
test("Search product and view results", async () => {
  await page.goto("http://localhost:3000");
  await page.fill("input", "Neutrogena");
  await page.click('button:has-text("Search")');
  await page.waitForSelector(".card");
  // Assert results visible
});
```

---

## Monitoring & Debugging

### Backend Logs

```
INFO:     Started server process [1234]
INFO:     Waiting for application startup
INFO:     Application startup complete
INFO:     127.0.0.1:12345 - POST /api/v1/analyze-product | 200 | 18234ms
```

### Frontend Errors

```
Browser DevTools → Console
Network tab shows API requests
Performance tab shows rendering time
```

### API Documentation

```
/docs (Swagger UI)
/redoc (ReDoc)
/openapi.json (OpenAPI schema)
```

---

## References

- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Guides](https://docs.trychroma.com/)
- [Claude API Reference](https://docs.anthropic.com/)
- [Next.js 14 Docs](https://nextjs.org/docs)
- [RAG Patterns](https://learn.deeplearning.ai/courses/rag-application-development)

---

**Last Updated:** March 2026  
**Maintainer:** IngredientIQ Team
