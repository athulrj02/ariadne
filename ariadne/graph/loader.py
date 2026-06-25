"""Loads unified triplets into Neo4j."""

import logging

from ariadne.etl.pipeline import run_all
from ariadne.graph.neo4j_client import GraphClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # Step 1 — run ETL pipeline
    logger.info("Starting ETL pipeline...")
    triplets = run_all()
    logger.info("ETL complete — %d triplets ready.", len(triplets))

    # Step 2 — load into Neo4j
    with GraphClient() as g:
        g.setup_schema()
        g.load_triplets(triplets)
        summary = g.summary()

    print(f"\nGraph loaded successfully!")
    print(f"  Nodes:         {summary['nodes']:,}")
    print(f"  Relationships: {summary['edges']:,}")