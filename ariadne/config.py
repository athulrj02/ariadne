"""Central configuration for Ariadne."""

from pathlib import Path


class Settings:
    # Project root — the outer ariadne folder
    repo_root: Path = Path(__file__).resolve().parents[1]

    # Data folders
    data_raw: Path = repo_root / "data" / "raw"
    data_processed: Path = repo_root / "data" / "processed"

    # CTD dataset filenames
    ctd_chem_disease: str = "CTD_chemicals_diseases.csv"
    ctd_exposure: str = "CTD_exposure_events.csv"
    ctd_pheno: str = "CTD_pheno_term_ixns.csv"


settings = Settings()