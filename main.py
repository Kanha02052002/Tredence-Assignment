from fastapi import FastAPI, HTTPException
from loguru import logger
import uuid
from typing import Dict
import asyncio

from engine.core import GraphEngine
from engine.models import (
    CreateGraphRequest,
    CreateGraphResponse,
    RunGraphRequest,
    RunGraphResponse,
    RunStateResponse,
    CodeReviewState,
)
from tools.registry import ToolRegistry
from agents import sample_agent

app = FastAPI(title="Minimal Workflow Engine")

# Instantiate global engine and tool registry
tool_registry = ToolRegistry()
engine = GraphEngine(tool_registry=tool_registry)

# Register tools used by sample agent
tool_registry.register_tool("complexity_estimator", sample_agent.complexity_estimator)
tool_registry.register_tool("issue_detector", sample_agent.issue_detector)
tool_registry.register_tool("suggestion_generator", sample_agent.suggestion_generator)

# Register node functions into the engine's node registry
engine.register_node("extract_functions", sample_agent.extract_functions)
engine.register_node("check_complexity", sample_agent.check_complexity)
engine.register_node("detect_issues", sample_agent.detect_issues)
engine.register_node("suggest_improvements", sample_agent.suggest_improvements)
engine.register_node("finalize", sample_agent.finalize)


@app.post("/graph/create", response_model=CreateGraphResponse)
async def create_graph(req: CreateGraphRequest):
    logger.info("Creating graph")
    graph_id = engine.create_graph(
        nodes={n.id: n.fn_name for n in req.nodes},
        edges=req.edges,
        start_node_id=req.start_node_id,
    )
    return CreateGraphResponse(graph_id=graph_id)


@app.post("/graph/run", response_model=RunGraphResponse)
async def run_graph(req: RunGraphRequest):
    # Validate graph exists
    if not engine.graph_exists(req.graph_id):
        raise HTTPException(status_code=404, detail="Graph not found")

    run_id = engine.create_run_placeholder(req.graph_id)
    # Build State model from the provided dictionary. Using CodeReviewState for the sample agent.
    try:
        state = CodeReviewState(**req.initial_state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid initial state: {e}")

    # Execute synchronously (await) to return final_state in response.
    final_state, log = await engine.execute_graph(req.graph_id, state, run_id=run_id)
    return RunGraphResponse(run_id=run_id, final_state=final_state.dict(), execution_log=log)


@app.get("/graph/state/{run_id}", response_model=RunStateResponse)
async def get_run_state(run_id: str):
    run = engine.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStateResponse(
        run_id=run_id,
        status=run["status"],
        state=run["state"].dict(),
        execution_log=run["log"],
    )

# Simple startup message with example graph creation to demonstrate usage
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: registering sample graph example (optional)")
    # Create a sample graph automatically (optional convenience)
    sample_nodes = {
        "extract": "extract_functions",
        "check": "check_complexity",
        "detect": "detect_issues",
        "suggest": "suggest_improvements",
        "end": "finalize",
    }
    edges = {
        "extract": "check",
        "check": "detect",
        "detect": "suggest",
        "suggest": "end",
    }
    g_id = engine.create_graph(nodes=sample_nodes, edges=edges, start_node_id="extract", overwrite_if_exists=False)
    logger.info(f"Sample graph created with id: {g_id}")
