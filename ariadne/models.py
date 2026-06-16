"""Shared data models for Ariadne."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator


class NodeType(str, Enum):
    CHEMICAL = "Chemical"
    DISEASE = "Disease"
    PHENOTYPE = "Phenotype"


class Predicate(str, Enum):
    CAUSES = "CAUSES"
    TREATS = "TREATS"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    INCREASES = "INCREASES"
    DECREASES = "DECREASES"
    LINKED_TO = "LINKED_TO"
    MARKER_MECHANISM = "MARKER_MECHANISM"


class Triplet(BaseModel):
    """A single knowledge graph triplet with provenance."""

    head: str
    head_id: Optional[str] = None
    head_type: NodeType

    predicate: Predicate

    tail: str
    tail_id: Optional[str] = None
    tail_type: NodeType

    source: str
    pubmed_ids: list[str] = []
    direct_evidence: Optional[str] = None

    @field_validator("head", "tail")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("pubmed_ids", mode="before")
    @classmethod
    def parse_pubmed_ids(cls, v) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            return [x.strip() for x in v.split("|") if x.strip()]
        return [str(v)]

    def is_self_loop(self) -> bool:
        return self.head.strip().lower() == self.tail.strip().lower()