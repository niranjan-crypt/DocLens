"""
Citation Parser and Validator for DocLens.
Extracts citation tags [1], [2], maps them to retrieved chunks,
and validates citations against context boundaries to detect hallucinations.
"""
import re
from typing import List, Set, Tuple
from src.common.models import Citation, RetrievedChunk

CITATION_REGEX = re.compile(r"\[(\d+)\]")


class CitationParser:
    """Parses, validates, and extracts context citations from generated answers."""

    def parse_citations(
        self,
        answer_text: str,
        retrieved_chunks: List[RetrievedChunk],
    ) -> Tuple[List[Citation], float, List[int]]:
        """
        Extract citations and compute citation validity.

        Returns:
            Tuple of:
            - List of resolved Citation objects
            - Citation validity ratio (0.0 to 1.0)
            - List of hallucinated/invalid citation numbers
        """
        raw_matches = list(CITATION_REGEX.finditer(answer_text))
        if not raw_matches:
            # If no citations were generated (e.g. valid refusal), validity is 1.0
            return [], 1.0, []

        max_valid_index = len(retrieved_chunks)
        citations: List[Citation] = []
        seen_tags: Set[int] = set()
        invalid_tags: List[int] = []
        valid_count = 0

        for match in raw_matches:
            idx = int(match.group(1))
            tag_str = f"[{idx}]"

            if 1 <= idx <= max_valid_index:
                valid_count += 1
                if idx not in seen_tags:
                    seen_tags.add(idx)
                    retrieved_item = retrieved_chunks[idx - 1]
                    chunk = retrieved_item.chunk

                    # Take first sentence or 200 chars as verifiable snippet
                    clean_text = chunk.text.split("\n\n")[-1]
                    snippet = clean_text[:250].strip() + ("..." if len(clean_text) > 250 else "")

                    citations.append(
                        Citation(
                            tag=tag_str,
                            chunk_id=chunk.chunk_id,
                            company=chunk.company,
                            ticker=chunk.ticker,
                            fiscal_year=chunk.fiscal_year,
                            section_name=chunk.section_name,
                            snippet=snippet,
                            is_valid=True,
                        )
                    )
            else:
                invalid_tags.append(idx)
                citations.append(
                    Citation(
                        tag=tag_str,
                        chunk_id="UNKNOWN_HALLUCINATED_CHUNK",
                        company="N/A",
                        ticker="N/A",
                        fiscal_year=None,
                        section_name="Invalid Citation Tag",
                        snippet="Citation tag references non-existent context index.",
                        is_valid=False,
                    )
                )

        total_citations = len(raw_matches)
        validity_ratio = round(valid_count / total_citations, 4) if total_citations > 0 else 1.0
        return citations, validity_ratio, invalid_tags
