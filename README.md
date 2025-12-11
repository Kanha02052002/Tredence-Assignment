```markdown
# Minimal Workflow Engine (FastAPI + Python)

This project implements a minimal, yet functional, agent workflow engine inspired by LangGraph.
It demonstrates fundamentals in Python structure, API creation, state management, and basic async concepts.

Features
- Core GraphEngine to orchestrate node execution.
- Nodes are Python functions that receive and mutate a shared Pydantic state model.
- ToolRegistry to register and provide callable tools used by nodes.
- Support for edges, branching (nodes can decide next node), and looping (node can return a previous node to repeat).
- FastAPI endpoints to create graphs, run graphs, and query run state.
- A sample workflow "Code Review Mini-Agent" with loop-back refinements.

How to run
1. Create a virtual environment and install dependencies:
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

   pip install -r requirements.txt

2. Run the FastAPI app with uvicorn:
   uvicorn main:app --reload

Endpoints
- POST /graph/create
  Request:
  {
    "nodes": [
      {"id": "extract", "fn_name": "extract_functions"},
      {"id": "check", "fn_name": "check_complexity"},
      {"id": "detect", "fn_name": "detect_issues"},
      {"id": "suggest", "fn_name": "suggest_improvements"},
      {"id": "end", "fn_name": "finalize"}
    ],
    "edges": {
      "extract": "check",
      "check": "detect",
      "detect": "suggest",
      "suggest": "end"
    },
    "start_node_id": "extract"
  }
  Response: { "graph_id": "<uuid>" }

- POST /graph/run
  Request:
  {
    "graph_id": "<graph_id>",
    "initial_state": {
      "code_text": "def foo():\\n    pass\\n# TODO: fix",
      "quality_score": 0.0
    }
  }
  Response includes run_id, final_state and execution_log.

- GET /graph/state/{run_id}
  Returns current state, status, and log for the given run.

Sample workflow implemented
Code Review Mini-Agent:
- extract_functions -> check_complexity -> detect_issues -> suggest_improvements -> (loop to check_complexity if quality_score < 0.9) -> finalize

Notes / possible improvements
- Persist graphs and runs to durable storage (database) instead of in-memory dicts.
- Add authentication/authorization.
- Add richer edge definitions (multiple explicit conditional edges) and a graph schema UI.
- Add timeout, concurrency control, and cancellation for running workflows.
- Add more sophisticated node I/O validation and types per node.

```