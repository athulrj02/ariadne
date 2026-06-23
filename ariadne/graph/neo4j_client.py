"""Neo4j connection and graph loading."""

import logging
from neo4j import GraphDatabase

from ariadne.config import settings
from ariadne.models import Triplet

logger = logging.getLogger(__name__)


class GraphClient:
    """Manages Neo4j connection and graph operations."""

    def __init__(self):
        self._driver = None

    def connect(self):
        logger.info("Connecting to Neo4j at %s", settings.neo4j_uri)
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self._driver.verify_connectivity()
        logger.info("Connected successfully.")

    def close(self):
        if self._driver:
            self._driver.close()
            logger.info("Connection closed.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def setup_schema(self):
        """Create indexes for fast lookups."""
        logger.info("Setting up schema...")
        indexes = [
            "CREATE INDEX chemical_name IF NOT EXISTS FOR (n:Chemical) ON (n.name)",
            "CREATE INDEX disease_name IF NOT EXISTS FOR (n:Disease) ON (n.name)",
            "CREATE INDEX phenotype_name IF NOT EXISTS FOR (n:Phenotype) ON (n.name)",
        ]
        with self._driver.session() as session:
            for idx in indexes:
                session.run(idx)
        logger.info("Schema ready.")

    def load_triplets(self, triplets: list[Triplet], batch_size: int = 500):
        """Load triplets into Neo4j in batches."""
        logger.info("Loading %d triplets...", len(triplets))
        total = 0

        for i in range(0, len(triplets), batch_size):
            batch = triplets[i: i + batch_size]
            self._load_batch(batch)
            total += len(batch)
            if total % 10000 == 0:
                logger.info("  %d / %d loaded", total, len(triplets))

        logger.info("Done — %d triplets loaded.", total)

    def _load_batch(self, batch: list[Triplet]):
        """Load a single batch of triplets."""
        records = [{
            "head":      t.head,
            "head_id":   t.head_id or t.head,
            "head_type": t.head_type.value,
            "tail":      t.tail,
            "tail_id":   t.tail_id or t.tail,
            "tail_type": t.tail_type.value,
            "predicate": t.predicate.value,
            "source":    t.source,
            "pubmed_ids": t.pubmed_ids,
        } for t in batch]

        cypher = """
        UNWIND $records AS r

        MERGE (h {ontology_id: r.head_id})
        ON CREATE SET h.name = r.head,
                      h.node_type = r.head_type

        MERGE (t {ontology_id: r.tail_id})
        ON CREATE SET t.name = r.tail,
                      t.node_type = r.tail_type

        MERGE (h)-[rel:RELATES_TO {predicate: r.predicate, source: r.source}]->(t)
        ON CREATE SET rel.pubmed_ids = r.pubmed_ids
        """
        with self._driver.session() as session:
            session.run(cypher, records=records)

    def summary(self) -> dict:
        """Return node and edge counts."""
        with self._driver.session() as session:
            nodes = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
            edges = session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
        return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Test connection only
    with GraphClient() as g:
        print("Connection successful!")
        print("Summary:", g.summary())