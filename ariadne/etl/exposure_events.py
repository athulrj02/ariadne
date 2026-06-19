"""ETL pipeline for CTD_exposure_events.csv"""

import logging
from pathlib import Path

import pandas as pd

from ariadne.models import NodeType, Predicate, Triplet

logger = logging.getLogger(__name__)

COLUMNS = [
    "exposurestressorname", "exposurestressorid", "stressorsourcecategory",
    "stressorsourcedetails", "numberofstressorsamples", "stressornotes",
    "numberofreceptors", "receptors", "receptornotes", "smokingstatus",
    "age", "ageunitsofmeasurement", "agequalifier", "sex", "race",
    "methods", "detectionlimit", "detectionlimituom", "detectionfrequency",
    "medium", "exposuremarker", "exposuremarkerid", "markerlevel",
    "markerunitsofmeasurement", "markermeasurementstatistic", "assaynotes",
    "studycountries", "stateorprovince", "citytownregionarea",
    "exposureeventnotes", "outcomerelationship", "diseasename", "diseaseid",
    "phenotypename", "phenotypeid", "phenotypeactiondegreetype", "anatomy",
    "exposureoutcomenotes", "reference", "associatedstudytitles",
    "enrollmentstartyear", "enrollmentendyear", "studyfactors", "extra",
]

OUTCOME_RELATION_MAP = {
    "causes":      Predicate.CAUSES,
    "cause":       Predicate.CAUSES,
    "associated":  Predicate.ASSOCIATED_WITH,
    "association": Predicate.ASSOCIATED_WITH,
    "linked":      Predicate.LINKED_TO,
    "link":        Predicate.LINKED_TO,
}


def _resolve_predicate(value) -> Predicate:
    if pd.isna(value):
        return Predicate.LINKED_TO
    cleaned = str(value).strip().lower()
    for key, pred in OUTCOME_RELATION_MAP.items():
        if key in cleaned:
            return pred
    return Predicate.LINKED_TO


def _resolve_tail(row) -> tuple[str, NodeType] | None:
    """Return (name, NodeType) for the outcome — disease first, phenotype as fallback."""
    if pd.notna(row.get("diseasename")):
        return str(row["diseasename"]).strip(), NodeType.DISEASE
    if pd.notna(row.get("phenotypename")):
        return str(row["phenotypename"]).strip(), NodeType.PHENOTYPE
    return None


def load(path: Path) -> pd.DataFrame:
    logger.info("Loading %s", path)
    df = pd.read_csv(path, comment="#", header=None,
                     low_memory=False, names=COLUMNS)
    logger.info("Loaded %d rows", len(df))
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    original = len(df)

    # Drop rows with no stressor name
    df = df.dropna(subset=["exposurestressorname"])

    # Drop rows where both disease and phenotype are missing
    mask = df["diseasename"].notna() | df["phenotypename"].notna()
    df = df[mask]

    df = df.copy()
    df["Predicate"] = df["outcomerelationship"].apply(_resolve_predicate)

    # Remove duplicates on the triplet key
    df = df.drop_duplicates(
        subset=["exposurestressorname", "Predicate", "diseasename", "phenotypename"]
    )

    logger.info("Cleaned: %d → %d rows", original, len(df))
    return df


def to_triplets(df: pd.DataFrame) -> list[Triplet]:
    triplets = []
    skipped = 0

    for _, row in df.iterrows():
        try:
            outcome = _resolve_tail(row)
            if outcome is None:
                skipped += 1
                continue

            tail_name, tail_type = outcome
            tail_id = str(row["diseaseid"]) if tail_type == NodeType.DISEASE and pd.notna(row.get("diseaseid")) else None

            t = Triplet(
                head=row["exposurestressorname"],
                head_id=str(row["exposurestressorid"]) if pd.notna(row.get("exposurestressorid")) else None,
                head_type=NodeType.CHEMICAL,
                predicate=row["Predicate"],
                tail=tail_name,
                tail_id=tail_id,
                tail_type=tail_type,
                source="CTD_exposure_events",
                pubmed_ids=row.get("reference", ""),
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
    triplets = run(settings.data_raw / settings.ctd_exposure)
    print(f"\nTotal triplets: {len(triplets):,}")
    print("\nFirst 3 triplets:")
    for t in triplets[:3]:
        print(f"  {t.head} → {t.predicate.value} → {t.tail} [{t.tail_type.value}]")