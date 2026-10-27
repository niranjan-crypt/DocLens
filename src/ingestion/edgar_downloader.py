"""
SEC EDGAR Downloader for DocLens.
Fetches 10-K filings with rate-limiting, compliant User-Agent headers,
lineage tracking, and idempotent deduplication via SHA-256 checksums.
"""
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

from src.common.config import Config, load_config
from src.common.db import DatabaseManager, compute_file_checksum
from src.common.logger import get_logger
from src.common.models import DocumentMetadata

logger = get_logger("edgar_downloader")


class EdgarDownloader:
    """Downloads SEC Form 10-K filings with compliant rate limiting and idempotency."""

    SEC_SUBMISSIONS_API = "https://data.sec.gov/submissions/CIK{cik}.json"
    SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{primary_doc}"

    def __init__(self, config: Optional[Config] = None, db_manager: Optional[DatabaseManager] = None):
        self.config = config or load_config()
        self.db = db_manager or DatabaseManager(self.config.db_url)
        self.output_dir = Path(self.config.raw_filings_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # SEC strictly mandates 'Sample Company Name AdminContact@<sample company domain>.com'
        self.headers = {
            "User-Agent": f"{self.config.user_agent_name} {self.config.user_agent_email}",
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }
        self.sec_headers = {
            "User-Agent": f"{self.config.user_agent_name} {self.config.user_agent_email}",
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }

    def _sleep_rate_limit(self):
        """Ensure requests remain well below SEC rate limit (max 10 requests/sec)."""
        time.sleep(1.0 / self.config.sec_rate_limit)

    def _get_with_retry(self, url: str, headers: Dict[str, str]) -> requests.Response:
        """Fetch URL with exponential backoff on transient errors or 429."""
        backoff = self.config.backoff_factor
        for attempt in range(1, self.config.max_retries + 1):
            try:
                self._sleep_rate_limit()
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 429:
                    logger.warning(f"SEC Rate limited (429). Backing off {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.warning(f"Fetch {url} returned status {resp.status_code} (attempt {attempt})")
            except requests.RequestException as e:
                logger.warning(f"Network error fetching {url} on attempt {attempt}: {e}")
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError(f"Failed to fetch {url} after {self.config.max_retries} attempts")

    def fetch_company_submissions(self, cik: str) -> Dict:
        """Fetch company submission index from SEC EDGAR API."""
        cik_padded = cik.zfill(10)
        url = self.SEC_SUBMISSIONS_API.format(cik=cik_padded)
        resp = self._get_with_retry(url, headers=self.headers)
        return resp.json()

    def download_10k_filing(
        self,
        ticker: str,
        company_name: str,
        sector: str,
        cik: str,
        target_year: int,
    ) -> Optional[DocumentMetadata]:
        """Find, download, and register the 10-K filing for the requested fiscal year."""
        logger.info(f"Checking 10-K for {ticker} ({company_name}) FY {target_year}...")
        doc_id = f"{ticker}_10K_{target_year}"
        out_file = self.output_dir / f"{doc_id}.html"

        # Check local cache and database idempotency
        if out_file.exists():
            checksum = compute_file_checksum(out_file)
            existing_doc = self.db.get_document_by_checksum(checksum)
            if existing_doc:
                logger.info(f"Filing {doc_id} already ingested (checksum {checksum[:8]}...). Skipping.")
                return DocumentMetadata(
                    doc_id=existing_doc.doc_id,
                    company=existing_doc.company,
                    ticker=existing_doc.ticker,
                    sector=existing_doc.sector,
                    doc_type=existing_doc.doc_type,
                    fiscal_year=existing_doc.fiscal_year,
                    filing_date=existing_doc.filing_date,
                    source_url=existing_doc.source_url,
                    checksum=existing_doc.checksum,
                    file_path=existing_doc.file_path,
                    downloaded_at=existing_doc.downloaded_at,
                )

        try:
            submissions = self.fetch_company_submissions(cik)
            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            accession_numbers = recent.get("accessionNumber", [])
            primary_documents = recent.get("primaryDocument", [])
            filing_dates = recent.get("filingDate", [])
            report_dates = recent.get("reportDate", [])

            cik_int = str(int(cik))
            match_index = None

            for i, form in enumerate(forms):
                if form == "10-K":
                    report_date = report_dates[i] if i < len(report_dates) else ""
                    # Check report year or filing year
                    report_year = int(report_date.split("-")[0]) if report_date else None
                    if report_year == target_year or (not report_year and filing_dates[i].startswith(str(target_year))):
                        match_index = i
                        break

            if match_index is None:
                # Fallback: find latest 10-K
                for i, form in enumerate(forms):
                    if form == "10-K":
                        match_index = i
                        break

            if match_index is None:
                logger.error(f"No 10-K found for {ticker} in recent submissions.")
                return None

            accession = accession_numbers[match_index]
            accession_nodash = accession.replace("-", "")
            primary_doc = primary_documents[match_index]
            filing_date = filing_dates[match_index]
            doc_url = self.SEC_ARCHIVES_BASE.format(
                cik_int=cik_int,
                accession_nodash=accession_nodash,
                primary_doc=primary_doc,
            )

            logger.info(f"Downloading {doc_id} from {doc_url}...")
            resp = self._get_with_retry(doc_url, headers=self.sec_headers)
            content = resp.content

            with open(out_file, "wb") as f:
                f.write(content)

            checksum = hashlib.sha256(content).hexdigest()
            meta = DocumentMetadata(
                doc_id=doc_id,
                company=company_name,
                ticker=ticker,
                sector=sector,
                doc_type="10-K",
                fiscal_year=target_year,
                filing_date=filing_date,
                source_url=doc_url,
                checksum=checksum,
                file_path=str(out_file),
                downloaded_at=datetime.utcnow(),
            )
            self.db.register_document(meta)
            logger.info(f"Saved {doc_id} (checksum: {checksum[:8]}...)")
            return meta

        except Exception as e:
            logger.error(f"Failed to download 10-K for {ticker}: {e}")
            return None

    def download_all_target_filings(self) -> List[DocumentMetadata]:
        """Download all filings specified in configuration."""
        results = []
        for company in self.config.companies:
            for year in company.fiscal_years:
                doc = self.download_10k_filing(
                    ticker=company.ticker,
                    company_name=company.name,
                    sector=company.sector,
                    cik=company.cik,
                    target_year=year,
                )
                if doc:
                    results.append(doc)
        return results


if __name__ == "__main__":
    downloader = EdgarDownloader()
    docs = downloader.download_all_target_filings()
    print(f"Downloaded / Registered {len(docs)} filings.")
