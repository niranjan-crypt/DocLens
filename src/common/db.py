"""
Database connection, ORM models, and lineage registry for DocLens.
Supports PostgreSQL (production/Docker) and SQLite (local zero-setup development).
"""
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from src.common.config import load_config
from src.common.models import DocumentMetadata, Chunk as ChunkModel

Base = declarative_base()


class DocumentRecord(Base):
    """Document registry table tracking provenance and checksums for idempotency."""
    __tablename__ = "documents"

    doc_id = Column(String(100), primary_key=True)
    company = Column(String(200), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)
    sector = Column(String(100), nullable=False)
    doc_type = Column(String(50), nullable=False)  # '10-K' or 'RULEBOOK'
    fiscal_year = Column(Integer, nullable=True, index=True)
    filing_date = Column(String(50), nullable=True)
    source_url = Column(Text, nullable=False)
    checksum = Column(String(64), nullable=False, unique=True)
    file_path = Column(Text, nullable=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("ChunkRecord", back_populates="document", cascade="all, delete-orphan")


class ChunkRecord(Base):
    """Chunk lineage table storing text chunks, section metadata, and token lengths."""
    __tablename__ = "chunks"

    chunk_id = Column(String(120), primary_key=True)
    doc_id = Column(String(100), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(String(100), nullable=False)
    company = Column(String(200), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=True, index=True)
    section_name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    context_header = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("DocumentRecord", back_populates="chunks")


class QueryLogRecord(Base):
    """Lineage log of user queries, retrieved chunks, latency metrics, and feedback."""
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    is_refusal = Column(Boolean, default=False)
    latency_total_ms = Column(Float, nullable=False)
    retrieved_chunk_ids = Column(Text, nullable=True)  # JSON-encoded chunk IDs
    feedback = Column(Integer, nullable=True)  # 1: Thumbs Up, -1: Thumbs Down
    timestamp = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Manages database sessions and schema operations."""

    def __init__(self, db_url: Optional[str] = None):
        if db_url is None:
            cfg = load_config()
            db_url = cfg.db_url

        self.db_url = db_url

        # Ensure parent directory exists for SQLite files
        if self.db_url.startswith("sqlite:///"):
            db_path = Path(self.db_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(self.db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_db()

    def init_db(self):
        """Create tables if they do not exist."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def register_document(self, meta: DocumentMetadata) -> bool:
        """Register a document if checksum does not exist. Returns True if inserted, False if skipped."""
        with self.get_session() as session:
            existing = session.query(DocumentRecord).filter_by(checksum=meta.checksum).first()
            if existing:
                return False  # Already exists (idempotent skip)

            record = DocumentRecord(
                doc_id=meta.doc_id,
                company=meta.company,
                ticker=meta.ticker,
                sector=meta.sector,
                doc_type=meta.doc_type,
                fiscal_year=meta.fiscal_year,
                filing_date=meta.filing_date,
                source_url=meta.source_url,
                checksum=meta.checksum,
                file_path=meta.file_path,
                downloaded_at=meta.downloaded_at,
            )
            session.merge(record)
            session.commit()
            return True

    def get_document_by_checksum(self, checksum: str) -> Optional[DocumentRecord]:
        with self.get_session() as session:
            return session.query(DocumentRecord).filter_by(checksum=checksum).first()

    def list_documents(self) -> List[DocumentMetadata]:
        with self.get_session() as session:
            records = session.query(DocumentRecord).all()
            return [
                DocumentMetadata(
                    doc_id=r.doc_id,
                    company=r.company,
                    ticker=r.ticker,
                    sector=r.sector,
                    doc_type=r.doc_type,
                    fiscal_year=r.fiscal_year,
                    filing_date=r.filing_date,
                    source_url=r.source_url,
                    checksum=r.checksum,
                    file_path=r.file_path,
                    downloaded_at=r.downloaded_at,
                )
                for r in records
            ]

    def store_chunks(self, chunks: List[ChunkModel]):
        """Batch store chunks into database."""
        with self.get_session() as session:
            for ch in chunks:
                record = ChunkRecord(
                    chunk_id=ch.chunk_id,
                    doc_id=ch.doc_id,
                    section_id=ch.section_id,
                    company=ch.company,
                    ticker=ch.ticker,
                    fiscal_year=ch.fiscal_year,
                    section_name=ch.section_name,
                    position=ch.position,
                    text=ch.text,
                    context_header=ch.context_header,
                    token_count=ch.token_count,
                )
                session.merge(record)
            session.commit()

    def log_query(
        self,
        query: str,
        answer: str,
        is_refusal: bool,
        latency_ms: float,
        chunk_ids: Optional[str] = None,
    ) -> int:
        with self.get_session() as session:
            log = QueryLogRecord(
                query_text=query,
                answer_text=answer,
                is_refusal=is_refusal,
                latency_total_ms=latency_ms,
                retrieved_chunk_ids=chunk_ids,
            )
            session.add(log)
            session.commit()
            return log.id

    def record_feedback(self, log_id: int, feedback_val: int):
        with self.get_session() as session:
            record = session.query(QueryLogRecord).filter_by(id=log_id).first()
            if record:
                record.feedback = feedback_val
                session.commit()


def compute_file_checksum(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for lineage and idempotency."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()
