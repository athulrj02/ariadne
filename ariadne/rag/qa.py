"""GraphRAG question answering - connects Ollama to Neo4j."""

import logging
from langchain_ollama import OllamaLLM
from ariadne.config import settings
from ariadne.graph.neo4j_client import GraphClient

logger = logging.getLogger(__name__)

# Few-shot examples to help Llama generate correct Cypher
CYPHER_EXAMPLES = """
# Question: Which chemicals cause alopecia?
# Cypher:
MATCH (h)-[r:RELATES_TO]->(t)
WHERE toLower(t.name) CONTAINS 'alopecia'
AND r.predicate = 'CAUSES'
RETURN h.name AS chemical, r.pubmed_ids AS evidence
LIMIT 10

# Question: What diseases are associated with lead?
# Cypher:
MATCH (h)-[r:RELATES_TO]->(t)
WHERE toLower(h.name) CONTAINS 'lead'
RETURN t.name AS disease, r.predicate AS relationship, r.pubmed_ids AS evidence
LIMIT 10

# Question: Which chemicals treat diabetes?
# Cypher:
MATCH (h)-[r:RELATES_TO]->(t)
WHERE toLower(t.name) CONTAINS 'diabet'
AND r.predicate = 'TREATS'
RETURN h.name AS chemical, r.pubmed_ids AS evidence
LIMIT 10
"""

CYPHER_PROMPT = """You are an expert at converting biomedical questions into Neo4j Cypher queries.

The graph has nodes with properties: name, node_type
Relationships are all called RELATES_TO with properties: predicate, pubmed_ids, source

Predicate values: CAUSES, TREATS, ASSOCIATED_WITH, INCREASES, DECREASES, LINKED_TO, MARKER_MECHANISM

Here are some examples:
{examples}

Now write ONLY a Cypher query for this question. No explanation, no markdown, just the query:
Question: {question}
Cypher:"""

ANSWER_PROMPT = """You are a helpful biomedical research assistant.

A user asked: {question}

The knowledge graph returned these results:
{results}

Write a clear, concise answer based only on these results. 
For each finding mention the PubMed evidence if available.
If no results were found, say so clearly.
"""


class AriadneQA:
    """Question answering over the Ariadne knowledge graph."""

    def __init__(self):
        self.llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )

    def _generate_cypher(self, question: str) -> str:
        """Use Llama to convert a natural language question to Cypher."""
        prompt = CYPHER_PROMPT.format(
            examples=CYPHER_EXAMPLES,
            question=question
        )
        cypher = self.llm.invoke(prompt)
        # Clean up any markdown the model might add
        cypher = cypher.strip()
        if "```" in cypher:
            cypher = cypher.split("```")[1]
            if cypher.startswith("cypher"):
                cypher = cypher[6:]
        return cypher.strip()

    def _run_query(self, cypher: str) -> list[dict]:
        """Run the Cypher query against Neo4j."""
        with GraphClient() as g:
            return g.run_cypher(cypher)

    def _generate_answer(self, question: str, results: list[dict]) -> str:
        """Use Llama to turn graph results into a plain English answer."""
        prompt = ANSWER_PROMPT.format(
            question=question,
            results=str(results[:20])  # limit to avoid token overflow
        )
        return self.llm.invoke(prompt)

    def ask(self, question: str) -> dict:
        """Ask a question and get a cited answer from the knowledge graph."""
        logger.info("Question: %s", question)

        # Step 1 — generate Cypher
        cypher = self._generate_cypher(question)
        logger.info("Generated Cypher:\n%s", cypher)

        # Step 2 — run against Neo4j
        try:
            results = self._run_query(cypher)
            logger.info("Got %d results", len(results))
        except Exception as exc:
            logger.error("Cypher failed: %s", exc)
            results = []

        # Step 3 — generate answer
        answer = self._generate_answer(question, results)

        return {
            "question": question,
            "cypher": cypher,
            "results": results,
            "answer": answer
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    qa = AriadneQA()

    questions = [
        "Which chemicals cause alopecia?",
        "What diseases are associated with lead?",
        "Which chemicals treat diabetes?",
    ]

    for question in questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        result = qa.ask(question)
        print(f"\nCypher:\n{result['cypher']}")
        print(f"\nAnswer:\n{result['answer']}")