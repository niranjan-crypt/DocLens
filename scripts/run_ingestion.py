"""
End-to-End Ingestion Runner for DocLens (Week 1 / Phases 1-3).
Orchestrates:
1. Document Acquisition (SEC 10-K filings + SEBI LODR 2015 rulebook)
2. Document Registry tracking in SQLite/PostgreSQL with SHA-256 checksums
3. HTML & PDF Parsing with Table-of-Contents disambiguation
4. 16-Check Automated Data Quality Gatekeeper
5. Structure-Aware Chunking with Context Headers
6. Persistence to database and JSONL lines
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Ensure repo root is on python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.chunking.structure_chunker import StructureAwareChunker
from src.common.config import Config, load_config
from src.common.db import DatabaseManager, compute_file_checksum
from src.common.logger import get_logger
from src.common.models import Chunk, DocumentMetadata, ParsedSection
from src.ingestion.parser_html import HTMLFilingParser
from src.ingestion.parser_pdf import RulebookParser
from src.ingestion.quality_gate import DataQualityGate
from src.ingestion.rulebook_fetcher import RulebookFetcher
from scripts.seed_data import FILINGS_DATA, generate_seed_data

logger = get_logger("run_ingestion")


def run_pipeline(validate_only: bool = False):
    config: Config = load_config()
    db = DatabaseManager(config.db_url)

    raw_filings_dir = Path(config.raw_filings_dir)
    raw_rulebooks_dir = Path(config.raw_rulebooks_dir)
    processed_dir = Path(config.processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("🚀 DOCLENS OFFLINE INGESTION PIPELINE (WEEK 1)")
    print("=" * 65)

    # ---------------------------------------------------------
    # STEP 1: Data Collection & Lineage Registration
    # ---------------------------------------------------------
    print("\n[Step 1/5] Ingesting & Registering Documents...")
    rulebook_fetcher = RulebookFetcher(config, db)
    rulebook_meta = rulebook_fetcher.fetch_rulebook("SEBI_LODR_2015")
    db.register_document(rulebook_meta)
    print(f"  ✓ Registered Rulebook: {rulebook_meta.doc_id} (SHA: {rulebook_meta.checksum[:10]}...)")

    # Generate or verify seed 10-K filings
    html_files = list(raw_filings_dir.glob("*.html"))
    if len(html_files) < len(FILINGS_DATA):
        print(f"  Generating authentic target filings in {raw_filings_dir}...")
        html_files = generate_seed_data(raw_filings_dir)

    for html_file in html_files:
        doc_id = html_file.stem
        if doc_id in FILINGS_DATA:
            info = FILINGS_DATA[doc_id]
            checksum = compute_file_checksum(html_file)
            doc_meta = DocumentMetadata(
                doc_id=doc_id,
                company=info["company"],
                ticker=info["ticker"],
                sector=info["sector"],
                doc_type="10-K",
                fiscal_year=info["year"],
                filing_date=info["filing_date"],
                source_url=f"https://www.sec.gov/edgar/searchedgar/{info['ticker'].lower()}_{info['year']}.htm",
                checksum=checksum,
                file_path=str(html_file),
                downloaded_at=datetime.utcnow(),
            )
            db.register_document(doc_meta)
            print(f"  ✓ Registered 10-K Filing: {doc_id} ({info['company']})")

    # ---------------------------------------------------------
    # STEP 2: HTML & PDF Section Parsing
    # ---------------------------------------------------------
    print("\n[Step 2/5] Parsing Narrative Sections & Regulation Clauses...")
    html_parser = HTMLFilingParser(min_body_chars=300)
    pdf_parser = RulebookParser(min_reg_chars=100)

    all_sections: List[ParsedSection] = []

    # Parse 10-Ks
    for html_file in sorted(raw_filings_dir.glob("*.html")):
        doc_id = html_file.stem
        if doc_id not in FILINGS_DATA:
            continue
        info = FILINGS_DATA[doc_id]
        with open(html_file, "r", encoding="utf-8") as f:
            html_text = f.read()

        sections = html_parser.extract_sections(
            doc_id=doc_id,
            company=info["company"],
            ticker=info["ticker"],
            fiscal_year=info["year"],
            html_or_text=html_text,
            is_already_text=False,
        )
        print(f"  ✓ {doc_id}: Extracted {len(sections)} narrative sections ({', '.join(s.section_code for s in sections)})")
        all_sections.extend(sections)

    # Parse Rulebook
    rulebook_path = raw_rulebooks_dir / "SEBI_LODR_2015.txt"
    if rulebook_path.exists():
        rb_sections = pdf_parser.parse_text_or_file(str(rulebook_path), doc_id="SEBI_LODR_2015")
        print(f"  ✓ SEBI_LODR_2015: Extracted {len(rb_sections)} regulations ({', '.join(s.section_code for s in rb_sections)})")
        all_sections.extend(rb_sections)

    # ---------------------------------------------------------
    # STEP 3: Automated Data Quality Gatekeeper (16 Checks)
    # ---------------------------------------------------------
    print("\n[Step 3/5] Running 16-Check Data Quality Gate...")
    gate = DataQualityGate(config)
    report = gate.run_all_checks(all_sections)

    for res in report.results:
        symbol = "✅" if res.passed else "❌"
        print(f"  {symbol} {res.check_name}: {res.details}")

    print(f"\n  Quality Gate Summary: {report.passed_checks}/{report.total_checks_run} checks passed.")
    if not report.is_success:
        print("  ❌ Data Quality Gate FAILED! Halting ingestion pipeline.")
        sys.exit(1)

    print("  🎉 All 16 Quality Gate Checks PASSED successfully!")

    if validate_only:
        print("\n[Validate-Only Mode] Ingestion validation completed.")
        return

    # ---------------------------------------------------------
    # STEP 4: Structure-Aware Chunking with Context Headers
    # ---------------------------------------------------------
    print("\n[Step 4/5] Executing Structure-Aware Chunking...")
    chunker = StructureAwareChunker(
        target_tokens=config.structure_target_tokens,
        min_tokens=config.structure_min_tokens,
        max_tokens=config.structure_max_tokens,
        overlap_tokens=config.structure_overlap_tokens,
        prepend_header=config.prepend_header,
    )

    all_chunks: List[Chunk] = []
    for sec in all_sections:
        chunks = chunker.chunk_section(sec)
        all_chunks.extend(chunks)

    print(f"  ✓ Generated {len(all_chunks)} chunks across {len(all_sections)} sections.")
    if all_chunks:
        print(f"  Sample Chunk [0] Header:\n    {all_chunks[0].context_header}")
        print(f"  Sample Chunk [0] Preview:\n    {all_chunks[0].text[:120]}...\n")

    # ---------------------------------------------------------
    # STEP 5: Persistence to Database & JSONL
    # ---------------------------------------------------------
    print("[Step 5/5] Persisting Processed Artifacts...")
    # Save sections JSONL
    sections_jsonl = processed_dir / "sections.jsonl"
    with open(sections_jsonl, "w", encoding="utf-8") as f:
        for s in all_sections:
            f.write(json.dumps(s.model_dump()) + "\n")
    print(f"  ✓ Saved {len(all_sections)} sections to {sections_jsonl}")

    # Save chunks JSONL
    chunks_jsonl = processed_dir / "chunks.jsonl"
    with open(chunks_jsonl, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c.model_dump()) + "\n")
    print(f"  ✓ Saved {len(all_chunks)} chunks to {chunks_jsonl}")

    # Save chunks into SQLite/PostgreSQL
    db.store_chunks(all_chunks)
    print(f"  ✓ Stored {len(all_chunks)} chunk lineage records in database.")

    print("\n" + "=" * 65)
    print("✨ WEEK 1 PIPELINE COMPLETE: All data ingested, parsed, checked & chunked!")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DocLens Ingestion Runner")
    parser.add_argument("--validate-only", action="store_true", help="Run checks only without chunking")
    args = parser.parse_args()
    run_pipeline(validate_only=args.validate_only)
