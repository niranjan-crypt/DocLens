"""
Dense Vector Indexer for DocLens.
Uses BAAI/bge-small-en-v1.5 sentence embeddings and persistent ChromaDB collection.
Applies BGE query instruction prefix for queries only (not documents).
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import Chunk, QueryFilters

logger = get_logger("dense_indexer")


class DenseVectorIndexer:
    """Embeds chunks with bge-small-en-v1.5 and manages ChromaDB persistent collection."""

    COLLECTION_NAME = "doclens_chunks"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.chroma_dir = Path(self.config.chroma_db_dir)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB client at {self.chroma_dir}...")
        self.client = chromadb.PersistentClient(path=str(self.chroma_dir))

        self._model = None
        self._collection = None

    @property
    def model(self):
        if self._model is None:
            logger.info(f"Loading embedding model: {self.config.embedding_model}...")
            self._model = SentenceTransformer(self.config.embedding_model)
        return self._model

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def index_chunks(self, chunks: List[Chunk]):
        """Batch embed and index chunks into ChromaDB."""
        if not chunks:
            return

        logger.info(f"Indexing {len(chunks)} chunks into ChromaDB collection '{self.COLLECTION_NAME}'...")

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "section_id": c.section_id,
                "company": c.company,
                "ticker": c.ticker,
                "fiscal_year": c.fiscal_year if c.fiscal_year else 0,
                "section_name": c.section_name,
                "position": c.position,
                "token_count": c.token_count,
            }
            for c in chunks
        ]

        # Note: BGE models do NOT use prefix for document text, only for queries!
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.embedding_batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            show_progress_bar=True,
        ).tolist()

        # ChromaDB upsert in chunks to prevent payload size limits
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i : i + batch_size],
                embeddings=embeddings[i : i + batch_size],
                documents=texts[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )
        logger.info(f"Successfully indexed {len(chunks)} chunks in ChromaDB.")

    def search(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        top_k: int = 20,
    ) -> List[Tuple[Chunk, float, int]]:
        """
        Query ChromaDB using BGE query instruction prefix.

        Returns:
            List of (chunk, cosine_similarity, rank) tuples.
        """
        # BGE query prefix is mandatory for query embedding quality
        prefixed_query = f"{self.config.query_instruction}{query}"
        query_embedding = self.model.encode(
            prefixed_query,
            normalize_embeddings=self.config.normalize_embeddings,
        ).tolist()

        where_filter = None
        if filters:
            conds = []
            if filters.ticker:
                conds.append({"ticker": {"$eq": filters.ticker.upper()}})
            if filters.fiscal_year:
                conds.append({"fiscal_year": {"$eq": filters.fiscal_year}})
            if len(conds) == 1:
                where_filter = conds[0]
            elif len(conds) > 1:
                where_filter = {"$and": conds}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        retrieved: List[Tuple[Chunk, float, int]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return retrieved

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for rank, (cid, doc_text, meta, dist) in enumerate(zip(ids, docs, metas, distances), start=1):
            # ChromaDB cosine distance = 1 - cosine_similarity
            similarity = 1.0 - dist
            chunk = Chunk(
                chunk_id=cid,
                doc_id=meta["doc_id"],
                section_id=meta["section_id"],
                company=meta["company"],
                ticker=meta["ticker"],
                fiscal_year=meta["fiscal_year"] if meta["fiscal_year"] > 0 else None,
                section_name=meta["section_name"],
                position=meta["position"],
                text=doc_text,
                token_count=meta["token_count"],
            )
            retrieved.append((chunk, float(similarity), rank))

        return retrieved
