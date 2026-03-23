"""Force reset and reseed the knowledge base."""
import shutil
import os
import sys
sys.path.insert(0, 'backend')

from rag.knowledge_base import ChemicalKnowledgeBase, seed_knowledge_base
from config import settings

db_path = settings.VECTOR_DB_PATH

# Remove old database completely
if os.path.exists(db_path):
    shutil.rmtree(db_path)
    print(f"[OK] Cleared database: {db_path}")

# Create fresh knowledge base
os.makedirs(db_path, exist_ok=True)
kb = ChemicalKnowledgeBase(db_path)

# Seed with expanded chemical list
seed_knowledge_base(kb)
count = kb.count_chemicals()

print(f"[OK] Knowledge base reseeded with {count} chemicals")

# Verify a few chemicals
if count > 30:
    print(f"[OK] Database successfully populated with expanded list")
    results = kb.search("titanium dioxide", top_k=1)
    if results:
        print(f"  Sample retrieval test: {results[0]['name']} ({results[0]['safety_rating']})")
else:
    print(f"[ERROR] Database only has {count} chemicals (expected 40+)")
    sys.exit(1)
