"""ETL pipeline for CTD_chemicals_diseases.csv"""

import logging
from pathlib import Path

import pandas as pd

from ariadne.models import NodeType, Predicate, Triplet

logger = logging.getLogger(__name__)

DIRECT_EVIDENCE_MAP = {
    "marker/mechanism": Predicate.MARKER_MECHANISM,
    "therapeutic":      Predicate.TREATS,
}


def _resolve_predicate(direct_evidence) -> Predicate:
    if pd.isna(direct_evidence):
        return Predicate.ASSOCIATED_WITH
    cleaned = str(direct_evidence).strip().lower()
    return DIRECT_EVIDENCE_MAP.get(cleaned, Predicate.ASSOCIATED_WITH)


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, comment="#", low_memory=False,
                     header=None)
    df.columns = [
        "ChemicalName", "ChemicalID", "CasRN",
        "DiseaseName", "DiseaseID", "DirectEvidence",
        "InferenceGeneSymbol", "InferenceScore",
        "OmimIDs", "PubMedIDs"
    ]
    logger.info("Loaded %d rows", len(df))
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    original = len(df)

    df = df.dropna(subset=["ChemicalName", "DiseaseName"])

    mask = (
        df["ChemicalName"].str.strip().str.lower()
        !=
        df["DiseaseName"].str.strip().str.lower()
    )
    df = df[mask]

    df = df.copy()
    df["Predicate"] = df["DirectEvidence"].apply(_resolve_predicate)
    df = df.drop_duplicates(subset=["ChemicalName", "Predicate", "DiseaseName"])

    logger.info("Cleaned: %d → %d rows", original, len(df))
    return df


def to_triplets(df: pd.DataFrame) -> list[Triplet]:
    triplets = []
    skipped = 0

    for _, row in df.iterrows():
        try:
            t = Triplet(
                head=row["ChemicalName"],
                head_id=str(row["ChemicalID"]) if pd.notna(row.get("ChemicalID")) else None,
                head_type=NodeType.CHEMICAL,
                predicate=row["Predicate"],
                tail=row["DiseaseName"],
                tail_id=str(row["DiseaseID"]) if pd.notna(row.get("DiseaseID")) else None,
                tail_type=NodeType.DISEASE,
                source="CTD_chemicals_diseases",
                pubmed_ids=row.get("PubMedIDs", ""),
                direct_evidence=row.get("DirectEvidence") if pd.notna(row.get("DirectEvidence")) else None,
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
    triplets = run(settings.data_raw / settings.ctd_chem_disease)
    print(f"\nTotal triplets: {len(triplets):,}")
    print("\nFirst 3 triplets:")
    for t in triplets[:3]:
        print(f"  {t.head} → {t.predicate.value} → {t.tail}")