import os
from typing import Optional

import chromadb
from chromadb.config import Settings


def get_chroma_client(persist_dir: Optional[str] = None):
    host = os.getenv("CHROMA_HOST")
    if host:
        port = int(os.getenv("CHROMA_PORT", "8000"))
        return chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(anonymized_telemetry=False),
        )
    path = persist_dir or os.path.join(
        os.path.dirname(__file__), "..", "..", ".chroma"
    )
    return chromadb.PersistentClient(
        path=path,
        settings=Settings(anonymized_telemetry=False),
    )
