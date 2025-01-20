"""RAGAS evaluation pipeline: faithfulness, answer relevancy, and HCPCS extraction metrics."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvalSample:
    """A single labeled evaluation sample for RAG or extraction evaluation."""

    question: str
    ground_truth_answer: str
    document_text: str
    hcpcs_codes: list[str] = field(default_factory=list)


@dataclass
class ExtractionMetrics:
    """Precision, recall, and F1 for HCPCS code extraction."""

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        """Fraction of extracted codes that are correct."""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        """Fraction of true codes that were extracted."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        """Harmonic mean of precision and recall."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def load_eval_dataset(csv_path: Path) -> list[EvalSample]:
    """Load evaluation samples from a CSV file.

    Expected columns: question, ground_truth_answer, document_text, hcpcs_codes.

    Args:
        csv_path: Path to the evaluation CSV.

    Returns:
        List of EvalSample objects.
    """
    samples = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes = [c.strip() for c in row.get("hcpcs_codes", "").split("|") if c.strip()]
            samples.append(EvalSample(
                question=row["question"],
                ground_truth_answer=row["ground_truth_answer"],
                document_text=row["document_text"],
                hcpcs_codes=codes,
            ))
    return samples


def run_ragas_evaluation(
    samples: list[EvalSample],
    pipeline_answer_fn: Any,
) -> dict[str, float]:
    """Run RAGAS evaluation for faithfulness and answer relevancy.

    Requires the 'ragas' package (>=0.1.0). Builds a RAGAS Dataset
    from pipeline outputs and evaluates with standard metrics.

    Args:
        samples: Labeled evaluation samples.
        pipeline_answer_fn: Callable(question, context) -> str answer.

    Returns:
        Dict with 'faithfulness' and 'answer_relevancy' scores.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness
    except ImportError:
        print(
            "RAGAS evaluation requires: pip install ragas datasets",
            file=sys.stderr,
        )
        return {"faithfulness": 0.0, "answer_relevancy": 0.0}

    questions, answers, contexts, ground_truths = [], [], [], []

    for sample in samples:
        questions.append(sample.question)
        ground_truths.append(sample.ground_truth_answer)
        contexts.append([sample.document_text])

        answer = pipeline_answer_fn(sample.question, sample.document_text)
        answers.append(answer)

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
    return {
        "faithfulness": float(result["faithfulness"]),
        "answer_relevancy": float(result["answer_relevancy"]),
    }


def run_extraction_evaluation(samples: list[EvalSample]) -> ExtractionMetrics:
    """Run HCPCS extraction evaluation against ground-truth codes.

    Args:
        samples: Evaluation samples with expected hcpcs_codes.

    Returns:
        Aggregate ExtractionMetrics.
    """
    from src.extraction.hcpcs_chain import extract_hcpcs_codes

    metrics = ExtractionMetrics()
    for sample in samples:
        result = extract_hcpcs_codes(sample.document_text)
        extracted = set(item["code"].upper() for item in result.get("hcpcs_codes", []))
        expected = set(c.upper() for c in sample.hcpcs_codes)
        metrics.true_positives += len(extracted & expected)
        metrics.false_positives += len(extracted - expected)
        metrics.false_negatives += len(expected - extracted)

    return metrics


def main() -> None:
    """CLI entry point for the RAGAS evaluation pipeline."""
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline with RAGAS metrics")
    parser.add_argument("dataset", type=Path, help="Path to evaluation CSV dataset")
    parser.add_argument("--output", "-o", type=Path, help="Write results to JSON file")
    parser.add_argument(
        "--skip-ragas", action="store_true", help="Skip RAGAS eval, only run extraction metrics"
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Error: dataset not found: {args.dataset}", file=sys.stderr)
        sys.exit(1)

    samples = load_eval_dataset(args.dataset)
    print(f"Loaded {len(samples)} evaluation samples")

    results: dict[str, Any] = {}

    print("\nRunning HCPCS extraction evaluation...")
    ext_metrics = run_extraction_evaluation(samples)
    results["extraction"] = {
        "precision": round(ext_metrics.precision, 4),
        "recall": round(ext_metrics.recall, 4),
        "f1": round(ext_metrics.f1, 4),
    }
    print(f"  Precision: {ext_metrics.precision:.4f}")
    print(f"  Recall:    {ext_metrics.recall:.4f}")
    print(f"  F1:        {ext_metrics.f1:.4f}")

    if not args.skip_ragas:
        print("\nRunning RAGAS faithfulness + relevancy evaluation...")
        ragas_scores = run_ragas_evaluation(samples, lambda q, ctx: q)
        results["ragas"] = ragas_scores
        print(f"  Faithfulness:     {ragas_scores['faithfulness']:.4f}")
        print(f"  Answer Relevancy: {ragas_scores['answer_relevancy']:.4f}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    main()
