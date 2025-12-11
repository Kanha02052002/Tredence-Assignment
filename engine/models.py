from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# Shared/mutable state model used by nodes (sample CodeReviewState)
class StateModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        # allow mutation of fields
        allow_mutation = True

class CodeReviewState(StateModel):
    code_text: str = Field("", description="Raw code to be reviewed")
    functions: List[Dict] = Field(default_factory=list, description="Extracted function metadata")
    issues: List[Dict] = Field(default_factory=list, description="Detected issues")
    suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")
    quality_score: float = Field(0.0, description="Overall quality score (0-1)")
    metadata: Dict = Field(default_factory=dict)

# API models
class NodeDef(BaseModel):
    id: str
    fn_name: str

class CreateGraphRequest(BaseModel):
    nodes: List[NodeDef]
    edges: Dict[str, str]  # simple mapping as required
    start_node_id: str

class CreateGraphResponse(BaseModel):
    graph_id: str

class RunGraphRequest(BaseModel):
    graph_id: str
    initial_state: Dict

class RunGraphResponse(BaseModel):
    run_id: str
    final_state: Dict
    execution_log: List[str]

class RunStateResponse(BaseModel):
    run_id: str
    status: str
    state: Dict
    execution_log: List[str]
