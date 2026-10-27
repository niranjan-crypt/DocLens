"""
Configuration loader and validator for DocLens.
Loads YAML configuration and merges with environment variables.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file from project root if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class CompanyConfig(BaseModel):
    ticker: str
    name: str
    sector: str
    cik: str
    fiscal_years: List[int]


class RulebookConfig(BaseModel):
    id: str
    title: str
    version: str
    source_url: str


class TargetSection(BaseModel):
    id: str
    name: str


class Config(BaseModel):
    # Project Info
    project_name: str = "doclens"
    version: str = "0.1.0"
    seed: int = 42

    # Paths (resolved relative to PROJECT_ROOT)
    raw_filings_dir: Path
    raw_rulebooks_dir: Path
    processed_dir: Path
    eval_dir: Path
    chroma_db_dir: Path
    bm25_index_path: Path
    db_url: str

    # Corpus
    companies: List[CompanyConfig]
    rulebooks: List[RulebookConfig]

    # Ingestion
    user_agent_name: str
    user_agent_email: str
    sec_rate_limit: int = 5
    max_retries: int = 3
    backoff_factor: float = 2.0
    target_sections: List[TargetSection]

    # Quality Gate
    max_garbage_char_ratio: float = 0.02
    min_sections_per_filing: int = 2
    min_tokens_per_section: int = 200
    max_tokens_per_section: int = 150000
    duplicate_jaccard_threshold: float = 0.95

    # Chunking
    baseline_chunk_size: int = 500
    baseline_chunk_overlap: int = 100
    structure_target_tokens: int = 400
    structure_min_tokens: int = 150
    structure_max_tokens: int = 600
    structure_overlap_tokens: int = 60
    prepend_header: bool = True

    # Embeddings & Retrieval
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    query_instruction: str = "Represent this sentence for searching relevant passages: "
    normalize_embeddings: bool = True
    embedding_batch_size: int = 32
    top_k_dense: int = 20
    top_k_sparse: int = 20
    rrf_k: int = 60
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    final_top_k: int = 5
    refusal_score_threshold: float = 0.15

    # Generation
    llm_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"
    api_fallback_enabled: bool = True
    temperature: float = 0.1
    max_new_tokens: int = 512
    refusal_message: str = "The provided documents do not contain enough information to answer this question."


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and parse the YAML config file, resolving file paths relative to project root."""
    if config_path is None:
        path = PROJECT_ROOT / "configs" / "config.yaml"
    else:
        path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Resolve paths relative to root
    paths = raw.get("paths", {})
    def resolve_p(p: str) -> Path:
        p_obj = Path(p)
        return p_obj if p_obj.is_absolute() else (PROJECT_ROOT / p_obj)

    # Database URL priority: environment variable > config.yaml
    db_env_var = raw.get("paths", {}).get("postgres_url_env", "DATABASE_URL")
    db_url = os.getenv(db_env_var) or raw.get("paths", {}).get("db_path", "sqlite:///data/doclens.db")
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        rel_db = db_url.replace("sqlite:///", "")
        db_url = f"sqlite:///{PROJECT_ROOT / rel_db}"

    user_name = os.getenv("SEC_EDGAR_USER_NAME") or raw.get("ingestion", {}).get("user_agent_name", "Niranjan Krishnakumar")
    user_email = os.getenv("SEC_EDGAR_USER_EMAIL") or raw.get("ingestion", {}).get("user_agent_email", "niranjankk9@gmail.com")

    return Config(
        project_name=raw.get("project", {}).get("name", "doclens"),
        version=raw.get("project", {}).get("version", "0.1.0"),
        seed=raw.get("project", {}).get("seed", 42),
        raw_filings_dir=resolve_p(paths.get("raw_filings_dir", "data/raw/filings")),
        raw_rulebooks_dir=resolve_p(paths.get("raw_rulebooks_dir", "data/raw/rulebooks")),
        processed_dir=resolve_p(paths.get("processed_dir", "data/processed")),
        eval_dir=resolve_p(paths.get("eval_dir", "data/eval")),
        chroma_db_dir=resolve_p(paths.get("chroma_db_dir", "data/chromadb")),
        bm25_index_path=resolve_p(paths.get("bm25_index_path", "data/bm25_index.pkl")),
        db_url=db_url,
        companies=[CompanyConfig(**c) for c in raw.get("corpus", {}).get("companies", [])],
        rulebooks=[RulebookConfig(**r) for r in raw.get("corpus", {}).get("rulebooks", [])],
        user_agent_name=user_name,
        user_agent_email=user_email,
        sec_rate_limit=raw.get("ingestion", {}).get("sec_rate_limit_per_second", 5),
        max_retries=raw.get("ingestion", {}).get("max_retries", 3),
        backoff_factor=raw.get("ingestion", {}).get("backoff_factor", 2.0),
        target_sections=[TargetSection(**s) for s in raw.get("ingestion", {}).get("target_sections", [])],
        max_garbage_char_ratio=raw.get("quality_gate", {}).get("max_garbage_char_ratio", 0.02),
        min_sections_per_filing=raw.get("quality_gate", {}).get("min_sections_per_filing", 2),
        min_tokens_per_section=raw.get("quality_gate", {}).get("min_tokens_per_section", 200),
        max_tokens_per_section=raw.get("quality_gate", {}).get("max_tokens_per_section", 150000),
        duplicate_jaccard_threshold=raw.get("quality_gate", {}).get("duplicate_jaccard_threshold", 0.95),
        baseline_chunk_size=raw.get("chunking", {}).get("baseline", {}).get("chunk_size", 500),
        baseline_chunk_overlap=raw.get("chunking", {}).get("baseline", {}).get("chunk_overlap", 100),
        structure_target_tokens=raw.get("chunking", {}).get("structure_aware", {}).get("target_tokens", 400),
        structure_min_tokens=raw.get("chunking", {}).get("structure_aware", {}).get("min_tokens", 150),
        structure_max_tokens=raw.get("chunking", {}).get("structure_aware", {}).get("max_tokens", 600),
        structure_overlap_tokens=raw.get("chunking", {}).get("structure_aware", {}).get("overlap_tokens", 60),
        prepend_header=raw.get("chunking", {}).get("structure_aware", {}).get("prepend_header", True),
        embedding_model=raw.get("embeddings", {}).get("model_name", "BAAI/bge-small-en-v1.5"),
        query_instruction=raw.get("embeddings", {}).get("query_instruction", "Represent this sentence for searching relevant passages: "),
        normalize_embeddings=raw.get("embeddings", {}).get("normalize_embeddings", True),
        embedding_batch_size=raw.get("embeddings", {}).get("batch_size", 32),
        top_k_dense=raw.get("retrieval", {}).get("top_k_dense", 20),
        top_k_sparse=raw.get("retrieval", {}).get("top_k_sparse", 20),
        rrf_k=raw.get("retrieval", {}).get("rrf_k", 60),
        reranker_model=raw.get("retrieval", {}).get("reranker_model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        final_top_k=raw.get("retrieval", {}).get("final_top_k", 5),
        refusal_score_threshold=raw.get("retrieval", {}).get("refusal_score_threshold", 0.15),
        llm_model=raw.get("generation", {}).get("model_name", "llama3.2:3b"),
        ollama_base_url=raw.get("generation", {}).get("ollama_base_url", "http://localhost:11434"),
        api_fallback_enabled=raw.get("generation", {}).get("api_fallback_enabled", True),
        temperature=raw.get("generation", {}).get("temperature", 0.1),
        max_new_tokens=raw.get("generation", {}).get("max_new_tokens", 512),
        refusal_message=raw.get("generation", {}).get("refusal_message", "The provided documents do not contain enough information to answer this question."),
    )
