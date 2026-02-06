from agents.analysis import DetailedAnalysisAgent, InitialAnalysisAgent
from agents.code_generator import CodeGenerationAgent
from agents.reflection import ReflectionAgent
from agents.search import WebSearchAgent
from agents.synthesis import SynthesisAgent
from agents.understanding import UnderstandingAgent
from core.models import PipelineState
from langgraph.graph import END, StateGraph

from workflows.routers import (
    route_after_detailed_analysis,
    route_after_initial_analysis,
    route_after_reflection,
    route_after_search,
    route_after_understanding,
)


def create_workflow():
    understanding_agent = UnderstandingAgent()
    web_search_agent = WebSearchAgent()
    initial_analysis_agent = InitialAnalysisAgent()
    reflection_agent = ReflectionAgent()
    detailed_analysis_agent = DetailedAnalysisAgent()
    code_generation_agent = CodeGenerationAgent()
    synthesis_agent = SynthesisAgent()

    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("understand", understanding_agent.understand)
    workflow.add_node("web_search", web_search_agent.search)
    workflow.add_node("initial_analysis", initial_analysis_agent.analyze)
    workflow.add_node("reflection", reflection_agent.reflect)
    workflow.add_node("detailed_analysis", detailed_analysis_agent.analyze)
    workflow.add_node("code_generation", code_generation_agent.generate)
    workflow.add_node("synthesis", synthesis_agent.synthesize)

    # Entry point
    workflow.set_entry_point("understand")

    # Build graph
    workflow.add_conditional_edges(
        "understand",
        route_after_understanding,
        {
            "web_search": "web_search",
            "initial_analysis": "initial_analysis",
            "synthesis": "synthesis",
        },
    )

    workflow.add_conditional_edges(
        "web_search", route_after_search, {"initial_analysis": "initial_analysis"}
    )

    workflow.add_conditional_edges(
        "initial_analysis",
        route_after_initial_analysis,
        {
            "reflection": "reflection",
            "detailed_analysis": "detailed_analysis",
            "synthesis": "synthesis",
        },
    )

    workflow.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {"detailed_analysis": "detailed_analysis", "synthesis": "synthesis"},
    )

    workflow.add_conditional_edges(
        "detailed_analysis",
        route_after_detailed_analysis,
        {"code_generation": "code_generation", "synthesis": "synthesis"},
    )

    workflow.add_edge("code_generation", "synthesis")
    workflow.add_edge("synthesis", END)

    return workflow.compile()
