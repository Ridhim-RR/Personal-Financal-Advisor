"""Seed the ChromaDB company_tickers collection with company→ticker mappings.

Run:
  poetry run python src/data/seed_company_tickers.py

This populates a ChromaDB collection used by the Ticker Resolver for RAG-based
company name to ticker symbol resolution.
"""

import json
import os
import chromadb
from chromadb.config import Settings


COLLECTION_NAME = "company_tickers"
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".chroma")
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "company_tickers.json")


def seed_company_tickers():
    client = chromadb.PersistentClient(
        path=PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )

    # Delete existing collection if present
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    with open(DATA_FILE) as f:
        entries = json.load(f)

    ids = []
    documents = []
    metadatas = []

    for i, entry in enumerate(entries):
        # The document text includes company name, aliases, sector, and exchange
        aliases_str = ", ".join(entry.get("aliases", []))
        doc_text = (
            f"Company: {entry['company']}. "
            f"Aliases: {aliases_str}. "
            f"Sector: {entry.get('sector', '')}. "
            f"Exchange: {entry.get('exchange', '')}. "
            f"Ticker: {entry['ticker']}."
        )
        ids.append(str(i))
        documents.append(doc_text)
        metadatas.append({
            "company": entry["company"],
            "ticker": entry["ticker"],
            "sector": entry.get("sector", ""),
            "exchange": entry.get("exchange", ""),
        })

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"  Seeded {len(entries)} company→ticker mappings into '{COLLECTION_NAME}'")
    print(f"  Persist dir: {PERSIST_DIR}")


if __name__ == "__main__":
    seed_company_tickers()
