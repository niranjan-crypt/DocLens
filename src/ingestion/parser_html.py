"""
HTML 10-K Section Parser for DocLens.
Extracts narrative sections (Item 1 Business, Item 1A Risk Factors, Item 7 MD&A)
while removing XBRL junk, scripts, CSS, and avoiding Table of Contents false positives.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from src.common.logger import get_logger
from src.common.models import ParsedSection

logger = get_logger("parser_html")

# Common 10-K narrative item patterns
SECTION_PATTERNS = [
    {
        "code": "item_1",
        "name": "Item 1. Business",
        "regex": re.compile(
            r"(?:ITEM|Item)\s+1[\.\:\s]+(?:Business|BUSINESS)",
            re.IGNORECASE,
        ),
    },
    {
        "code": "item_1a",
        "name": "Item 1A. Risk Factors",
        "regex": re.compile(
            r"(?:ITEM|Item)\s+1A[\.\:\s]+(?:Risk\s+Factors|RISK\s+FACTORS)",
            re.IGNORECASE,
        ),
    },
    {
        "code": "item_7",
        "name": "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations",
        "regex": re.compile(
            r"(?:ITEM|Item)\s+7[\.\:\s]+(?:Management['’]s\s+Discussion|MANAGEMENT['’]S\s+DISCUSSION)",
            re.IGNORECASE,
        ),
    },
]

# Next-item boundary patterns to stop extraction
ITEM_STOP_PATTERNS = {
    "item_1": re.compile(r"(?:ITEM|Item)\s+(?:1A|1B|2)[\.\:\s]+", re.IGNORECASE),
    "item_1a": re.compile(r"(?:ITEM|Item)\s+(?:1B|1C|2)[\.\:\s]+", re.IGNORECASE),
    "item_7": re.compile(r"(?:ITEM|Item)\s+(?:7A|8)[\.\:\s]+", re.IGNORECASE),
}


class HTMLFilingParser:
    """Parses SEC 10-K HTML filings into clean structured sections."""

    def __init__(self, min_body_chars: int = 1500):
        self.min_body_chars = min_body_chars

    def clean_html(self, html_content: str) -> str:
        """Strip scripts, styles, hidden XBRL, comments and normalize whitespace."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Decompose non-content tags
        for tag in soup(["script", "style", "head", "noscript", "meta", "link", "ix:header"]):
            tag.decompose()

        # Remove elements with display:none
        for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
            tag.decompose()

        # Extract text while preserving line breaks for paragraph boundaries
        text = soup.get_text(separator="\n\n")

        # Normalize unicode spaces and clean carriage returns
        text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
        # Collapse excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def compute_garbage_ratio(self, text: str) -> float:
        """Compute the ratio of non-alphanumeric, non-whitespace, non-standard punctuation chars."""
        if not text:
            return 1.0
        # Allowed chars: letters, digits, standard punctuation and whitespace
        clean_chars = len(re.findall(r"[A-Za-z0-9\s\.\,\;\:\'\’\"\-–—\(\)\$\%\/]", text))
        total_chars = len(text)
        return 1.0 - (clean_chars / total_chars)

    def extract_sections(
        self,
        doc_id: str,
        company: str,
        ticker: str,
        fiscal_year: Optional[int],
        html_or_text: str,
        is_already_text: bool = False,
    ) -> List[ParsedSection]:
        """Extract narrative Item 1, 1A, and 7 sections, rejecting TOC false positives."""
        if is_already_text:
            text = html_or_text
        else:
            text = self.clean_html(html_or_text)

        parsed_sections: List[ParsedSection] = []

        for sec in SECTION_PATTERNS:
            code = sec["code"]
            name = sec["name"]
            regex = sec["regex"]
            stop_regex = ITEM_STOP_PATTERNS.get(code)

            # Find all occurrences of this heading in the text
            matches = list(regex.finditer(text))
            if not matches:
                continue

            # In SEC filings, the Table of Contents has short snippets (< 500 chars before next item).
            # The genuine body section has the longest body length before the next item stop pattern.
            best_chunk_text = ""
            for m in matches:
                start_idx = m.start()
                subtext = text[start_idx:]

                # Look for end boundary (either specific next item or ANY next item)
                stop_pos = None
                if stop_regex:
                    stop_m = stop_regex.search(subtext[m.end() - start_idx :])
                    if stop_m:
                        stop_pos = (m.end() - start_idx) + stop_m.start()

                if stop_pos is None:
                    # Generic next item boundary
                    any_stop = re.search(r"(?:ITEM|Item)\s+\d+[A-Za-z]?[\.\:\s]+", subtext[m.end() - start_idx :], re.IGNORECASE)
                    if any_stop:
                        stop_pos = (m.end() - start_idx) + any_stop.start()
                    else:
                        stop_pos = min(len(subtext), 80000)

                body_candidate = subtext[:stop_pos].strip()

                # If candidate contains TOC dot leader (... 12 or ... 25), it's a TOC row, skip it
                if re.search(r"\.{3,}\s*\d+", body_candidate[:300]):
                    continue

                # Keep candidate with most narrative text
                if len(body_candidate) > len(best_chunk_text):
                    best_chunk_text = body_candidate

            # Verify it is not a TOC snippet
            if len(best_chunk_text) >= self.min_body_chars:
                # Strip excessive spaces within paragraphs
                clean_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in best_chunk_text.split("\n")]
                clean_sec_text = "\n".join(line for line in clean_lines if line)
                tokens_est = len(clean_sec_text.split())
                garbage = self.compute_garbage_ratio(clean_sec_text)

                parsed_sections.append(
                    ParsedSection(
                        section_id=f"{doc_id}_{code}",
                        doc_id=doc_id,
                        company=company,
                        ticker=ticker,
                        fiscal_year=fiscal_year,
                        section_name=name,
                        section_code=code,
                        raw_text=best_chunk_text,
                        clean_text=clean_sec_text,
                        token_count=tokens_est,
                        char_count=len(clean_sec_text),
                        garbage_ratio=round(garbage, 4),
                    )
                )

        return parsed_sections


def save_sections_to_jsonl(sections: List[ParsedSection], output_path: Path):
    """Write parsed sections to JSONL format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(s.model_dump()) + "\n")
