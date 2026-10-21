"""
Automated Data Quality Gate for DocLens.
Executes 16 rigorous structural, lexical, and integrity checks on parsed documents
before chunking and vector indexing. Fails loudly with detailed diagnostics.
"""
import re
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import ParsedSection

logger = get_logger("quality_gate")


class QualityCheckResult(BaseModel):
    check_name: str
    passed: bool
    details: str
    severity: str = "ERROR"  # "ERROR" or "WARNING"


class QualityGateReport(BaseModel):
    total_sections_checked: int
    total_checks_run: int
    passed_checks: int
    failed_checks: int
    is_success: bool
    results: List[QualityCheckResult]


class DataQualityGate:
    """Enterprise Data Quality Gatekeeper with 16 automated tests."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()

    def run_all_checks(self, sections: List[ParsedSection]) -> QualityGateReport:
        """Run all 16 quality gatekeeper tests on a list of parsed sections."""
        results: List[QualityCheckResult] = []

        if not sections:
            results.append(
                QualityCheckResult(
                    check_name="Q01_no_empty_corpus",
                    passed=False,
                    details="Section list is completely empty.",
                )
            )
            return QualityGateReport(
                total_sections_checked=0,
                total_checks_run=1,
                passed_checks=0,
                failed_checks=1,
                is_success=False,
                results=results,
            )

        # 1. Non-empty text check
        empty_secs = [s.section_id for s in sections if not s.clean_text.strip()]
        results.append(
            QualityCheckResult(
                check_name="Q01_no_empty_sections",
                passed=len(empty_secs) == 0,
                details=f"Empty sections found: {len(empty_secs)} {empty_secs[:3]}",
            )
        )

        # 2. Minimum character count (> 300 chars)
        short_secs = [s.section_id for s in sections if s.char_count < 300]
        results.append(
            QualityCheckResult(
                check_name="Q02_min_char_count",
                passed=len(short_secs) == 0,
                details=f"Sections below 300 chars: {len(short_secs)} {short_secs[:3]}",
            )
        )

        # 3. Maximum character count sanity bound (< 1,500,000 chars)
        oversized = [s.section_id for s in sections if s.char_count > 1500000]
        results.append(
            QualityCheckResult(
                check_name="Q03_max_char_count",
                passed=len(oversized) == 0,
                details=f"Sections exceeding 1.5M chars: {len(oversized)}",
            )
        )

        # 4. Garbage character ratio limit
        garbage_fails = [
            s.section_id
            for s in sections
            if s.garbage_ratio > self.config.max_garbage_char_ratio
        ]
        results.append(
            QualityCheckResult(
                check_name="Q04_garbage_character_ratio",
                passed=len(garbage_fails) == 0,
                details=f"Sections exceeding {self.config.max_garbage_char_ratio*100:.1f}% garbage: {len(garbage_fails)} {garbage_fails[:3]}",
            )
        )

        # 5. Token count positive and sane (> 50 tokens)
        low_tokens = [s.section_id for s in sections if s.token_count < 50]
        results.append(
            QualityCheckResult(
                check_name="Q05_positive_token_counts",
                passed=len(low_tokens) == 0,
                details=f"Sections below 50 tokens: {len(low_tokens)}",
            )
        )

        # 6. doc_id non-empty and well-formed
        bad_doc_ids = [s.section_id for s in sections if not s.doc_id or len(s.doc_id) < 3]
        results.append(
            QualityCheckResult(
                check_name="Q06_valid_doc_ids",
                passed=len(bad_doc_ids) == 0,
                details=f"Malformed doc_ids: {len(bad_doc_ids)}",
            )
        )

        # 7. Company name non-empty
        bad_company = [s.section_id for s in sections if not s.company or len(s.company.strip()) < 2]
        results.append(
            QualityCheckResult(
                check_name="Q07_valid_company_names",
                passed=len(bad_company) == 0,
                details=f"Missing company names: {len(bad_company)}",
            )
        )

        # 8. Ticker symbol valid (1-6 uppercase chars)
        bad_tickers = [
            s.section_id
            for s in sections
            if not re.match(r"^[A-Z0-9\.\-]{1,8}$", s.ticker)
        ]
        results.append(
            QualityCheckResult(
                check_name="Q08_valid_ticker_symbols",
                passed=len(bad_tickers) == 0,
                details=f"Invalid ticker symbols: {len(bad_tickers)} {bad_tickers[:3]}",
            )
        )

        # 9. Fiscal year sanity (between 2000 and 2030 or None for timeless rules)
        bad_years = [
            s.section_id
            for s in sections
            if s.fiscal_year is not None and not (2000 <= s.fiscal_year <= 2030)
        ]
        results.append(
            QualityCheckResult(
                check_name="Q09_valid_fiscal_years",
                passed=len(bad_years) == 0,
                details=f"Fiscal years outside 2000-2030: {len(bad_years)}",
            )
        )

        # 10. Section name contains recognizable header (Item or Regulation)
        bad_headers = [
            s.section_id
            for s in sections
            if not any(k in s.section_name.lower() for k in ["item", "regulation", "rule", "chapter", "full"])
        ]
        results.append(
            QualityCheckResult(
                check_name="Q10_valid_section_name_format",
                passed=len(bad_headers) == 0,
                details=f"Sections missing recognized header keyword: {len(bad_headers)}",
            )
        )

        # 11. No duplicate section IDs
        seen_ids: Set[str] = set()
        duplicate_ids: List[str] = []
        for s in sections:
            if s.section_id in seen_ids:
                duplicate_ids.append(s.section_id)
            seen_ids.add(s.section_id)
        results.append(
            QualityCheckResult(
                check_name="Q11_unique_section_ids",
                passed=len(duplicate_ids) == 0,
                details=f"Duplicate section IDs: {len(duplicate_ids)} {duplicate_ids[:3]}",
            )
        )

        # 12. No duplicate section text (Jaccard token similarity < 0.95)
        duplicate_pairs: List[Tuple[str, str]] = []
        for i in range(min(len(sections), 50)):
            tokens_i = set(sections[i].clean_text.lower().split()[:200])
            for j in range(i + 1, min(len(sections), 50)):
                tokens_j = set(sections[j].clean_text.lower().split()[:200])
                if tokens_i and tokens_j:
                    jaccard = len(tokens_i & tokens_j) / len(tokens_i | tokens_j)
                    if jaccard > self.config.duplicate_jaccard_threshold:
                        duplicate_pairs.append((sections[i].section_id, sections[j].section_id))
        results.append(
            QualityCheckResult(
                check_name="Q12_no_duplicate_section_text",
                passed=len(duplicate_pairs) == 0,
                details=f"Highly duplicated text pairs (>95% Jaccard): {len(duplicate_pairs)}",
            )
        )

        # 13. No remaining raw HTML markup tags
        html_leakage = [
            s.section_id
            for s in sections
            if re.search(r"<(?:div|span|script|style|table|tr|td)[\s>]", s.clean_text, re.IGNORECASE)
        ]
        results.append(
            QualityCheckResult(
                check_name="Q13_no_unrendered_html_tags",
                passed=len(html_leakage) == 0,
                details=f"Sections with residual HTML tags: {len(html_leakage)}",
            )
        )

        # 14. No excessive blank newlines (collapsed properly)
        newline_issues = [
            s.section_id for s in sections if re.search(r"\n{4,}", s.clean_text)
        ]
        results.append(
            QualityCheckResult(
                check_name="Q14_clean_whitespace_structure",
                passed=len(newline_issues) == 0,
                details=f"Sections with 4+ consecutive newlines: {len(newline_issues)}",
            )
        )

        # 15. Table of contents rejection: 10-K sections must be substantial (> 1000 chars)
        toc_leaks = [
            s.section_id
            for s in sections
            if "item" in s.section_id.lower() and s.char_count < 1000
        ]
        results.append(
            QualityCheckResult(
                check_name="Q15_toc_snippet_rejection",
                passed=len(toc_leaks) == 0,
                details=f"10-K sections suspiciously short (< 1000 chars, likely TOC leak): {len(toc_leaks)}",
            )
        )

        # 16. Minimum sections per 10-K document (at least 2 narrative items extracted)
        doc_section_counts: Dict[str, int] = {}
        for s in sections:
            if "10K" in s.doc_id:
                doc_section_counts[s.doc_id] = doc_section_counts.get(s.doc_id, 0) + 1
        underextracted = [
            doc_id
            for doc_id, count in doc_section_counts.items()
            if count < self.config.min_sections_per_filing
        ]
        results.append(
            QualityCheckResult(
                check_name="Q16_min_sections_per_filing",
                passed=len(underextracted) == 0,
                details=f"Filings with fewer than {self.config.min_sections_per_filing} sections: {len(underextracted)}",
            )
        )

        failed_count = sum(1 for r in results if not r.passed)
        passed_count = len(results) - failed_count

        report = QualityGateReport(
            total_sections_checked=len(sections),
            total_checks_run=len(results),
            passed_checks=passed_count,
            failed_checks=failed_count,
            is_success=(failed_count == 0),
            results=results,
        )

        logger.info(
            f"Quality Gate Report: {passed_count}/{len(results)} checks passed. Success: {report.is_success}"
        )
        return report
