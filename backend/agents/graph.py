"""LangGraph StateGraph — compiles the 9-node RCA workflow into a real graph.

Falls back to the sequential chain (run_workflow) if graph compilation fails.
"""
from typing import Any, Dict

from backend.agents.state import RCAAgentState
from backend.utils.logging import logger

# Module-level compiled graph (or None if compilation fails).
compiled_rca_graph: Any = None

try:
    from langgraph.graph import StateGraph, END

    from backend.agents.workflow import rca_workflow

    # LangGraph requires TypedDict or dict-based state; Pydantic models need
    # model_config allowing arbitrary types.  We build the graph over dict
    # state and wrap/unwrap RCAAgentState at the boundaries.

    def _to_dict(state: RCAAgentState) -> Dict[str, Any]:
        return state.model_dump()

    def _from_dict(d: Dict[str, Any]) -> RCAAgentState:
        return RCAAgentState(**d)

    # ── Node wrappers (operate on dict state) ───────────────────────────
    def _planner(state: dict) -> dict:
        return _to_dict(rca_workflow.planner_node(_from_dict(state)))

    def _log_analysis(state: dict) -> dict:
        return _to_dict(rca_workflow.log_analysis_node(_from_dict(state)))

    def _trace_analysis(state: dict) -> dict:
        return _to_dict(rca_workflow.trace_analysis_node(_from_dict(state)))

    def _exception_analysis(state: dict) -> dict:
        return _to_dict(rca_workflow.exception_analysis_node(_from_dict(state)))

    def _metrics(state: dict) -> dict:
        return _to_dict(rca_workflow.metrics_node(_from_dict(state)))

    def _git_deployment(state: dict) -> dict:
        return _to_dict(rca_workflow.git_deployment_node(_from_dict(state)))

    def _rag_retrieval(state: dict) -> dict:
        return _to_dict(rca_workflow.rag_retrieval_node(_from_dict(state)))

    def _confidence(state: dict) -> dict:
        return _to_dict(rca_workflow.confidence_node(_from_dict(state)))

    def _final_rca(state: dict) -> dict:
        return _to_dict(rca_workflow.final_rca_node(_from_dict(state)))

    # ── Conditional edge routers ────────────────────────────────────────
    def _after_planner(state: dict) -> str:
        """Route to log_analysis (always runs first after planner)."""
        return "log_analysis"

    def _after_exception(state: dict) -> str:
        """Skip metrics_node when run_metric_agent is False."""
        plan = state.get("execution_plan", {})
        if plan.get("run_metric_agent", False):
            return "metrics"
        return "git_deployment"

    def _after_metrics(state: dict) -> str:
        """Skip git_deployment_node when run_deployment_agent is False."""
        plan = state.get("execution_plan", {})
        if plan.get("run_deployment_agent", False):
            return "git_deployment"
        return "rag_retrieval"

    def _after_git(state: dict) -> str:
        return "rag_retrieval"

    # ── Build graph ─────────────────────────────────────────────────────
    builder = StateGraph(dict)

    builder.add_node("planner", _planner)
    builder.add_node("log_analysis", _log_analysis)
    builder.add_node("trace_analysis", _trace_analysis)
    builder.add_node("exception_analysis", _exception_analysis)
    builder.add_node("metrics", _metrics)
    builder.add_node("git_deployment", _git_deployment)
    builder.add_node("rag_retrieval", _rag_retrieval)
    builder.add_node("confidence", _confidence)
    builder.add_node("final_rca", _final_rca)

    builder.set_entry_point("planner")

    # Planner → Log (always)
    builder.add_edge("planner", "log_analysis")
    # Log → Trace
    builder.add_edge("log_analysis", "trace_analysis")
    # Trace → Exception
    builder.add_edge("trace_analysis", "exception_analysis")
    # Exception → conditional (metrics or skip)
    builder.add_conditional_edges("exception_analysis", _after_exception, {
        "metrics": "metrics",
        "git_deployment": "git_deployment",
    })
    # Metrics → conditional (git_deployment or skip)
    builder.add_conditional_edges("metrics", _after_metrics, {
        "git_deployment": "git_deployment",
        "rag_retrieval": "rag_retrieval",
    })
    # Git → RAG
    builder.add_edge("git_deployment", "rag_retrieval")
    # RAG → Confidence
    builder.add_edge("rag_retrieval", "confidence")
    # Confidence → Final RCA
    builder.add_edge("confidence", "final_rca")
    # Final RCA → END
    builder.add_edge("final_rca", END)

    compiled_rca_graph = builder.compile()
    logger.info("LangGraph RCA StateGraph compiled successfully")

except Exception as exc:
    logger.error(
        "LangGraph StateGraph compilation failed",
        error=str(exc),
    )
    raise
