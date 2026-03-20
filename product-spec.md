# IngredientIQ — Product Specification

**Version:** 1.0 — Initial Draft  
**Timeline:** 8-Day Sprint  
**Status:** Planning Phase  
**Last Updated:** March 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Product Overview](#3-product-overview)
4. [Technical Architecture](#4-technical-architecture)
5. [Feature Specification](#5-feature-specification)
6. [Data Sources & Knowledge Base](#6-data-sources--knowledge-base)
7. [8-Day Build Plan](#7-8-day-build-plan)
8. [Risks & Mitigations](#8-risks--mitigations)
9. [Success Metrics](#9-success-metrics)
10. [Glossary](#10-glossary)

---

## 1. Executive Summary

**IngredientIQ** is a web application that empowers consumers to make informed decisions about the products they use daily. A user enters a product name or uploads a photo of a product label, and the app returns a color-coded safety breakdown of every ingredient — flagged as **Safe**, **Caution**, or **Harmful** — backed by citations from trusted chemical and toxicology databases.

This project is built as a learning exercise in **RAG (Retrieval-Augmented Generation)** and **MCP (Model Context Protocol)** architectures, demonstrating how AI can be grounded in specialized knowledge rather than relying on general model training alone.

> **Learning Goal:** By the end of this project you will understand how to ingest domain-specific data into a vector store (RAG), expose external tools to a language model at runtime (MCP), and orchestrate both patterns in a single AI pipeline.

---

## 2. Problem Statement

### The Challenge

Consumer product labels list dozens of chemical ingredients using technical IUPAC names that are opaque to the average user. Current options are fragmented: users must manually Google each ingredient, switch between EWG, PubChem, and toxicology papers, and synthesize conflicting information themselves.

### The Opportunity

A single AI interface that instantly retrieves, reasons over, and presents ingredient safety data can save users significant time while helping them avoid potentially harmful substances.

### Target Users

| User Segment | Primary Need |
|---|---|
| Health-conscious consumers | Quickly identify harmful chemicals in beauty, food, and cleaning products |
| Parents & caregivers | Evaluate safety of children's products, food additives, and household chemicals |
| Students & researchers | Learn about ingredient safety with cited, structured reference data |

---

## 3. Product Overview

### 3.1 Core User Flows

**Flow A — Text Search**
1. User types a product name (e.g., "Neutrogena Ultra Sheer Sunscreen")
2. App extracts ingredient list via product database lookup (MCP tool)
3. Each ingredient is analyzed via RAG pipeline against the chemical safety knowledge base
4. Results are returned as a structured safety report with color-coded badges

**Flow B — Image Upload**
1. User uploads a photo of a product label or ingredient list
2. Vision model (Claude) extracts text from the image (OCR via AI)
3. Extracted ingredient list is passed into the same RAG pipeline as Flow A
4. Identical structured safety report is returned

### 3.2 Safety Rating System

| Rating | Label | Meaning |
|---|---|---|
| ✅ | **SAFE** | Widely considered safe by regulatory agencies (FDA, EPA, EFSA). No significant adverse effects reported at normal exposure levels. |
| ⚠️ | **CAUTION** | Some studies suggest potential risks at high doses or with prolonged exposure. Acceptable in small quantities. User should be informed. |
| ❌ | **HARMFUL** | Classified as toxic, carcinogenic, endocrine-disrupting, or otherwise hazardous. Flagged by EWG, IARC, or equivalent body. |
| ❓ | **UNKNOWN** | Insufficient data in knowledge base. Raw chemical name displayed with a prompt to research further. |

---

## 4. Technical Architecture

### 4.1 Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         User Interface (React / Next.js)        │
│       Text Query  ──OR──  Image Upload          │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│     Orchestration Layer (LangChain + Claude)    │
└────────────┬────────────────────────┬───────────┘
             │                        │
             ▼                        ▼
┌────────────────────┐   ┌────────────────────────┐
│    MCP Server      │   │     RAG Pipeline        │
│                    │   │                         │
│  • Product lookup  │   │  • Embedding model      │
│  • Barcode scan    │   │  • Vector store         │
│  • EWG API         │   │    (ChromaDB)           │
│  • PubChem API     │   │  • Knowledge base       │
└────────────────────┘   └────────────────────────┘
```

### 4.2 RAG Pipeline Design

RAG (Retrieval-Augmented Generation) is the backbone of the safety analysis. Rather than relying on the LLM's memorized knowledge, the app retrieves real-time, grounded chemical data before generating a response.

| Step  | Stage      | Description                                                          |
|-------|------------|----------------------------------------------------------------------|
| 1     | **Ingest** | Scrape or load chemical safety data from EWG Skin Deep, PubChem, and | |       |            | IARC lists. Convert to chunked text documents.                       |
| 2     | **Embed**  | Generate vector embeddings for each chemical record using OpenAI     | |       |            | `text-embedding-ada-002` or a free HuggingFace model.                |
| 3     | **Store**  | Store embeddings in ChromaDB (local, free). Each vector includes     | |       |            | metadata: chemical name, CAS number, safety rating.                  |
| 4     |**Retrieve**| On query, embed the ingredient name and find top-k nearest neighbors | |       |            | in the vector store.                                                 |
| 5     |**Generate**| Pass retrieved context + ingredient name to Claude. Prompt instructs | |       |            | the model to classify the ingredient and cite its source.            |
---------------------------------------------------------------------------------------------

### 4.3 MCP Server Design

MCP (Model Context Protocol) enables the LLM to call external tools at inference time. IngredientIQ uses an MCP server to expose live data tools that the model can invoke on demand.

| Tool Name        | Trigger                   | Returns                                    |
|------------------|---------------------------|--------------------------------------------|
|`lookup_product`  | User enters a product name| Ingredient list from Open Food Facts /INCI | |                  |                           | database                                   |
|`scan_barcode`    | User uploads barcode image| Product name + ingredient list via barcode | |                  |                           | lookup API                                 |
|`fetch_ewg_rating`| Ingredient not  in RAG    | Live EWG Skin Deep safety score for the    | |                  |                           | chemical                                   |
| `search_pubchem` | Deep analysis requested   | PubChem compound data: hazard flags, LD50, | |                  |                           | regulatory status                          |
---------------------------------------------------------------------------------------------

### 4.4 Tech Stack

| Layer        | Technology             |Why                                                |
|--------------|------------------------|---------------------------------------------------|
| Frontend     | Next.js + Tailwind CSS | Fast React framework; easy file upload UX         |
| LLM          | Claude/ Gemini/ openAI | Vision support for image analysis;strong reasoning| 
| Orchestration| LangChain/ LlamaIndex  | Built-in RAG chains and agent tools               |
| Embeddings   | OpenAI ada-002/ all-MiniLM | High quality; ada-002 is industry standard    |
| Vector DB    | ChromaDB (local)       | Free, runs locally, easy Python API — learning    |
| MCP Server   | MCP SDK (Python)       | Official SDK; connects tools to Claude            |
| Product Data | Open Food Facts API    | Free, open, no key required for basic use         |
| Chemical Data| PubChem REST API       | Free, authoritative, no key required              |

---

## 5. Feature Specification

### 5.1 MVP Features

| Feature | Description | Technology | Target Day |
|---|---|---|---|
| Product Search | Text input to search by product name or brand | Open Food Facts MCP | Day 2 |
| Image Upload | Upload label photo; AI extracts ingredient list via OCR | Claude Vision API | Day 3 |
| Ingredient Parser | Parse raw ingredient string into individual chemical names | LLM prompt + regex | Day 2 |
| Safety Lookup | Per-ingredient safety classification via RAG | ChromaDB + Claude | Day 4 |
| Safety Report UI | Color-coded ingredient cards (Safe / Caution / Harmful) | React + Tailwind | Day 5 |
| Source Citations | Each rating shows source (EWG, PubChem, IARC) | RAG metadata | Day 5 |
| Overall Score | Aggregate product safety score (0–100) | Scoring algorithm | Day 6 |
| Live Fallback | If RAG misses, call PubChem API live via MCP | MCP Tool | Day 6 |

### 5.2 Post-MVP Stretch Goals

- Barcode scanner via camera (mobile UX)
- Side-by-side product comparison view
- User-created watchlist of ingredients to always flag
- Browser extension for scanning products while shopping online
- Export safety report as PDF

---

## 6. Data Sources & Knowledge Base

The RAG knowledge base should be populated from authoritative, freely available data sources.

| Source | Data Type | Access Method | License |
|---|---|---|---|
| EWG Skin Deep | Cosmetic ingredient hazard scores (1–10) | Web scrape or CSV download | Free / Attribution |
| PubChem | Chemical properties, GHS hazard flags | REST API (no key required) | Public Domain |
| IARC Monographs | Carcinogen classifications (Group 1, 2A, 2B) | PDF → parse → load | WHO Open Access |
| Open Food Facts | Food product ingredient lists | REST API (no key required) | ODbL Open License |
| FDA GRAS List | Generally Recognized as Safe food additives | CSV from FDA.gov | US Gov / Public |

> **Tip:** Start with PubChem + FDA GRAS as your primary data sources — they are the most accessible and structured. Add EWG data once the pipeline is working.

---

## 7. 8-Day Build Plan

| Day | Tasks | Milestone |
|---|---|---|
| **Day 1** | Set up repo, install dependencies (LangChain, ChromaDB, Next.js). Read MCP and RAG docs. Design data schema for ingredients. | ✅ Dev environment ready |
| **Day 2** | Build MCP server with `lookup_product` tool. Connect Open Food Facts API. Write ingredient parser prompt. Test with 5 products. | ✅ Product → ingredients working |
| **Day 3** | Ingest EWG + PubChem data into ChromaDB. Write embedding pipeline. Test basic semantic search for chemical names. | ✅ RAG knowledge base populated |
| **Day 4** | Wire RAG pipeline to Claude. For each ingredient, retrieve context and generate safety classification. Add citations. | ✅ Per-ingredient AI analysis working |
| **Day 5** | Build frontend: search bar, image upload, ingredient card components with color-coded safety badges. | ✅ Working UI end-to-end |
| **Day 6** | Add overall product score, MCP fallback to live PubChem API, handle Unknown ingredients gracefully. | ⏳ Polish & edge cases |
| **Day 7** | Image upload + Claude Vision OCR flow. Test with 20 real product photos. Fix parsing errors. | ⏳ Image flow complete |
| **Day 8** | QA testing, bug fixes, deploy to Vercel + Railway. Write README with architecture diagram. | ⏳ Shipped & documented |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| EWG data scraping blocked | Knowledge base too small; low coverage | Use PubChem + FDA GRAS list as primary; EWG as supplement |
| Ingredient name mismatch | RAG retrieval misses correct record | Normalize names via CAS number lookup before embedding |
| LLM hallucination | Incorrect safety rating shown to user | Always show source citation; add disclaimer banner in UI |
| Image OCR failures | Cannot extract ingredients from noisy photos | Fallback to manual text entry; show OCR confidence score |
| Scope creep | Project not finished in 8 days | Lock MVP features by Day 2; treat stretch goals as optional |
| API rate limits | PubChem or Open Food Facts throttles requests | Cache responses locally; implement exponential backoff |

---

## 9. Success Metrics

### Functional Acceptance Criteria (MVP is done when...)

- [ ] User can search any product by name and receive a safety report within 10 seconds
- [ ] User can upload a photo and receive ingredient extraction + safety analysis
- [ ] At least 80% of common cosmetic/food ingredients are covered in the knowledge base
- [ ] Every safety rating shows at least one cited source
- [ ] App handles unknown ingredients gracefully without crashing

### Learning Acceptance Criteria

- [ ] You can explain the difference between RAG and fine-tuning to a non-technical audience
- [ ] You can describe what MCP is and why it's more flexible than hardcoded tool calls
- [ ] You understand how vector embeddings enable semantic search
- [ ] You can extend the system by adding a new MCP tool or a new data source to the RAG store

---

## 10. Glossary

| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation — a pattern where relevant documents are fetched from a knowledge base and injected into the LLM prompt before generation. |
| **MCP** | Model Context Protocol — an open standard that lets LLMs call external tools and data sources in a structured, safe way at inference time. |
| **Vector Store** | A database optimized for storing and searching high-dimensional vectors (embeddings), enabling semantic similarity search. |
| **Embedding** | A numerical representation of text in high-dimensional space, where semantically similar texts are close to each other. |
| **ChromaDB** | An open-source, locally-runnable vector database well-suited for learning and prototyping RAG applications. |
| **INCI** | International Nomenclature of Cosmetic Ingredients — standardized naming system for cosmetic chemicals. |
| **EWG** | Environmental Working Group — non-profit that publishes consumer product safety ratings via the Skin Deep database. |
| **CAS Number** | A unique numeric identifier assigned to every chemical substance, used to reliably match ingredient names across databases. |

---

> **Note:** This is a living document. Update it as your understanding of the project evolves — particularly the architecture section after you have built the RAG pipeline and MCP server for the first time.
