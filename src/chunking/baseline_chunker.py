"""
Baseline Chunker for DocLens.
Implements standard naive fixed-token chunking with fixed token overlap.
Serves as Configuration 1 baseline in the ablation study.
"""
from typing import List
from src.common.models import Chunk, ParsedSection


class BaselineChunker:
    """Fixed-token chunker without structure awareness or context headers."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_section(self, section: ParsedSection) -> List[Chunk]:
        """Split section into naive fixed-word-window chunks."""
        words = section.clean_text.split()
        if not words:
            return []

        chunks: List[Chunk] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        pos = 0

        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            chunk_id = f"{section.section_id}_base_c{pos:03d}"

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
                    text=chunk_text,
                    context_header=None,  # Baseline does NOT have context headers
                    token_count=len(chunk_words),
                )
            )
            pos += 1

            if i + self.chunk_size >= len(words):
                break

        return chunks

    def chunk_all(self, sections: List[ParsedSection]) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        for s in sections:
            all_chunks.extend(self.chunk_section(s))
        return all_chunks
