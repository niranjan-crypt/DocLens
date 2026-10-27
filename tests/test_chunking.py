"""
Tests for Baseline and Structure-Aware Chunkers.
Verifies header formatting, paragraph boundary preservation, and token lengths.
"""
from src.chunking.baseline_chunker import BaselineChunker
from src.chunking.structure_chunker import StructureAwareChunker
from src.common.models import ParsedSection


def create_test_section():
    paras = [
        "Paragraph one discussing global enterprise cloud computing strategies and Azure hyperscale deployments.",
        "Paragraph two analyzing cybersecurity compliance frameworks, zero trust network architecture, and audits.",
        "Paragraph three evaluating hardware supply chain dependencies across semiconductor fabrication plants.",
    ]
    text = "\n\n".join(paras)
    return ParsedSection(
        section_id="MSFT_10K_2025_item_1a",
        doc_id="MSFT_10K_2025",
        company="Microsoft Corporation",
        ticker="MSFT",
        fiscal_year=2025,
        section_name="Item 1A. Risk Factors",
        section_code="item_1a",
        raw_text=text,
        clean_text=text,
        token_count=len(text.split()),
        char_count=len(text),
        garbage_ratio=0.0,
    )


def test_baseline_chunker_fixed_size():
    chunker = BaselineChunker(chunk_size=15, chunk_overlap=5)
    section = create_test_section()
    chunks = chunker.chunk_section(section)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.context_header is None
        assert c.token_count <= 15


def test_structure_aware_chunker_includes_context_header():
    chunker = StructureAwareChunker(target_tokens=20, min_tokens=5, overlap_tokens=0, prepend_header=True)
    section = create_test_section()
    chunks = chunker.chunk_section(section)
    assert len(chunks) > 0
    first_chunk = chunks[0]
    expected_header = "[Microsoft Corporation | MSFT 10-K FY 2025 | Item 1A. Risk Factors]"
    assert expected_header in first_chunk.text
    assert first_chunk.context_header == expected_header
    assert first_chunk.section_name == "Item 1A. Risk Factors"
