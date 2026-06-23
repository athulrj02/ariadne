"""Central configuration for Ariadne."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings:
    # Project paths
    repo_root: Path = Path(__file__).resolve().parents[1]
    data_raw: Path = repo_root / "data" / "raw"
    data_processed: Path = repo_root / "data" / "processed"

    # CTD dataset filenames
    ctd_chem_disease: str = "CTD_chemicals_diseases.csv"
    ctd_exposure: str = "CTD_exposure_events.csv"
    ctd_pheno: str = "CTD_pheno_term_ixns.csv"

    # Neo4j connection
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")


settings = Settings()