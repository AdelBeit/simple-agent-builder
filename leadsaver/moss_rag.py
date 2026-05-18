import asyncio
from moss import MossClient, DocumentInfo, QueryOptions, MutationOptions
from config import MOSS_PROJECT_ID, MOSS_PROJECT_KEY

_client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)
_loaded_indexes: set[str] = set()


def _index_name(business_id: int, name: str = "", email: str = "") -> str:
    slug = name.lower().replace(" ", "-").replace("'", "")
    # Add email prefix (without domain) for uniqueness
    email_prefix = email.split("@")[0] if email else ""
    if email_prefix:
        slug = f"{slug}-{email_prefix}"
    # Sanitize to alphanumeric + dash only
    import re
    slug = re.sub(r"[^a-z0-9-]", "", slug)[:50]
    return f"{slug}-{business_id}" if slug else f"business-{business_id}"


async def _ensure_loaded(index_name: str):
    if index_name not in _loaded_indexes:
        try:
            await _client.load_index(index_name)
            _loaded_indexes.add(index_name)
        except Exception:
            pass


async def store_profile(business_id: int, profile_text: str, name: str = "", email: str = ""):
    """Index a business profile in Moss. Creates or replaces the index."""
    index_name = _index_name(business_id, name, email)

    # Chunk by paragraph — better retrieval than one blob
    paragraphs = [p.strip() for p in profile_text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [profile_text]

    docs = [
        DocumentInfo(id=f"{business_id}-{i}", text=para)
        for i, para in enumerate(paragraphs)
    ]

    try:
        indexes = await _client.list_indexes()
        # list_indexes returns IndexInfo objects — extract name via attribute or dict access
        def _ix_name(ix):
            if hasattr(ix, "name"): return ix.name
            if hasattr(ix, "get"): return ix.get("name") or ix.get("id")
            return str(ix)
        existing = [_ix_name(ix) for ix in (indexes or [])]
        if index_name in existing:
            await _client.add_docs(index_name, docs, MutationOptions(upsert=True))
        else:
            await _client.create_index(index_name, docs, model_id="moss-minilm")
        _loaded_indexes.discard(index_name)
        print(f"[MOSS] Indexed {len(docs)} chunks for business {business_id}")
        return True
    except Exception as e:
        print(f"[MOSS] Failed to store profile for business {business_id}: {e}")
        return False


async def query_profile(business_id: int, query: str, top_k: int = 3, name: str = "", email: str = "") -> str:
    """Query Moss for the most relevant chunks for a given caller query."""
    index_name = _index_name(business_id, name, email)
    await _ensure_loaded(index_name)

    try:
        results = await _client.query(
            index_name,
            query,
            QueryOptions(top_k=top_k, alpha=0.8),
        )
        if results and results.docs:
            return "\n".join(doc.text for doc in results.docs)
    except Exception as e:
        print(f"[MOSS] Query failed for business {business_id}: {e}")

    return ""
