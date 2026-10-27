"""
Structure-Aware Chunker for DocLens.
Partitions narrative filings along paragraph and sentence boundaries,
strictly respecting section limits and prepending rich document lineage headers.
"""
import re
from typing import List, Optional
from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import Chunk, ParsedSection

logger = get_logger("structure_chunker")


class StructureAwareChunker:
    """Structure-aware chunker with paragraph boundary preservation and metadata prefixing."""

    def __init__(
        self,
        target_tokens: int = 400,
        min_tokens: int = 150,
        max_tokens: int = 600,
        overlap_tokens: int = 60,
        prepend_header: bool = True,
    ):
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.prepend_header = prepend_header

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text by double newlines into discrete paragraphs."""
        raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        paragraphs = []
        for p in raw_paras:
            # If a paragraph is excessively long, split by sentence endings
            words = p.split()
            if len(words) > self.max_tokens:
                sentences = re.split(r"(?<=[.!?])\s+", p)
                curr_sent_block = []
                curr_count = 0
                for s in sentences:
                    s_words = s.split()
                    if curr_count + len(s_words) > self.target_tokens and curr_sent_block:
                        paragraphs.append(" ".join(curr_sent_block))
                        curr_sent_block = [s]
                        curr_count = len(s_words)
                    else:
                        curr_sent_block.append(s)
                        curr_count += len(s_words)
                if curr_sent_block:
                    paragraphs.append(" ".join(curr_sent_block))
            else:
                paragraphs.append(p)
        return paragraphs

    def build_context_header(self, section: ParsedSection) -> str:
        """Construct standardized context header, e.g. [Microsoft | MSFT 10-K 2025 | Item 1A. Risk Factors]"""
        year_str = f"FY {section.fiscal_year}" if section.fiscal_year else "Regulatory Rulebook"
        doc_type_str = "10-K" if section.fiscal_year else "Regulation"
        return f"[{section.company} | {section.ticker} {doc_type_str} {year_str} | {section.section_name}]"

    def chunk_section(self, section: ParsedSection) -> List[Chunk]:
        """Convert a parsed section into structure-bounded chunks with context headers."""
        paragraphs = self._split_into_paragraphs(section.clean_text)
        if not paragraphs:
            return []

        chunks: List[Chunk] = []
        header = self.build_context_header(section) if self.prepend_header else ""

        current_words: List[str] = []
        current_paragraphs: List[str] = []
        pos = 0

        for para in paragraphs:
            para_words = para.split()

            # If adding this paragraph exceeds target tokens and we have enough words, flush chunk
            if len(current_words) + len(para_words) > self.target_tokens and len(current_words) >= self.min_tokens:
                body_text = "\n\n".join(current_paragraphs)
                full_text = f"{header}\n\n{body_text}".strip() if header else body_text
                chunk_id = f"{section.section_id}_c{pos:03d}"

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=section.doc_id,
                        section_id=section.section_id,
                        company=section.company,
                        ticker=section.ticker,
                        fiscal_year=section.fiscal_year,
                        section_name=section.section_name,
                        position=pos,
                        text=full_text,
                        context_header=header if self.prepend_header else None,
                        token_count=len(full_text.split()),
                    )
                )
                pos += 1

                # Calculate overlap by carrying over trailing words/paragraphs
                if self.overlap_tokens > 0 and current_words:
                    overlap_words = current_words[-self.overlap_tokens :]
                    current_words = list(overlap_words)
                    current_paragraphs = [" ".join(overlap_words)]
                else:
                    current_words = []
                    current_paragraphs = []

            current_paragraphs.append(para)
            current_words.extend(para_words)

        # Flush remaining words as final chunk
        if current_paragraphs:
            body_text = "\n\n".join(current_paragraphs)
            full_text = f"{header}\n\n{body_text}".strip() if header else body_text
            chunk_id = f"{section.section_id}_c{pos:03d}"

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=section.doc_id,
                    section_id=section.section_id,
                    company=section.company,
                    ticker=section.ticker,
                    fiscal_year=section.fiscal_year,
                    section_name=section.section_name,
                    position=pos,
                    text=full_text,
                    context_header=header if self.prepend_header else None,
                    token_count=len(full_text.split()),
                )
            )

        return chunks

    def chunk_all(self, sections: List[ParsedSection]) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        for s in sections:
            all_chunks.extend(self.chunk_section(s))
        logger.info(f"Generated {len(all_chunks)} structure-aware chunks across {len(sections)} sections.")
        return all_chunks
