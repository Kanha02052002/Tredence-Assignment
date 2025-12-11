from typing import Callable, Dict
from loguru import logger

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, fn: Callable):
        logger.debug(f"Registering tool: {name}")
        if name in self._tools:
            logger.warning(f"Overwriting existing tool '{name}'")
        self._tools[name] = fn

    def get_tool(self, name: str):
        fn = self._tools.get(name)
        if fn is None:
            raise KeyError(f"Tool '{name}' is not registered")
        return fn

    def list_tools(self):
        return list(self._tools.keys())
