"""ETL pipeline for CTD_pheno_term_ixns.csv"""

import logging
from pathlib import Path

import pandas as pd

from ariadne.models import NodeType, Predicate, Triplet

logger = logging.getLogger(__name__)

COLUMNS = [
    "chemicalname", "chemicalid", "casrn",
    "phenotypename", "phenotypeid", "comentionedterms",
    "organism", "organismid", "interaction",
    "interactionactions", "anatomyterms",
    "inferencegenesymbols", "pubmedids", "extra",
]

ACTION_MAP = {
    "increases":  Predicate.INCREASES,
    "decreases":  Predicate.DECREASES,
    "inhibits":   Predicate.DECREASES,
    "causes":     Predicate.CAUSES,
    "affects":    Predicate.ASSOCIATED_WITH,
    "associated": Predicate.ASSOCIATED_WITH,
}


def _resolve_predicate(action) -> Predicate:
    """Parse the first token before ^ in interactionactions.
    
    Example: 'decreases^phenotype' → DECREASES
    """
    if pd.isna(action):
        return Predicate.ASSOCIATED_WITH
    token = str(action).split("^")[0].strip().lower()
    return ACTION_MAP.get(token, Predicate.ASSOCIATED_WITH)


def load(path: Path) -> pd.DataFrame:
    logger.info("Loading %s", path)
    df = pd.read_csv(path, comment="#", header=None,
                     low_memory=False, names=COLUMNS)
    logger.info("Loaded %d rows", len(df))
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    original = len(df)

    df = df.dropna(subset=["chemicalname", "phenotypename"])

    # Remove self loops
    mask = (
        df["chemicalname"].str.strip().str.lower()
        !=
        df["phenotypename"].str.strip().str.lower()
    )
    df = df[mask]

    df = df.copy()
    df["Predicate"] = df["interactionactions"].apply(_resolve_predicate)
    df = df.drop_duplicates(subset=["chemicalname", "Predicate", "phenotypename"])

    logger.info("Cleaned: %d → %d rows", original, len(df))
    return df


def to_triplets(df: pd.DataFrame) -> list[Triplet]:
    triplets = []
    skipped = 0

    for _, row in df.iterrows():
        try:
            t = Triplet(
                head=row["chemicalname"],
                head_id=str(row["chemicalid"]) if pd.notna(row.get("chemicalid")) else None,
                head_type=NodeType.CHEMICAL,
                predicate=row["Predicate"],
                tail=row["phenotypename"],
                tail_id=str(row["phenotypeid"]) if pd.notna(row.get("phenotypeid")) else None,
                tail_type=NodeType.PHENOTYPE,
                source="CTD_pheno_term_ixns",
                pubmed_ids=row.get("pubmedids", ""),
            )
            if not t.is_self_loop():
                triplets.append(t)
        except Exception as exc:
            logger.debug("Skipped row: %s", exc)
            skipped += 1

    logger.info("Produced %d triplets (%d skipped)", len(triplets), skipped)
    return triplets


def run(path: Path) -> list[Triplet]:
    df = load(path)
    df = clean(df)
    return to_triplets(df)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    from ariadne.config import settings
    triplets = run(settings.data_raw / settings.ctd_pheno)
    print(f"\nTotal triplets: {len(triplets):,}")
    print("\nFirst 3 triplets:")
    for t in triplets[:3]:
        print(f"  {t.head} → {t.predicate.value} → {t.tail}")