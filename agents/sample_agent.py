from typing import Optional
import asyncio
from loguru import logger
from engine.models import CodeReviewState
from tools.registry import ToolRegistry



async def complexity_estimator(function_meta):
    await asyncio.sleep(0.05)
    code = function_meta.get("body", "")
    complexity = min(1.0, len(code) / 200.0)
    return complexity

async def issue_detector(function_meta):
    await asyncio.sleep(0.05)
    body = function_meta.get("body", "")
    issues = []
    if "TODO" in body or "FIXME" in body:
        issues.append({"type": "todo", "detail": "Found TODO/FIXME comment"})
    if len(body.splitlines()) > 50:
        issues.append({"type": "long_function", "detail": "Function body too long"})
    return issues

async def suggestion_generator(issues):
    await asyncio.sleep(0.02)
    suggestions = []
    for i, issue in enumerate(issues):
        suggestions.append(f"Suggestion {i+1}: Address issue {issue['type']} - {issue['detail']}")
    return suggestions
=
def complexity_estimator_sync(meta):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(complexity_estimator(meta))

def issue_detector_sync(meta):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(issue_detector(meta))

def suggestion_generator_sync(issues):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(suggestion_generator(issues))


async def extract_functions(state: CodeReviewState, tools: ToolRegistry) -> Optional[str]:
    await asyncio.sleep(0.05) 
    code = state.code_text or ""
    funcs = []
    parts = code.split("\n")
    current = None
    body_lines = []
    for line in parts:
        if line.strip().startswith("def "):
            if current:
                funcs.append({"name": current, "body": "\n".join(body_lines)})
            current = line.strip().split("(")[0].replace("def ", "")
            body_lines = []
        elif current:
            body_lines.append(line)
    if current:
        funcs.append({"name": current, "body": "\n".join(body_lines)})
    if not funcs:
        funcs = [{"name": "synthetic_main", "body": code}]

    state.functions = funcs
    state.metadata["extracted"] = len(funcs)
    logger.debug(f"extract_functions -> found {len(funcs)} functions")
    return None  





async def check_complexity(state: CodeReviewState, tools: ToolRegistry) -> Optional[str]:
    estimator = tools.get_tool("complexity_estimator")
    total = 0.0
    scores = []
    for f in state.functions:
        if asyncio.iscoroutinefunction(estimator):
            c = await estimator(f)
        else:
            c = estimator(f)
        scores.append(1.0 - c) 
        total += (1.0 - c)
    if scores:
        state.quality_score = sum(scores) / len(scores)
    else:
        state.quality_score = 0.0
    state.metadata["checked"] = True
    logger.debug(f"check_complexity -> quality_score={state.quality_score:.3f}")
    return None  


async def detect_issues(state: CodeReviewState, tools: ToolRegistry) -> Optional[str]:
    detector = tools.get_tool("issue_detector")
    all_issues = []
    for f in state.functions:
        if asyncio.iscoroutinefunction(detector):
            issues = await detector(f)
        else:
            issues = detector(f)
        for iss in issues:
            iss_entry = {"fn": f["name"], **iss}
            all_issues.append(iss_entry)
    state.issues = all_issues
    state.metadata["issues_found"] = len(all_issues)
    logger.debug(f"detect_issues -> found {len(all_issues)} issues")
    return None


async def suggest_improvements(state: CodeReviewState, tools: ToolRegistry) -> Optional[str]:
    sugg_gen = tools.get_tool("suggestion_generator")
    if asyncio.iscoroutinefunction(sugg_gen):
        suggestions = await sugg_gen(state.issues)
    else:
        suggestions = sugg_gen(state.issues)
    state.suggestions.extend(suggestions)
    state.quality_score = min(1.0, state.quality_score + 0.15 * (1.0 if state.issues else 0.5))
    logger.debug(f"suggest_improvements -> new quality_score={state.quality_score:.3f}")
    if state.quality_score < 0.9:
        logger.debug("Quality below threshold, looping back to 'check' node")
        return "check"  
    return None  


async def finalize(state: CodeReviewState, tools: ToolRegistry) -> Optional[str]:
    await asyncio.sleep(0.02)
    state.metadata["finalized"] = True
    return None
