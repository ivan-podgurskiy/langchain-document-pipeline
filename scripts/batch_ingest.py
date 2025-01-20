"""Batch ingestion CLI: process a directory of PDF files with a progress bar."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from tqdm import tqdm


async def ingest_file(pdf_path: Path, base_url: str) -> dict:
    """Send a single PDF to the /ingest endpoint.

    Corrupt or encrypted PDFs are caught and returned as failed entries
    rather than crashing the entire batch run.

    Args:
        pdf_path: Path to the PDF file.
        base_url: Base URL of the running FastAPI service.

    Returns:
        Dict with ingestion result or error info.
    """
    import httpx

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
            with open(pdf_path, "rb") as f:
                response = await client.post(
                    "/ingest/",
                    files={"file": (pdf_path.name, f, "application/pdf")},
                )
    except Exception as exc:
        # Network errors, connection refused, etc.
        return {"status": "failed", "reason": str(exc), "filename": pdf_path.name}

    if response.status_code == 409:
        return {"status": "skipped", "reason": "already_ingested", "filename": pdf_path.name}

    if response.status_code >= 400:
        # Server-side errors (e.g., corrupt PDF triggers 500)
        return {
            "status": "failed",
            "reason": f"HTTP {response.status_code}: {response.text[:200]}",
            "filename": pdf_path.name,
        }

    return response.json()


async def run_batch(
    directory: Path,
    base_url: str,
    concurrency: int = 3,
) -> dict:
    """Ingest all PDF files in a directory with controlled concurrency.

    Args:
        directory: Directory to scan for PDF files.
        base_url: Base URL of the running FastAPI service.
        concurrency: Maximum number of simultaneous ingest requests.

    Returns:
        Summary dict with counts of done, skipped, and failed files.
    """
    pdf_files = sorted(directory.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in: {directory}")
        return {"total": 0, "done": 0, "skipped": 0, "failed": 0}

    semaphore = asyncio.Semaphore(concurrency)
    results = {"total": len(pdf_files), "done": 0, "skipped": 0, "failed": 0}
    errors: list[dict] = []

    async def ingest_with_semaphore(path: Path) -> dict:
        async with semaphore:
            return await ingest_file(path, base_url)

    tasks = [ingest_with_semaphore(p) for p in pdf_files]

    with tqdm(total=len(tasks), desc="Ingesting PDFs", unit="file") as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            status = result.get("status", "done")
            results[status] = results.get(status, 0) + 1
            pbar.update(1)
            pbar.set_postfix(done=results["done"], skip=results["skipped"], fail=results["failed"])

    return results


def main() -> None:
    """CLI entry point for batch ingestion."""
    parser = argparse.ArgumentParser(
        description="Batch ingest a directory of PDF files into the document pipeline"
    )
    parser.add_argument("directory", type=Path, help="Directory containing PDF files")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="FastAPI service base URL"
    )
    parser.add_argument(
        "--concurrency", type=int, default=3, help="Max simultaneous uploads"
    )
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"Error: not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    results = asyncio.run(run_batch(args.directory, args.url, args.concurrency))

    print(f"\nBatch ingestion complete:")
    print(f"  Total:   {results['total']}")
    print(f"  Done:    {results['done']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Failed:  {results['failed']}")

    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
