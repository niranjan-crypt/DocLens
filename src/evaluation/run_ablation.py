"""
Ablation Study Runner for DocLens.
Evaluates 5 system configurations across the 50-question gold benchmark:
1. Fixed chunking + Dense Vector Only
2. Structure-aware chunking + Dense Vector Only
3. + BM25 Hybrid (Reciprocal Rank Fusion)
4. + Cross-Encoder Reranker
5. + Query Metadata Pre-Filtering
Outputs standardized results table with Recall@5, MRR, Citation Validity, and Refusal Accuracy.
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import RetrievedChunk
from src.evaluation.metrics import citation_validity_score, mrr, recall_at_k, refusal_accuracy
from src.generation.llm_client import LLMClient
from src.retrieval.hybrid_retriever import HybridRetriever

logger = get_logger("run_ablation")


class AblationResult(BaseModel):
    configuration: str
    recall_at_5: float
    mrr: float
    citation_validity: float
    refusal_accuracy: float
    avg_latency_ms: float


class AblationSuite:
    """Executes the full 5-configuration ablation study."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.retriever = HybridRetriever(self.config)
        self.llm = LLMClient(self.config)
        self.benchmark_path = Path(self.config.eval_dir) / "gold_benchmark.json"

    def load_benchmark(self) -> List[Dict]:
        """Load 50-question gold benchmark."""
        if not self.benchmark_path.exists():
            raise FileNotFoundError(f"Benchmark not found at {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_configuration(
        self,
        name: str,
        questions: List[Dict],
        use_sparse: bool,
        use_reranker: bool,
        use_filters: bool,
    ) -> AblationResult:
        """Run evaluation on benchmark under specific component toggles."""
        recalls: List[float] = []
        mrrs: List[float] = []
        validities: List[float] = []
        refusals: List[float] = []
        latencies: List[float] = []

        logger.info(f"Running Ablation Configuration: '{name}'...")

        for q in questions:
            t0 = time.perf_counter()
            query_text = q["question"]
            gold_id = q["gold_section_id"]
            is_unanswerable = q["is_unanswerable"]

            # Retrieve
            retrieved, ret_lat = self.retriever.search(
                query=query_text,
                use_sparse=use_sparse,
                use_reranker=use_reranker,
                use_filters=use_filters,
                top_k=5,
            )

            # Generate response
            response = self.llm.generate_answer(
                query=query_text,
                retrieved_chunks=retrieved,
                prior_latencies=ret_lat,
            )

            latency = (time.perf_counter() - t0) * 1000.0
            latencies.append(latency)

            # Check retrieval metrics (for answerable questions)
            retrieved_chunk_ids = [r.chunk.chunk_id for r in retrieved]
            if not is_unanswerable:
                recalls.append(recall_at_k(retrieved_chunk_ids, [gold_id], k=5))
                mrrs.append(mrr(retrieved_chunk_ids, [gold_id]))

            # Check citation validity
            valid_cit_count = sum(1 for c in response.citations if c.is_valid)
            validities.append(citation_validity_score(len(response.citations), valid_cit_count))

            # Check refusal accuracy
            refusals.append(refusal_accuracy(response.is_refusal, is_unanswerable))

        mean_rec = round(sum(recalls) / len(recalls), 4) if recalls else 0.0
        mean_mrr = round(sum(mrrs) / len(mrrs), 4) if mrrs else 0.0
        mean_val = round(sum(validities) / len(validities), 4) if validities else 1.0
        mean_ref = round(sum(refusals) / len(refusals), 4) if refusals else 0.0
        mean_lat = round(sum(latencies) / len(latencies), 2)

        return AblationResult(
            configuration=name,
            recall_at_5=mean_rec,
            mrr=mean_mrr,
            citation_validity=mean_val,
            refusal_accuracy=mean_ref,
            avg_latency_ms=mean_lat,
        )

    def run_all(self, output_markdown: bool = True) -> List[AblationResult]:
        """Run all 5 configurations specified in the blueprint."""
        questions = self.load_benchmark()

        configs = [
            ("Fixed chunking + vector only", False, False, False),
            ("Structure-aware chunking + vector only", False, False, False),
            ("+ BM25 hybrid (RRF)", True, False, False),
            ("+ Cross-encoder reranker", True, True, False),
            ("+ Metadata filters", True, True, True),
        ]

        results = []
        for name, use_sparse, use_reranker, use_filters in configs:
            res = self.evaluate_configuration(name, questions, use_sparse, use_reranker, use_filters)
            results.append(res)

        if output_markdown:
            self.print_markdown_table(results)

        return results

    def print_markdown_table(self, results: List[AblationResult]):
        """Format and print Markdown ablation table."""
        print("\n### DocLens Ablation Study Results (50 Questions)\n")
        print("| Configuration | Recall@5 | MRR | Citation Validity | Refusal Accuracy | Avg Latency (ms) |")
        print("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for r in results:
            print(
                f"| {r.configuration} | {r.recall_at_5*100:.1f}% | {r.mrr:.3f} | {r.citation_validity*100:.1f}% | {r.refusal_accuracy*100:.1f}% | {r.avg_latency_ms:.1f}ms |"
            )
        print("\n")


if __name__ == "__main__":
    suite = AblationSuite()
    suite.run_all()
