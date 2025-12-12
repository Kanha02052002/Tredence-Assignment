from typing import Callable, Dict, Optional, Any, List
from loguru import logger
import asyncio
import uuid

from engine.models import StateModel


class GraphEngine:
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._node_registry: Dict[str, Callable] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}

    def register_node(self, fn_name: str, fn: Callable):
        logger.debug(f"Registering node function '{fn_name}'")
        self._node_registry[fn_name] = fn

    def create_graph(self, nodes: Dict[str, str], edges: Dict[str, str], start_node_id: str, overwrite_if_exists: bool = True) -> str:
        graph_id = str(uuid.uuid4())
        if not overwrite_if_exists:
            while graph_id in self._graphs:
                graph_id = str(uuid.uuid4())

        self._graphs[graph_id] = {
            "nodes": nodes,
            "edges": edges,
            "start_node_id": start_node_id,
        }
        logger.info(f"Graph created: {graph_id} with nodes {list(nodes.keys())}")
        return graph_id

    def graph_exists(self, graph_id: str) -> bool:
        return graph_id in self._graphs

    def create_run_placeholder(self, graph_id: str) -> str:
        run_id = str(uuid.uuid4())
        self._runs[run_id] = {
            "graph_id": graph_id,
            "state": None,
            "log": [],
            "status": "created",
        }
        return run_id

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._runs.get(run_id)

    async def execute_graph(self, graph_id: str, state: StateModel, run_id: Optional[str] = None, max_steps: int = 100) -> (StateModel, List[str]):
        if graph_id not in self._graphs:
            raise ValueError("Graph not found")

        graph = self._graphs[graph_id]
        nodes = graph["nodes"]
        edges = graph["edges"]
        current_node = graph["start_node_id"]

        if run_id is None:
            run_id = str(uuid.uuid4())

        self._runs[run_id] = {
            "graph_id": graph_id,
            "state": state,
            "log": [],
            "status": "running",
        }

        execution_log: List[str] = []
        steps = 0

        logger.info(f"Starting execution run {run_id} for graph {graph_id}")
        try:
            while current_node is not None and steps < max_steps:
                steps += 1
                execution_log.append(f"Executing node: {current_node}")
                run_record = self._runs[run_id]
                run_record["log"] = execution_log
                run_record["state"] = state

                fn_name = nodes.get(current_node)
                if fn_name is None:
                    raise RuntimeError(f"No function mapped for node id '{current_node}'")

                fn = self._node_registry.get(fn_name)
                if fn is None:
                    raise RuntimeError(f"Function '{fn_name}' not registered in node registry")

                logger.debug(f"Calling node function '{fn_name}' for node id '{current_node}'")

                if asyncio.iscoroutinefunction(fn):
                    result = await fn(state, self.tool_registry)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, fn, state, self.tool_registry)

                
                next_node: Optional[str] = None
                if isinstance(result, str) and result:
                    next_node = result
                    execution_log.append(f"Node '{current_node}' requested next node '{next_node}'")
                elif result is None:
                    next_node = edges.get(current_node)
                elif isinstance(result, dict) and "next" in result:
                    next_node = result.get("next")
                else:
                    next_node = edges.get(current_node)

                logger.debug(f"Transitioning from '{current_node}' to '{next_node}'")
                current_node = next_node

            
            self._runs[run_id]["status"] = "completed"
            self._runs[run_id]["state"] = state
            self._runs[run_id]["log"] = execution_log
            logger.info(f"Run {run_id} completed in {steps} steps")
            
            return state, execution_log
        except Exception as e:
            logger.exception("Execution failed: {}", e)
            self._runs[run_id]["status"] = "failed"
            self._runs[run_id]["log"] = execution_log + [f"error: {e}"]
            raise
