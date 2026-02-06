import logging

from config.language_styles import LANGUAGE_STYLES
from core.models import PipelineState

logger = logging.getLogger(__name__)


class SynthesisAgent:
    def synthesize(self, state: PipelineState) -> PipelineState:
        language = state.get("language", "中文")
        domain = state["domain"]
        understanding = state.get("understanding")
        web_results = state.get("web_search_results")
        initial_analysis = state.get("initial_analysis")
        reflection = state.get("reflection")
        final_analysis = state.get("final_analysis")
        artifacts = state.get("artifacts", [])

        if state.get("error"):
            state["final_answer"] = f"Error: {state['error']}"
            return state

        response_parts = []

        # Understanding summary
        if understanding:
            response_parts.append("### 需求理解 / Understanding\n")
            response_parts.append(f"**意图:** {understanding.intent}")
            response_parts.append(f"**领域:** {understanding.domain}")
            response_parts.append(
                f"**关键概念:** {', '.join(understanding.key_concepts)}\n"
            )

        # Web search results
        if web_results and web_results.results:
            response_parts.append("\n### 网络搜索结果 / Web Search Results\n")
            for i, result in enumerate(web_results.results[:3], 1):
                response_parts.append(f"{i}. **{result.get('title', 'Untitled')}**")
                response_parts.append(f"   {result.get('url', '')}")
                response_parts.append(f"   {result.get('content', '')[:200]}...\n")

        # 深度思考模式：优先显示反思后的内容
        if reflection:
            response_parts.append(
                "\n### 深度分析（经过反思优化）/ Deep Analysis (Refined)\n"
            )

            # 显示反思过程（折叠）
            response_parts.append("\n**反思过程:**")
            response_parts.append(
                f"- ✅ **优势:** {', '.join(reflection.strengths[:2])}"
            )  # 只显示前2个
            response_parts.append(
                f"- ⚠️ **改进点:** {', '.join(reflection.weaknesses[:2])}"
            )

            # 显示优化后的答案（这是最终答案）
            response_parts.append("\n**最终分析结果:**\n")
            response_parts.append(reflection.refined_answer)

        # 普通模式：显示初步分析
        elif initial_analysis:
            response_parts.append("\n### 分析结果 / Analysis\n")
            response_parts.append(initial_analysis)

        # Detailed technical analysis (仅 Arch/DEV 域)
        if final_analysis:
            response_parts.append("\n---\n")
            response_parts.append("\n### 技术方案 / Technical Solution\n")

            response_parts.append("**需求清单:**")
            for req in final_analysis.requirements:
                response_parts.append(f"- {req}")

            if final_analysis.architecture:
                response_parts.append(f"\n**系统架构:**\n{final_analysis.architecture}")

            if final_analysis.tech_stack:
                response_parts.append(
                    f"\n**技术栈:** {', '.join(final_analysis.tech_stack)}"
                )

            if final_analysis.detailed_explanation:
                response_parts.append(
                    f"\n**详细说明:**\n{final_analysis.detailed_explanation}"
                )

        # Code artifacts
        if artifacts:
            response_parts.append("\n---\n")
            response_parts.append("\n### 代码实现 / Code Implementation\n")

            for i, artifact in enumerate(artifacts, 1):
                response_parts.append(f"\n**{i}. {artifact.title}**\n")
                response_parts.append(f"```{artifact.language}\n{artifact.code}\n```\n")

                if artifact.explanation:
                    response_parts.append(f"**说明:** {artifact.explanation}\n")

                if artifact.dependencies:
                    response_parts.append(
                        f"**依赖项:** `{' | '.join(artifact.dependencies)}`\n"
                    )

        # Domain-specific disclaimers
        disclaimers = LANGUAGE_STYLES.get(language, LANGUAGE_STYLES["中文"])
        if domain == "medical":
            response_parts.append(disclaimers["medical_disclaimer"])
        elif domain == "legal":
            response_parts.append(disclaimers["legal_disclaimer"])

        state["final_answer"] = "\n".join(response_parts)
        return state
