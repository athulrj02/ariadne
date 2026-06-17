"""Download and extract CTD datasets automatically."""

import gzip
import logging
import shutil
from pathlib import Path

import requests

from ariadne.config import settings

logger = logging.getLogger(__name__)

# CTD direct download URLs
DATASETS = {
    "CTD_chemicals_diseases.csv": "https://ctdbase.org/reports/CTD_chemicals_diseases.csv.gz",
    "CTD_exposure_events.csv": "https://ctdbase.org/reports/CTD_exposure_events.csv.gz",
    "CTD_pheno_term_ixns.csv": "https://ctdbase.org/reports/CTD_pheno_term_ixns.csv.gz",
}


def download_file(url: str, destination: Path) -> None:
    """Download a single file from a URL and save it."""
    logger.info("Downloading %s", url)
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Saved to %s", destination)


def extract_gz(gz_path: Path, output_path: Path) -> None:
    """Extract a .gz file to a CSV."""
    logger.info("Extracting %s", gz_path)
    with gzip.open(gz_path, "rb") as f_in:
        with open(output_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    gz_path.unlink()  # delete the .gz after extracting
    logger.info("Extracted to %s", output_path)


def run() -> None:
    """Download and extract all three CTD datasets."""
    raw_dir = settings.data_raw
    raw_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in DATASETS.items():
        csv_path = raw_dir / filename

        # Skip if already downloaded
        if csv_path.exists():
            logger.info("Already exists, skipping: %s", filename)
            continue

        gz_path = raw_dir / (filename + ".gz")
        download_file(url, gz_path)
        extract_gz(gz_path, csv_path)

    logger.info("All datasets ready in %s", raw_dir)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    run()