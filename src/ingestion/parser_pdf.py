"""
Regulatory Rulebook Parser for DocLens.
Splits disclosure rulebooks into discrete regulations (e.g. Regulation 30, Regulation 33)
with metadata including regulation number, title, chapter, and text.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from src.common.logger import get_logger
from src.common.models import ParsedSection

logger = get_logger("parser_pdf")

# Regex to detect numbered regulations like "Regulation 30: Disclosure of events or information."
REGULATION_PATTERN = re.compile(
    r"(?:Regulation|Rule)\s+(\d+[A-Za-z]?)\s*[\:\.\-–—]\s*([^\n\r\.]+)",
    re.IGNORECASE,
)
CHAPTER_PATTERN = re.compile(r"CHAPTER\s+([IVXLCDM\d]+)[\:\s\-–—]+([^\n\r]+)", re.IGNORECASE)


class RulebookParser:
    """Parses regulatory texts and PDFs into structured sections per regulation."""

    def __init__(self, min_reg_chars: int = 100):
        self.min_reg_chars = min_reg_chars

    def parse_text_or_file(self, file_path_or_text: str, doc_id: str = "SEBI_LODR_2015") -> List[ParsedSection]:
        """Parse rulebook file or raw string into regulation sections."""
        if "\n" not in file_path_or_text and len(file_path_or_text) < 260 and Path(file_path_or_text).exists():
            with open(file_path_or_text, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            content = file_path_or_text

        sections: List[ParsedSection] = []
        matches = list(REGULATION_PATTERN.finditer(content))

        if not matches:
            # Fallback if no specific regulation headers found: chunk by chapter
            logger.warning("No discrete regulation markers found; falling back to whole document.")
            sections.append(
                ParsedSection(
                    section_id=f"{doc_id}_full",
                    doc_id=doc_id,
                    company="Securities and Exchange Board of India",
                    ticker="SEBI",
                    fiscal_year=2015,
                    section_name="Full Rulebook",
                    section_code="full",
                    raw_text=content,
                    clean_text=content.strip(),
                    token_count=len(content.split()),
                    char_count=len(content),
                    garbage_ratio=0.0,
                )
            )
            return sections

        for i, match in enumerate(matches):
            reg_num = match.group(1).strip()
            reg_title = match.group(2).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if (i + 1 < len(matches)) else len(content)

            reg_body = content[start_pos:end_pos].strip()
            clean_text = re.sub(r"\n{3,}", "\n\n", reg_body)

            if len(clean_text) >= self.min_reg_chars:
                sections.append(
                    ParsedSection(
                        section_id=f"{doc_id}_reg_{reg_num.lower()}",
                        doc_id=doc_id,
                        company="Securities and Exchange Board of India",
                        ticker="SEBI",
                        fiscal_year=2015,
                        section_name=f"Regulation {reg_num}: {reg_title}",
                        section_code=f"reg_{reg_num.lower()}",
                        raw_text=reg_body,
                        clean_text=clean_text,
                        token_count=len(clean_text.split()),
                        char_count=len(clean_text),
                        garbage_ratio=0.0,
                    )
                )

        logger.info(f"Parsed {len(sections)} regulations from {doc_id}")
        return sections
