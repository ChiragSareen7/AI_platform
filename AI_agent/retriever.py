from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import settings
from embeddings import get_embedding_model


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


# Updated chunking for better context coverage around key facts
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 300

# After category filtering: fewer, more relevant results
TOP_K = 3
# Legacy: used when fallback searches all docs (also use TOP_K)
TOP_K_FALLBACK = 3
RELEVANCE_THRESHOLD = 0.3

# Categories for document routing (must match metadata "category")
CATEGORIES = ("hiring", "products", "policies", "security", "general")
_QDRANT_CLIENT = None
_PINECONE_INDEX = None


def _category_from_filename(filename: str) -> str:
    """
    Infer document category from source file name for metadata.
    Returns one of: hiring, products, policies, security, general.
    """
    name = filename.lower()
    if any(k in name for k in ("hiring", "career", "job", "internship", "recruit", "careers")):
        return "hiring"
    if any(k in name for k in ("product", "platform", "acquisition")):
        return "products"
    if any(k in name for k in ("policy", "policies", "rules", "compliance")):
        return "policies"
    if any(k in name for k in ("security", "secure")):
        return "security"
    return "general"


def detect_category(query: str) -> str:
    """
    Rule-based category detection from query text.
    - internship, hiring → hiring
    - product, platform → products
    - policy, rules → policies
    - security → security
    - else → general
    """
    if not query or not query.strip():
        return "general"
    text = query.lower().strip()
    if any(k in text for k in ("internship", "internships", "hiring", "job", "jobs", "career", "careers", "recruit", "recruitment")):
        return "hiring"
    if any(
        k in text
        for k in (
            "product",
            "products",
            "platform",
            "feature",
            "features",
            "acquisition",
            "acquire",
            "acquired",
            "acquires",
            "merger",
            "merge",
        )
    ):
        return "products"
    if any(k in text for k in ("policy", "policies", "rules", "rule", "compliance")):
        return "policies"
    if any(k in text for k in ("security", "secure")):
        return "security"
    return "general"


def _load_pdfs_from_directory(data_dir: Path) -> List[Document]:
    """
    Load all PDFs from the data directory.
    Adds metadata: source (file name), category (hiring|products|policies|security|general).
    """
    documents: List[Document] = []
    pdf_paths = sorted(data_dir.glob("*.pdf"))
    if not pdf_paths:
        logger.warning("No PDF files found in data directory: %s", data_dir)

    for pdf_path in pdf_paths:
        logger.info("Loading PDF: %s", pdf_path.name)
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        category = _category_from_filename(pdf_path.name)
        for d in docs:
            # Always preserve normalized source file name for downstream consumers.
            d.metadata["source"] = str(pdf_path.name)
            d.metadata["category"] = category
        documents.extend(docs)

    logger.info("Total raw documents loaded: %d", len(documents))
    return documents


def _chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split documents into overlapping chunks for RAG.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    # Debug: number of chunks per source file
    per_file_counts: dict[str, int] = {}
    for c in chunks:
        src = c.metadata.get("source", "unknown")
        per_file_counts[src] = per_file_counts.get(src, 0) + 1

    logger.info("Chunking summary (chunk_size=%d, overlap=%d):", CHUNK_SIZE, CHUNK_OVERLAP)
    for src, count in per_file_counts.items():
        logger.info("  %s -> %d chunks", src, count)

    return chunks


def _build_or_load_faiss_vector_store(embeddings: Any) -> FAISS:
    """
    Build the FAISS vector store from PDFs if not present, otherwise load it from disk.
    Set FORCE_REBUILD_VECTOR_STORE=true in env to force rebuild when data changes.
    """
    vector_store_dir = settings.vector_store_dir
    index_dir = vector_store_dir / "faiss_index"

    force_rebuild = os.getenv("FORCE_REBUILD_VECTOR_STORE", "false").lower() == "true"

    if index_dir.exists() and not force_rebuild:
        logger.info("Loading existing FAISS index from %s", index_dir)
        return FAISS.load_local(
            folder_path=str(index_dir),
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )

    if force_rebuild and index_dir.exists():
        logger.info("FORCE_REBUILD_VECTOR_STORE=true, rebuilding FAISS index at %s", index_dir)

    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    documents = _load_pdfs_from_directory(data_dir)
    if not documents:
        logger.warning("No documents loaded; creating empty FAISS index.")
        vector_store = FAISS.from_texts([""], embeddings)
    else:
        chunks = _chunk_documents(documents)
        logger.info("Total chunks to embed: %d", len(chunks))
        vector_store = FAISS.from_documents(chunks, embeddings)

    index_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_dir))
    logger.info("Saved FAISS index to %s (with category metadata)", index_dir)
    return vector_store


def _get_qdrant_client():
    from qdrant_client import QdrantClient
    global _QDRANT_CLIENT

    if _QDRANT_CLIENT is not None:
        return _QDRANT_CLIENT

    qdrant_path = str(Path(settings.qdrant_path).resolve())
    if settings.qdrant_url:
        try:
            remote_client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
            remote_client.get_collections()
            logger.info("Using remote Qdrant at %s", settings.qdrant_url)
            _QDRANT_CLIENT = remote_client
            return _QDRANT_CLIENT
        except Exception as exc:
            logger.warning(
                "Remote Qdrant unavailable (%s). Falling back to local path: %s",
                str(exc),
                qdrant_path,
            )
    logger.info("Using local Qdrant at path: %s", qdrant_path)
    _QDRANT_CLIENT = QdrantClient(path=qdrant_path)
    return _QDRANT_CLIENT


def _ensure_qdrant_collection(embeddings: Any):
    from qdrant_client.http import models as rest
    from qdrant_client.models import PointStruct

    force_rebuild = os.getenv("FORCE_REBUILD_VECTOR_STORE", "false").lower() == "true"
    collection_name = settings.qdrant_collection_name
    client = _get_qdrant_client()

    def _collection_exists() -> bool:
        try:
            client.get_collection(collection_name=collection_name)
            return True
        except Exception:
            return False

    exists = _collection_exists()
    if exists and not force_rebuild:
        logger.info("Loading existing Qdrant collection '%s'", collection_name)
        return client

    logger.info(
        "Building Qdrant collection '%s' (force_rebuild=%s)",
        collection_name,
        str(force_rebuild),
    )
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    documents = _load_pdfs_from_directory(data_dir)
    chunks = _chunk_documents(documents) if documents else []
    logger.info("Total chunks to embed into Qdrant: %d", len(chunks))

    if exists:
        client.delete_collection(collection_name=collection_name)
    dim = len(embeddings.embed_query("nexora vector dimension probe"))
    client.create_collection(
        collection_name=collection_name,
        vectors_config=rest.VectorParams(size=dim, distance=rest.Distance.COSINE),
    )

    points = []
    if not chunks:
        points.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, "nexora:empty:0")),
                vector=embeddings.embed_query(""),
                payload={
                    "page_content": "",
                    "metadata": {"source": "empty", "category": "general", "page": 0},
                },
            )
        )
    else:
        for idx, chunk in enumerate(chunks):
            meta = dict(chunk.metadata or {})
            source = str(meta.get("source", "unknown"))
            page = str(meta.get("page", 0))
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}:{page}:{idx}"))
            points.append(
                PointStruct(
                    id=pid,
                    vector=embeddings.embed_query(chunk.page_content),
                    payload={"page_content": chunk.page_content, "metadata": meta},
                )
            )

    batch_size = 64
    for i in range(0, len(points), batch_size):
        client.upsert(
            collection_name=collection_name,
            points=points[i : i + batch_size],
            wait=True,
        )

    logger.info("Saved/updated Qdrant collection '%s'", collection_name)
    return client


def _qdrant_similarity_search_with_scores(
    query: str, k: int, category: str
) -> List[Tuple[Document, float]]:
    from qdrant_client.http import models as rest

    embeddings = get_embedding_model()
    client = _ensure_qdrant_collection(embeddings)
    collection_name = settings.qdrant_collection_name
    query_vector = embeddings.embed_query(query)

    def _to_results(response) -> List[Tuple[Document, float]]:
        points = list(getattr(response, "points", []) or [])
        out: List[Tuple[Document, float]] = []
        for p in points:
            payload = getattr(p, "payload", {}) or {}
            meta = payload.get("metadata", {}) or {}
            text = payload.get("page_content", "") or ""
            out.append((Document(page_content=text, metadata=meta), float(getattr(p, "score", 0.0))))
        return out

    filtered = rest.Filter(
        must=[
            rest.FieldCondition(
                key="metadata.category",
                match=rest.MatchValue(value=category),
            )
        ]
    )
    filtered_resp = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=filtered,
        limit=k,
        with_payload=True,
        with_vectors=False,
    )
    results = _to_results(filtered_resp)
    docs_searched = f"category={category} (filtered)"

    if not results:
        logger.info("[RAG routing] no results in category; fallback: searching all docs")
        all_resp = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=TOP_K_FALLBACK,
            with_payload=True,
            with_vectors=False,
        )
        results = _to_results(all_resp)
        docs_searched = "all (fallback)"
    elif float(results[0][1]) < RELEVANCE_THRESHOLD:
        logger.info(
            "[RAG routing] best score %.4f < threshold %.2f; fallback: searching all docs",
            float(results[0][1]),
            RELEVANCE_THRESHOLD,
        )
        all_resp = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=TOP_K_FALLBACK,
            with_payload=True,
            with_vectors=False,
        )
        results = _to_results(all_resp)
        docs_searched = "all (fallback)"

    logger.info("[RAG routing] docs_searched=%s", docs_searched)
    return results


def _get_pinecone_index():
    global _PINECONE_INDEX
    if _PINECONE_INDEX is not None:
        return _PINECONE_INDEX

    try:
        from pinecone import Pinecone, ServerlessSpec
    except ImportError as exc:
        raise ImportError(
            "pinecone package is not installed. Run: pip install pinecone"
        ) from exc

    if not settings.pinecone_api_key:
        raise ValueError("PINECONE_API_KEY is missing for VECTOR_DB_PROVIDER=pinecone")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    index_name = settings.pinecone_index_name
    existing = [i.get("name") for i in pc.list_indexes()]
    if index_name not in existing:
        logger.info(
            "Creating Pinecone index '%s' (dim=%d metric=%s cloud=%s region=%s)",
            index_name,
            settings.pinecone_dimension,
            settings.pinecone_metric,
            settings.pinecone_cloud,
            settings.pinecone_region,
        )
        pc.create_index(
            name=index_name,
            dimension=settings.pinecone_dimension,
            metric=settings.pinecone_metric,
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )
    _PINECONE_INDEX = pc.Index(index_name)
    return _PINECONE_INDEX


def _ensure_pinecone_index(embeddings: Any):
    force_rebuild = os.getenv("FORCE_REBUILD_VECTOR_STORE", "false").lower() == "true"
    namespace = settings.pinecone_namespace
    index = _get_pinecone_index()

    # If namespace has vectors and rebuild not forced, reuse.
    try:
        stats = index.describe_index_stats()
        ns_stats = (stats.get("namespaces") or {}).get(namespace) or {}
        if ns_stats.get("vector_count", 0) > 0 and not force_rebuild:
            logger.info(
                "Using existing Pinecone namespace '%s' with %s vectors",
                namespace,
                ns_stats.get("vector_count"),
            )
            return index
    except Exception:
        # Continue with rebuild flow if stats unavailable.
        pass

    logger.info(
        "Building Pinecone namespace '%s' (force_rebuild=%s)",
        namespace,
        str(force_rebuild),
    )
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    documents = _load_pdfs_from_directory(data_dir)
    chunks = _chunk_documents(documents) if documents else []
    logger.info("Total chunks to embed into Pinecone: %d", len(chunks))

    # Clear namespace for deterministic rebuild (ignore if namespace is absent).
    try:
        index.delete(delete_all=True, namespace=namespace)
    except Exception as exc:
        logger.info("Pinecone namespace clear skipped: %s", str(exc))

    vectors = []
    if not chunks:
        vectors.append(
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "nexora:empty:0")),
                "values": embeddings.embed_query(""),
                "metadata": {
                    "source": "empty",
                    "category": "general",
                    "page": 0,
                    "text": "",
                },
            }
        )
    else:
        for idx, chunk in enumerate(chunks):
            meta = dict(chunk.metadata or {})
            source = str(meta.get("source", "unknown"))
            page = int(meta.get("page", 0))
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}:{page}:{idx}"))
            vectors.append(
                {
                    "id": pid,
                    "values": embeddings.embed_query(chunk.page_content),
                    "metadata": {
                        **meta,
                        "source": source,
                        "page": page,
                        "text": chunk.page_content,
                    },
                }
            )

    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i : i + batch_size], namespace=namespace)

    logger.info(
        "Saved/updated Pinecone index '%s' namespace '%s' with %d vectors",
        settings.pinecone_index_name,
        namespace,
        len(vectors),
    )
    return index


def _pinecone_similarity_search_with_scores(
    query: str, k: int, category: str
) -> List[Tuple[Document, float]]:
    embeddings = get_embedding_model()
    index = _ensure_pinecone_index(embeddings)
    namespace = settings.pinecone_namespace
    query_vector = embeddings.embed_query(query)

    def _query(filter_value):
        kwargs = {
            "vector": query_vector,
            "top_k": k if filter_value is not None else TOP_K_FALLBACK,
            "namespace": namespace,
            "include_values": False,
            "include_metadata": True,
        }
        if filter_value is not None:
            kwargs["filter"] = {"category": {"$eq": filter_value}}
        return index.query(**kwargs)

    def _to_results(resp) -> List[Tuple[Document, float]]:
        matches = list((resp or {}).get("matches", []) or [])
        # stable sorting for determinism
        matches.sort(key=lambda m: (-float(m.get("score", 0)), str(m.get("id", ""))))
        out: List[Tuple[Document, float]] = []
        for m in matches:
            meta = dict(m.get("metadata") or {})
            text = str(meta.get("text", ""))
            out.append((Document(page_content=text, metadata=meta), float(m.get("score", 0))))
        return out

    results = _to_results(_query(category))
    docs_searched = f"category={category} (filtered)"
    if not results:
        logger.info("[RAG routing] no results in category; fallback: searching all docs")
        results = _to_results(_query(None))
        docs_searched = "all (fallback)"
    elif float(results[0][1]) < RELEVANCE_THRESHOLD:
        logger.info(
            "[RAG routing] best score %.4f < threshold %.2f; fallback: searching all docs",
            float(results[0][1]),
            RELEVANCE_THRESHOLD,
        )
        results = _to_results(_query(None))
        docs_searched = "all (fallback)"
    logger.info("[RAG routing] docs_searched=%s", docs_searched)
    return results


def build_or_load_vector_store() -> Any:
    """
    Build or load the configured vector store provider.
    Providers:
    - qdrant (default)
    - pinecone
    - faiss
    """
    embeddings = get_embedding_model()
    provider = (settings.vector_db_provider or "qdrant").lower()
    logger.info("Vector DB provider selected: %s", provider)

    if provider == "qdrant":
        # Qdrant retrieval uses direct qdrant-client path.
        return "qdrant"
    if provider == "pinecone":
        # Pinecone retrieval uses direct pinecone client path.
        return "pinecone"
    if provider == "faiss":
        return _build_or_load_faiss_vector_store(embeddings)

    raise ValueError(
        f"Unsupported VECTOR_DB_PROVIDER={provider}. Use 'qdrant', 'pinecone', or 'faiss'."
    )


def similarity_search_with_scores(
    query: str, k: int = TOP_K
) -> List[Tuple[Document, float]]:
    """
    Run similarity search with relevance scores.
    Uses category routing: search only relevant category first; fallback to all docs if no good results.
    """
    category = detect_category(query)
    logger.info("[RAG routing] query=%r -> detected_category=%s", query, category)
    provider = (settings.vector_db_provider or "qdrant").lower()
    if provider == "qdrant":
        results = _qdrant_similarity_search_with_scores(query=query, k=k, category=category)
        docs_searched = "qdrant-routed"
    elif provider == "pinecone":
        results = _pinecone_similarity_search_with_scores(query=query, k=k, category=category)
        docs_searched = "pinecone-routed"
    else:
        vector_store = build_or_load_vector_store()

        # 1) Search only in the detected category (metadata filter)
        filter_dict = {"category": category}
        results = vector_store.similarity_search_with_relevance_scores(
            query, k=k, filter=filter_dict
        )
        docs_searched = "category=%s (filtered)" % category
        logger.info("[RAG routing] docs_searched=%s", docs_searched)

        # 2) Fallback: if no results or best score below threshold, search all docs
        if not results:
            logger.info("[RAG routing] no results in category; fallback: searching all docs")
            results = vector_store.similarity_search_with_relevance_scores(query, k=TOP_K_FALLBACK)
            docs_searched = "all (fallback)"
        elif results and float(results[0][1]) < RELEVANCE_THRESHOLD:
            logger.info(
                "[RAG routing] best score %.4f < threshold %.2f; fallback: searching all docs",
                float(results[0][1]),
                RELEVANCE_THRESHOLD,
            )
            results = vector_store.similarity_search_with_relevance_scores(query, k=TOP_K_FALLBACK)
            docs_searched = "all (fallback)"

    logger.info("[RAG routing] final docs_searched=%s, num_results=%d", docs_searched, len(results))
    for i, (doc, score) in enumerate(results):
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        cat = doc.metadata.get("category", "?")
        snippet = doc.page_content[:200].replace("\n", " ")
        logger.info(
            "  #%d score=%.4f source=%s category=%s page=%s snippet=%s",
            i + 1,
            float(score),
            src,
            cat,
            page,
            snippet,
        )
    return results


def test_retrieval(query: str, k: int = TOP_K) -> None:
    """
    Helper for manual testing of retriever quality without the LLM.
    Example:
        from retriever import test_retrieval
        test_retrieval("What companies has Nexora acquired?")
    """
    results = similarity_search_with_scores(query, k=k)
    print(f"\n=== Test retrieval for query: {query!r} ===")
    for i, (doc, score) in enumerate(results):
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        print(f"\nResult #{i + 1}")
        print(f"  score: {float(score):.4f}")
        print(f"  source: {src} (page {page})")
        print("  text snippet:")
        print(doc.page_content[:500])


