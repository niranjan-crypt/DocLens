"""
Tests for HTML and PDF parsers.
Verifies narrative item extraction, removal of noise tags, and TOC false positive rejection.
"""
import pytest
from src.ingestion.parser_html import HTMLFilingParser
from src.ingestion.parser_pdf import RulebookParser


def test_html_cleaning_removes_scripts_and_styles():
    parser = HTMLFilingParser()
    sample_html = """
    <html>
        <head><style>.hidden { display: none; }</style></head>
        <body>
            <script>console.log("tracking code");</script>
            <div style="display:none">Hidden XBRL data</div>
            <p>Legitimate narrative disclosure text for annual report.</p>
        </body>
    </html>
    """
    clean_text = parser.clean_html(sample_html)
    assert "tracking code" not in clean_text
    assert "Hidden XBRL" not in clean_text
    assert "Legitimate narrative disclosure" in clean_text


def test_table_of_contents_rejection_and_narrative_extraction():
    parser = HTMLFilingParser(min_body_chars=200)
    # Simulate an SEC 10-K HTML with TOC snippet followed by genuine Item 1A body
    filing_text = """
    PART I
    TABLE OF CONTENTS
    Item 1. Business ......................... 4
    Item 1A. Risk Factors .................... 12
    Item 7. Management's Discussion .......... 25

    ITEM 1A. RISK FACTORS
    """ + ("Our cybersecurity infrastructure is subject to sophisticated persistent threats. " * 30) + """
    ITEM 1B. UNRESOLVED STAFF COMMENTS
    None.
    """
    sections = parser.extract_sections(
        doc_id="TEST_10K_2025",
        company="Test Corp",
        ticker="TEST",
        fiscal_year=2025,
        html_or_text=filing_text,
        is_already_text=True,
    )

    assert len(sections) == 1
    sec = sections[0]
    assert sec.section_code == "item_1a"
    assert "cybersecurity infrastructure" in sec.clean_text
    assert sec.char_count > 500


def test_rulebook_regulation_extraction():
    parser = RulebookParser()
    sample_rulebook = """
    CHAPTER IV: LISTING OBLIGATIONS
    Regulation 30: Disclosure of events or information.
    Every listed entity shall make disclosures of any events or information which are material.
    The disclosure must be completed within thirty minutes from the closure of the meeting.

    Regulation 33: Financial Results.
    The approval process for quarterly results shall be completed within forty-five days.
    """
    sections = parser.parse_text_or_file(sample_rulebook, doc_id="SEBI_TEST")
    assert len(sections) == 2
    reg_names = [s.section_name for s in sections]
    assert any("Regulation 30" in name for name in reg_names)
    assert any("Regulation 33" in name for name in reg_names)


def test_item_7_mda_extraction():
    parser = HTMLFilingParser(min_body_chars=200)
    mda_text = """
    ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS
    """ + ("Cloud revenue increased significantly driven by enterprise customer workload migration. " * 20) + """
    ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK
    """
    sections = parser.extract_sections(
        doc_id="TEST_10K_2025",
        company="Test Corp",
        ticker="TEST",
        fiscal_year=2025,
        html_or_text=mda_text,
        is_already_text=True,
    )
    assert len(sections) == 1
    assert sections[0].section_code == "item_7"
    assert "Cloud revenue increased" in sections[0].clean_text


def test_garbage_ratio_computation():
    parser = HTMLFilingParser()
    clean = "Clean standard annual report text with typical financial numbers like $1,250,000."
    dirty = "%%%%% &&&&& $$$$$ @@@@@ ^^^^^ ***** ~~~~~    "
    assert parser.compute_garbage_ratio(clean) < 0.05
    assert parser.compute_garbage_ratio(dirty) > 0.40

