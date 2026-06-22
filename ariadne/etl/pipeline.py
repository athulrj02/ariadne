"""Master ETL pipeline — combines all three CTD datasets."""

import json
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

from ariadne.config import settings
from ariadne.etl import chem_disease, exposure_events, pheno_term
from ariadne.models import Triplet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _deduplicate(triplets: list[Triplet]) -> list[Triplet]:
    """Remove exact duplicates across all three datasets."""
    seen = set()
    unique = []
    for t in triplets:
        key = (t.head.lower(), t.predicate.value, t.tail.lower())
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def run_all() -> list[Triplet]:
    """Run ETL for all three datasets and return unified triplets."""
    all_triplets = []

    datasets = [
        (chem_disease,    settings.data_raw / settings.ctd_chem_disease, "Chemicals-Diseases"),
        (exposure_events, settings.data_raw / settings.ctd_exposure,     "Exposure Events"),
        (pheno_term,      settings.data_raw / settings.ctd_pheno,        "Pheno-Term Interactions"),
    ]

    for module, path, label in datasets:
        if not path.exists():
            logger.warning("Dataset not found, skipping: %s", path)
            continue
        logger.info("── Running ETL: %s ──", label)
        triplets = module.run(path)
        all_triplets.extend(triplets)
        logger.info("  %d triplets from %s", len(triplets), label)

    before = len(all_triplets)
    all_triplets = _deduplicate(all_triplets)
    logger.info(
        "Deduplication: %d → %d triplets (removed %d duplicates)",
        before, len(all_triplets), before - len(all_triplets)
    )

    return all_triplets


def save(triplets: list[Triplet]) -> None:
    """Save unified triplets to JSON and CSV."""
    out = settings.data_processed
    out.mkdir(parents=True, exist_ok=True)

    # Save as JSON
    json_path = out / "triplets_unified.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([t.model_dump() for t in triplets], f, indent=2, default=str)
    logger.info("Saved JSON → %s", json_path)

    # Save as CSV
    rows = [{
        "head":      t.head,
        "head_id":   t.head_id or "",
        "head_type": t.head_type.value,
        "predicate": t.predicate.value,
        "tail":      t.tail,
        "tail_id":   t.tail_id or "",
        "tail_type": t.tail_type.value,
        "source":    t.source,
        "pubmed_ids": "|".join(t.pubmed_ids),
    } for t in triplets]

    csv_path = out / "triplets_unified.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    logger.info("Saved CSV → %s", csv_path)


if __name__ == "__main__":
    triplets = run_all()

    print(f"\nTotal unified triplets: {len(triplets):,}")

    print("\nBy source:")
    for src, n in Counter(t.source for t in triplets).most_common():
        print(f"  {src}: {n:,}")

    print("\nBy predicate:")
    for pred, n in Counter(t.predicate.value for t in triplets).most_common():
        print(f"  {pred}: {n:,}")

    save(triplets)
    print("\nSaved to data/processed/")