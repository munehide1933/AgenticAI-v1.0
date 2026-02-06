from core.models import PipelineState, ProcessingMode


def route_after_understanding(state: PipelineState) -> str:
    understanding = state.get("understanding")
    if not understanding:
        return "synthesis"

    # Medical/Legal always search first
    if understanding.domain in ["medical", "legal"]:
        return "web_search"

    mode = state.get("processing_mode", ProcessingMode.BASIC)

    if mode == ProcessingMode.WEB_SEARCH or understanding.requires_web_search:
        return "web_search"
    else:
        return "initial_analysis"


def route_after_search(state: PipelineState) -> str:
    return "initial_analysis"


def route_after_initial_analysis(state: PipelineState) -> str:
    mode = state.get("processing_mode", ProcessingMode.BASIC)
    understanding = state.get("understanding")

    if mode == ProcessingMode.DEEP_THINKING:
        return "reflection"

    if understanding and understanding.requires_code:
        return "detailed_analysis"

    return "synthesis"


def route_after_reflection(state: PipelineState) -> str:
    understanding = state.get("understanding")
    if understanding and understanding.requires_code:
        return "detailed_analysis"
    return "synthesis"


def route_after_detailed_analysis(state: PipelineState) -> str:
    analysis = state.get("final_analysis")
    if analysis and analysis.needs_code:
        return "code_generation"
    return "synthesis"
