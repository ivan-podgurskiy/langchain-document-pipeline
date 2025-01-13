"""Chunking strategy comparison: recursive character splitter vs semantic splitter."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from src.ingestion.pdf_loader import load_pdf
from src.ingestion.splitter import split_document


@dataclass
class ChunkingStats:
    """Statistics for a single chunking strategy run."""

    strategy: str
    chunk_count: int
    avg_chunk_chars: float
    min_chunk_chars: int
    max_chunk_chars: int
    chunks_under_100_chars: int
    chunks_over_1500_chars: int

    def to_dict(self) -> dict:
        """Convert to plain dict for JSON serialization."""
        return {
            "strategy": self.strategy,
            "chunk_count": self.chunk_count,
            "avg_chunk_chars": round(self.avg_chunk_chars, 1),
            "min_chunk_chars": self.min_chunk_chars,
            "max_chunk_chars": self.max_chunk_chars,
            "chunks_under_100_chars": self.chunks_under_100_chars,
            "chunks_over_1500_chars": self.chunks_over_1500_chars,
        }


def compute_stats(chunks: list, strategy: str) -> ChunkingStats:
    """Compute statistics over a list of TextChunk objects.

    Args:
        chunks: List of TextChunk objects from a splitting run.
        strategy: Human-readable strategy name for labeling.

    Returns:
        ChunkingStats summary.
    """
    sizes = [c.char_count for c in chunks]
    return ChunkingStats(
        strategy=strategy,
        chunk_count=len(chunks),
        avg_chunk_chars=sum(sizes) / len(sizes) if sizes else 0.0,
        min_chunk_chars=min(sizes) if sizes else 0,
        max_chunk_chars=max(sizes) if sizes else 0,
        chunks_under_100_chars=sum(1 for s in sizes if s < 100),
        chunks_over_1500_chars=sum(1 for s in sizes if s > 1500),
    )


def run_comparison(pdf_path: Path) -> list[ChunkingStats]:
    """Run multiple chunking strategies on a single PDF and collect statistics.

    Tests:
    - Recursive splitter with small chunks (512 chars, 64 overlap)
    - Recursive splitter with medium chunks (1000 chars, 200 overlap) — default
    - Recursive splitter with large chunks (2000 chars, 400 overlap)

    Args:
        pdf_path: Path to the PDF file to analyze.

    Returns:
        List of ChunkingStats, one per strategy.
    """
    doc = load_pdf(pdf_path)
    all_stats = []

    strategies = [
        ("recursive_small", 512, 64),
        ("recursive_medium", 1000, 200),
        ("recursive_large", 2000, 400),
    ]

    for strategy_name, chunk_size, overlap in strategies:
        chunks = split_document(doc, chunk_size=chunk_size, chunk_overlap=overlap)
        stats = compute_stats(chunks, strategy=f"{strategy_name} (size={chunk_size}, overlap={overlap})")
        all_stats.append(stats)
        print(f"\n{stats.strategy}:")
        print(f"  Chunks: {stats.chunk_count}")
        print(f"  Avg size: {stats.avg_chunk_chars:.0f} chars")
        print(f"  Range: [{stats.min_chunk_chars}, {stats.max_chunk_chars}]")
        print(f"  Too small (<100): {stats.chunks_under_100_chars}")
        print(f"  Too large (>1500): {stats.chunks_over_1500_chars}")

    return all_stats


def main() -> None:
    """CLI entry point for chunking comparison."""
    parser = argparse.ArgumentParser(description="Compare chunking strategies on a PDF")
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    parser.add_argument("--output", "-o", type=Path, help="Write JSON results to file")
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"Error: PDF not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    print(f"Comparing chunking strategies for: {args.pdf.name}")
    stats_list = run_comparison(args.pdf)

    if args.output:
        results = [s.to_dict() for s in stats_list]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    main()
