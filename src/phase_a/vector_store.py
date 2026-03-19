"""
Phase A — Vector Store
Handles embedding generation (OpenAI) and Pinecone upsert/query.
All other modules call find_relevant_tables() to get schema context.
"""

from __future__ import annotations
from openai import OpenAI
import pinecone
from config import settings

_openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
_pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)


def _get_index():
    return _pc.Index(settings.PINECONE_INDEX_NAME)


def _embed(text: str) -> list[float]:
    response = _openai_client.embeddings.create(
        input=text,
        model=settings.EMBEDDING_MODEL,
    )
    return response.data[0].embedding


def embed_and_store(metadata: list[dict]) -> None:
    """
    Embeds each table's DDL blob and upserts into Pinecone.
    Called by schema_collector.py during setup / schema refresh.

    Args:
        metadata: List of {"table": "schema.table", "ddl": "..."} dicts
    """
    index = _get_index()
    vectors = []

    for item in metadata:
        text = f"Table: {item['table']}\nColumns:\n{item['ddl']}"
        embedding = _embed(text)
        vectors.append({
            "id": item["table"].replace(".", "_").replace(" ", "_"),
            "values": embedding,
            "metadata": {
                "table": item["table"],
                "ddl": item["ddl"],
            },
        })

    # Upsert in batches of 100 to stay within Pinecone request limits
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i : i + batch_size])

    print(f"Upserted {len(vectors)} table embeddings into '{settings.PINECONE_INDEX_NAME}'.")


def find_relevant_tables(question: str, top_k: int | None = None) -> list[str]:
    """
    Semantic search: given a natural-language question or broken SQL fragment,
    returns the DDL blobs of the most relevant tables.

    Args:
        question: e.g. "Where is the fraud data?" or a broken SQL string
        top_k:    Number of tables to return (defaults to settings.VECTOR_TOP_K)

    Returns:
        List of DDL strings, most relevant first.

    Example:
        >>> find_relevant_tables("paid claims per member")
        ["  ClaimKey INT NOT NULL\\n  MemberKey INT NOT NULL ...", ...]
    """
    k = top_k or settings.VECTOR_TOP_K
    index = _get_index()
    query_embedding = _embed(question)
    results = index.query(
        vector=query_embedding,
        top_k=k,
        include_metadata=True,
    )
    return [match["metadata"]["ddl"] for match in results["matches"]]
