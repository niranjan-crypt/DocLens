"""
Tests for Citation Parsing, Hallucination Detection, and Guardrail Refusal.
"""
from src.common.models import Chunk, RetrievedChunk
from src.generation.citation_parser import CitationParser
from src.generation.guardrails import GenerationGuardrails


def create_dummy_retrieved_chunk(cid="chunk_001"):
    ch = Chunk(
        chunk_id=cid,
        doc_id="MSFT_10K_2025",
        section_id="MSFT_10K_2025_item_1a",
        company="Microsoft Corporation",
        ticker="MSFT",
        fiscal_year=2025,
        section_name="Item 1A. Risk Factors",
        position=0,
        text="Microsoft identifies cybersecurity nation-state threats as a material risk factor.",
        token_count=10,
    )
    return RetrievedChunk(chunk=ch, final_rank=1, dense_score=0.88)


def test_citation_parser_valid_tags():
    parser = CitationParser()
    retrieved = [create_dummy_retrieved_chunk("chunk_001")]
    answer = "Microsoft faces nation-state cyber threats [1] which are material to operations."

    citations, validity, invalid_tags = parser.parse_citations(answer, retrieved)
    assert len(citations) == 1
    assert citations[0].tag == "[1]"
    assert citations[0].chunk_id == "chunk_001"
    assert validity == 1.0
    assert len(invalid_tags) == 0


def test_citation_parser_flags_hallucinated_tags():
    parser = CitationParser()
    retrieved = [create_dummy_retrieved_chunk("chunk_001")]
    # Model generates citation [7] when only 1 chunk was provided
    answer = "Microsoft's cyber risks are severe [1] and cloud revenues surged [7]."

    citations, validity, invalid_tags = parser.parse_citations(answer, retrieved)
    assert len(citations) == 2
    assert validity == 0.5  # 1 out of 2 is valid
    assert invalid_tags == [7]
    assert citations[1].is_valid is False


def test_guardrails_refusal_detection():
    guardrails = GenerationGuardrails()
    refusal_text = "The provided documents do not contain enough information to answer this question."
    normal_text = "Microsoft generates substantial revenue from Intelligent Cloud."

    assert guardrails.is_refusal_answer(refusal_text) is True
    assert guardrails.is_refusal_answer(normal_text) is False
