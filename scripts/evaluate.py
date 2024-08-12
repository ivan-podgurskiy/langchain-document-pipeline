"""Extraction accuracy evaluation script: precision and recall for HCPCS codes."""

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
    """A single labeled evaluation sample."""

    document_text: str
    expected_codes: list[str]  # uppercase HCPCS codes


@dataclass
class EvalMetrics:
    """Precision, recall, and F1 for extraction."""

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


def evaluate_sample(extracted: list[str], expected: list[str]) -> tuple[int, int, int]:
    """Compute TP/FP/FN for a single extraction result.

    Args:
        extracted: Codes returned by the extraction chain (uppercase).
        expected: Ground-truth codes for this document (uppercase).

    Returns:
        Tuple of (true_positives, false_positives, false_negatives).
    """
    extracted_set = set(c.upper() for c in extracted)
    expected_set = set(c.upper() for c in expected)
    tp = len(extracted_set & expected_set)
    fp = len(extracted_set - expected_set)
    fn = len(expected_set - extracted_set)
    return tp, fp, fn


def load_ground_truth(csv_path: Path) -> list[EvalSample]:
    """Load evaluation samples from a CSV file.

    Expected columns: document_text, hcpcs_codes (pipe-separated).

    Args:
        csv_path: Path to the ground-truth CSV file.

    Returns:
        List of EvalSample objects.
    """
    samples = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes = [c.strip() for c in row["hcpcs_codes"].split("|") if c.strip()]
            samples.append(EvalSample(
                document_text=row["document_text"],
                expected_codes=codes,
            ))
    return samples


def run_evaluation(ground_truth_path: Path, output_path: Path | None = None) -> EvalMetrics:
    """Run HCPCS extraction evaluation against a ground-truth dataset.

    Loads the extraction chain, runs it on each sample, and computes
    aggregate precision, recall, and F1.

    Args:
        ground_truth_path: Path to ground-truth CSV.
        output_path: Optional path to write per-sample results JSON.

    Returns:
        Aggregate EvalMetrics across all samples.
    """
    # Import here to avoid requiring the full pipeline at module import time
    from src.extraction.hcpcs_chain import extract_hcpcs_codes

    samples = load_ground_truth(ground_truth_path)
    total_metrics = EvalMetrics()
    per_sample_results = []

    print(f"Evaluating {len(samples)} samples...")

    for i, sample in enumerate(samples, start=1):
        result = extract_hcpcs_codes(sample.document_text)
        extracted_codes = [item["code"] for item in result.get("hcpcs_codes", [])]

        tp, fp, fn = evaluate_sample(extracted_codes, sample.expected_codes)
        total_metrics.true_positives += tp
        total_metrics.false_positives += fp
        total_metrics.false_negatives += fn

        per_sample_results.append({
            "sample_index": i,
            "expected": sample.expected_codes,
            "extracted": extracted_codes,
            "tp": tp, "fp": fp, "fn": fn,
        })

        if i % 10 == 0:
            print(f"  Processed {i}/{len(samples)} samples")

    print(f"\nResults:")
    print(f"  Precision: {total_metrics.precision:.4f}")
    print(f"  Recall:    {total_metrics.recall:.4f}")
    print(f"  F1:        {total_metrics.f1:.4f}")

    if output_path:
        output = {
            "metrics": {
                "precision": total_metrics.precision,
                "recall": total_metrics.recall,
                "f1": total_metrics.f1,
                "true_positives": total_metrics.true_positives,
                "false_positives": total_metrics.false_positives,
                "false_negatives": total_metrics.false_negatives,
            },
            "samples": per_sample_results,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\nDetailed results written to: {output_path}")

    return total_metrics


def main() -> None:
    """CLI entry point for the evaluation script."""
    parser = argparse.ArgumentParser(description="Evaluate HCPCS extraction accuracy")
    parser.add_argument("ground_truth", type=Path, help="Path to ground-truth CSV")
    parser.add_argument("--output", "-o", type=Path, help="Write results to JSON file")
    args = parser.parse_args()

    if not args.ground_truth.exists():
        print(f"Error: ground truth file not found: {args.ground_truth}", file=sys.stderr)
        sys.exit(1)

    metrics = run_evaluation(args.ground_truth, args.output)
    sys.exit(0 if metrics.f1 >= 0.8 else 1)


if __name__ == "__main__":
    main()
