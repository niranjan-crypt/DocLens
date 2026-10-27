"""
Tests for Data Quality Gatekeeper.
Verifies that 16 automated checks correctly catch garbage, short snippets, and bad metadata.
"""
import pytest
from src.common.models import ParsedSection
from src.ingestion.quality_gate import DataQualityGate


def create_valid_section(section_id="MSFT_10K_2025_item_1a", token_count=400):
    text = "Microsoft Corporation is exposed to cybersecurity risks and cloud infrastructure vulnerabilities. " * 15
    return ParsedSection(
        section_id=section_id,
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
        garbage_ratio=0.005,
    )


def test_quality_gate_passes_valid_sections():
    gate = DataQualityGate()
    sec1 = create_valid_section("MSFT_10K_2025_item_1a")
    sec2 = ParsedSection(
        section_id="MSFT_10K_2025_item_1",
        doc_id="MSFT_10K_2025",
        company="Microsoft Corporation",
        ticker="MSFT",
        fiscal_year=2025,
        section_name="Item 1. Business",
        section_code="item_1",
        raw_text="Microsoft develops and licenses enterprise software and cloud services worldwide. " * 15,
        clean_text="Microsoft develops and licenses enterprise software and cloud services worldwide. " * 15,
        token_count=150,
        char_count=1200,
        garbage_ratio=0.002,
    )
    report = gate.run_all_checks([sec1, sec2])
    assert report.is_success is True
    assert report.failed_checks == 0
    assert report.total_checks_run == 16


def test_quality_gate_flags_excessive_garbage():
    gate = DataQualityGate()
    bad_text = "Valid text $$$$$ ##### @@@@@ ^^^^^ &&&&& ***** ~~~~~" * 20
    bad_sec = ParsedSection(
        section_id="BAD_10K_item_1",
        doc_id="BAD_10K",
        company="Bad Inc",
        ticker="BAD",
        fiscal_year=2025,
        section_name="Item 1. Business",
        section_code="item_1",
        raw_text=bad_text,
        clean_text=bad_text,
        token_count=200,
        char_count=len(bad_text),
        garbage_ratio=0.35,  # 35% garbage
    )
    report = gate.run_all_checks([bad_sec])
    assert report.is_success is False
    garbage_check = next(r for r in report.results if r.check_name == "Q04_garbage_character_ratio")
    assert garbage_check.passed is False


def test_quality_gate_catches_duplicate_section_ids():
    gate = DataQualityGate()
    sec1 = create_valid_section("DUP_ID")
    sec2 = create_valid_section("DUP_ID")
    report = gate.run_all_checks([sec1, sec2])
    assert report.is_success is False
    dup_check = next(r for r in report.results if r.check_name == "Q11_unique_section_ids")
    assert dup_check.passed is False
