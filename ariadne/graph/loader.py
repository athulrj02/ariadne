"""Loads unified triplets into Neo4j — supports resuming by dataset."""

import logging

from ariadne.config import settings
from ariadne.etl import chem_disease, exposure_events, pheno_term
from ariadne.graph.neo4j_client import GraphClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Each dataset with expected triplet count
DATASETS = [
    ("CTD_chemicals_diseases", chem_disease,    settings.data_raw / settings.ctd_chem_disease, 3602856),
    ("CTD_exposure_events",    exposure_events, settings.data_raw / settings.ctd_exposure,     6087),
    ("CTD_pheno_term_ixns",    pheno_term,      settings.data_raw / settings.ctd_pheno,        169334),
]


def already_loaded(client: GraphClient, source: str, expected: int) -> bool:
    """Check if a dataset is fully loaded by comparing counts."""
    result = client.run_cypher(
        "MATCH ()-[r:RELATES_TO {source: $source}]->() RETURN count(r) AS n",
        {"source": source}
    )
    actual = result[0]["n"]
    logger.info("  %s: %d / %d loaded", source, actual, expected)
    return actual >= expected


if __name__ == "__main__":
    with GraphClient() as g:
        g.setup_schema()

        for source_name, module, path, expected in DATASETS:
            if already_loaded(g, source_name, expected):
                logger.info("Already fully loaded — skipping: %s", source_name)
                continue

            logger.info("── Loading: %s ──", source_name)
            triplets = module.run(path)
            g.load_triplets(triplets)
            logger.info("Done: %s", source_name)

        summary = g.summary()

    print(f"\nGraph summary:")
    print(f"  Nodes:         {summary['nodes']:,}")
    print(f"  Relationships: {summary['edges']:,}")