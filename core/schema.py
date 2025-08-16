from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Profit(BaseModel):
    idea: str
    explanation: str


class Node(BaseModel):
    id: str
    parent_id: Optional[str]
    text: str
    type: Literal["seed", "outcome"]
    profit: Optional[Profit] = None


class RunResult(BaseModel):
    seed: str
    nodes: List[Node]


# Expert/moderator workflow
class ExpertOutcome(BaseModel):
    outcome: str
    explanation: str
    profit: Optional[Profit] = None


class ExpertResponse(BaseModel):
    expert: Literal["geo", "econ", "tech", "social"]
    outcomes: List[ExpertOutcome]


class FinalSelection(BaseModel):
    scenario: str
    selected_outcomes: List[ExpertOutcome]


# Single expert response
class ExpertSingleResponse(BaseModel):
    expert: Literal["geo", "econ", "tech", "social"]
    outcome: str
    explanation: str


# Tree output
class TreeNode(BaseModel):
    expert: Optional[Literal["geo", "econ", "tech", "social"]] = None
    outcome: str
    explanation: str
    profit: Optional[Profit] = None
    children: List["TreeNode"] = Field(default_factory=list)


class TreeResult(BaseModel):
    scenario: str
    children: List[TreeNode]


def node_to_dict(node: Node) -> Dict[str, Any]:
    data = node.model_dump()
    return data


