import httpx
from config import SUPERMEMORY_API_KEY

BASE = "https://api.supermemory.ai/v3"
CHUNK_SIZE = 500


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Split text into paragraph-based chunks of approximately chunk_size characters."""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        para_length = len(paragraph)

        # If adding this paragraph would exceed chunk_size, save current chunk
        if current_length + para_length > chunk_size and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(paragraph)
        current_length += para_length

    # Add remaining text
    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks


async def store_profile(business_id: int, text: str) -> bool:
    """
    Chunk business profile text and store in Supermemory.
    Each chunk is stored with containerTag=business_id for retrieval.
    """
    if not SUPERMEMORY_API_KEY:
        print("[SUPERMEMORY] No API key configured, skipping storage")
        return False

    if not text.strip():
        print(f"[SUPERMEMORY] Empty text for business {business_id}, skipping")
        return False

    chunks = _chunk_text(text)
    print(f"[SUPERMEMORY] Storing {len(chunks)} chunks for business {business_id}")

    headers = {
        "Authorization": f"Bearer {SUPERMEMORY_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, chunk in enumerate(chunks):
            try:
                response = await client.post(
                    f"{BASE}/ingest/add-document",
                    json={
                        "content": chunk,
                        "containerTag": str(business_id),
                        "metadata": {
                            "business_id": business_id,
                            "source": "website",
                            "chunk_index": i
                        }
                    },
                    headers=headers
                )
                response.raise_for_status()
                print(f"[SUPERMEMORY] Stored chunk {i+1}/{len(chunks)} for business {business_id}")
            except Exception as e:
                print(f"[SUPERMEMORY] Failed to store chunk {i}: {e}")
                return False

    return True


async def query_profile(business_id: int, query: str, limit: int = 3) -> str:
    """
    Query Supermemory for relevant chunks of a business profile.
    Returns joined text of top-k relevant chunks.
    """
    if not SUPERMEMORY_API_KEY:
        print("[SUPERMEMORY] No API key configured, returning empty context")
        return ""

    if not query.strip():
        return ""

    headers = {
        "Authorization": f"Bearer {SUPERMEMORY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE}/recall-search/search-memory-entries",
                json={
                    "query": query,
                    "containerTag": str(business_id),
                    "limit": limit
                },
                headers=headers
            )
            response.raise_for_status()
            results = response.json()

            # Extract content from memory entries
            if isinstance(results, dict) and "data" in results:
                entries = results["data"]
            elif isinstance(results, list):
                entries = results
            else:
                entries = []

            # Join the content from retrieved chunks
            chunks = [entry.get("content", "") for entry in entries if entry.get("content")]

            if chunks:
                print(f"[SUPERMEMORY] Retrieved {len(chunks)} relevant chunks for business {business_id}")
                return "\n\n".join(chunks)
            else:
                print(f"[SUPERMEMORY] No relevant chunks found for business {business_id}")
                return ""

    except Exception as e:
        print(f"[SUPERMEMORY] Query failed: {e}")
        return ""


async def update_memory(memory_id: str, content: str) -> bool:
    """Update a specific memory entry (for email reply updates)."""
    if not SUPERMEMORY_API_KEY:
        print("[SUPERMEMORY] No API key configured")
        return False

    headers = {
        "Authorization": f"Bearer {SUPERMEMORY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE}/content-management/update-a-memory-creates-new-version",
                json={
                    "id": memory_id,
                    "content": content
                },
                headers=headers
            )
            response.raise_for_status()
            print(f"[SUPERMEMORY] Updated memory {memory_id}")
            return True
    except Exception as e:
        print(f"[SUPERMEMORY] Failed to update memory {memory_id}: {e}")
        return False
