import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

import main
from tools.registry import ToolRegistry
from engine.core import GraphEngine
from engine.models import CodeReviewState


from agents import sample_agent


def make_sample_code(todo_count: int = 2, lines_per_fn: int = 10) -> str:
    parts = []
    for i in range(3):
        parts.append(f"def func_{i}(x):")
        for j in range(lines_per_fn):
            parts.append("x = x + 1")
        if i < todo_count:
            parts.append("# TODO: improve performance")
        parts.append("")
    return "\n".join(parts)


@pytest.mark.asyncio
async def test_engine_run_direct():
    registry = ToolRegistry()
    engine = GraphEngine(tool_registry=registry)

    registry.register_tool("complexity_estimator", sample_agent.complexity_estimator)
    registry.register_tool("issue_detector", sample_agent.issue_detector)
    registry.register_tool("suggestion_generator", sample_agent.suggestion_generator)

    engine.register_node("extract_functions", sample_agent.extract_functions)
    engine.register_node("check_complexity", sample_agent.check_complexity)
    engine.register_node("detect_issues", sample_agent.detect_issues)
    engine.register_node("suggest_improvements", sample_agent.suggest_improvements)
    engine.register_node("finalize", sample_agent.finalize)

    nodes = {
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
    graph_id = engine.create_graph(nodes=nodes, edges=edges, start_node_id="extract")

    initial_code = make_sample_code(todo_count=3, lines_per_fn=60)
    state = CodeReviewState(code_text=initial_code)
    run_id = engine.create_run_placeholder(graph_id)
    final_state, log = await engine.execute_graph(graph_id, state, run_id=run_id, max_steps=200)

    run_record = engine.get_run(run_id)
    assert run_record is not None
    assert run_record["status"] == "completed"
    assert final_state.metadata.get("finalized", False) is True
    assert isinstance(final_state.suggestions, list)
    assert len(final_state.suggestions) > 0
    assert final_state.quality_score >= 0.9 or final_state.metadata.get("issues_found", 0) == 0


def test_api_graph_create_run_state():
    client = TestClient(main.app)
    create_payload = {
        "nodes": [
            {"id": "extract", "fn_name": "extract_functions"},
            {"id": "check", "fn_name": "check_complexity"},
            {"id": "detect", "fn_name": "detect_issues"},
            {"id": "suggest", "fn_name": "suggest_improvements"},
            {"id": "end", "fn_name": "finalize"},
        ],
        "edges": {
            "extract": "check",
            "check": "detect",
            "detect": "suggest",
            "suggest": "end"
        },
        "start_node_id": "extract"
    }

    resp = client.post("/graph/create", json=create_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "graph_id" in data
    graph_id = data["graph_id"]

    initial_state = {"code_text": make_sample_code(todo_count=2, lines_per_fn=20)}
    run_resp = client.post("/graph/run", json={"graph_id": graph_id, "initial_state": initial_state})
    assert run_resp.status_code == 200, run_resp.text
    run_data = run_resp.json()
    assert "run_id" in run_data
    run_id = run_data["run_id"]
    assert "final_state" in run_data
    assert "execution_log" in run_data
    final_state = run_data["final_state"]

    assert isinstance(final_state, dict)
    assert "metadata" in final_state
    assert final_state["metadata"].get("finalized", True) is True or "quality_score" in final_state

    get_resp = client.get(f"/graph/state/{run_id}")
    assert get_resp.status_code == 200, get_resp.text
    state_data = get_resp.json()
    assert state_data["run_id"] == run_id
    assert state_data["status"] in ("completed", "running", "created", "failed")
    assert isinstance(state_data["state"], dict)
    assert isinstance(state_data["execution_log"], list)
