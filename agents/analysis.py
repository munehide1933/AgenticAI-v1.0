import logging
from typing import Any, AsyncIterator, Dict

from config.language_styles import LANGUAGE_STYLES
from core.models import AnalysisResult, PipelineState
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class InitialAnalysisAgent(BaseAgent):
    def analyze(self, state: PipelineState) -> PipelineState:
        """同步分析（保持向后兼容）"""
        query = state["query"]
        language = state.get("language", "中文")
        understanding = state.get("understanding")
        web_results = state.get("web_search_results")
        conversation_history = state.get("conversation_history", "")

        try:
            context_parts = [f"User Query: {query}"]

            # 添加对话历史上下文
            if conversation_history:
                context_parts.append(f"\nConversation History:\n{conversation_history}")

            if understanding:
                context_parts.append(f"\nIntent: {understanding.intent}")
                context_parts.append(
                    f"Key Concepts: {', '.join(understanding.key_concepts)}"
                )

            if web_results and web_results.results:
                context_parts.append(f"\nWeb Search Results:\n{web_results.summary}")

            context = "\n".join(context_parts)

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        f"{LANGUAGE_STYLES[language]['system_base']}\n\nProvide comprehensive initial analysis based on the query and available information. Remember the conversation context to provide coherent responses.",
                    ),
                    ("human", context),
                ]
            )

            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({})

            state["initial_analysis"] = result
            logger.info("Initial analysis completed")

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            state["error"] = f"Analysis error: {str(e)}"

        return state

    async def analyze_streaming(
        self, state: PipelineState
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式分析（异步生成器）- 统一返回字典格式"""
        query = state["query"]
        language = state.get("language", "中文")
        understanding = state.get("understanding")
        web_results = state.get("web_search_results")
        conversation_history = state.get("conversation_history", "")

        try:
            context_parts = [f"User Query: {query}"]

            if conversation_history:
                context_parts.append(f"\nConversation History:\n{conversation_history}")

            if understanding:
                context_parts.append(f"\nIntent: {understanding.intent}")
                context_parts.append(
                    f"Key Concepts: {', '.join(understanding.key_concepts)}"
                )

            if web_results and web_results.results:
                context_parts.append(f"\nWeb Search Results:\n{web_results.summary}")

            context = "\n".join(context_parts)

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        f"{LANGUAGE_STYLES[language]['system_base']}\n\nProvide comprehensive analysis. Remember conversation context.",
                    ),
                    ("human", context),
                ]
            )

            # 使用流式输出
            full_response = ""
            async for chunk in self.llm.astream(prompt.format_messages()):
                content = chunk.content
                full_response += content

                # 统一返回字典格式，类型为 "content"
                yield {"type": "content", "content": content}

            # 分析完成后更新状态
            state["initial_analysis"] = full_response

            # 返回完成信号
            yield {"type": "analysis_complete", "state": state}

        except Exception as e:
            logger.error(f"Streaming analysis failed: {e}", exc_info=True)
            yield {"type": "error", "content": f"分析出错: {str(e)}"}


class DetailedAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.parser = JsonOutputParser(pydantic_object=AnalysisResult)

    def analyze(self, state: PipelineState) -> PipelineState:
        understanding = state.get("understanding")

        if not understanding or not understanding.requires_code:
            logger.info("Detailed analysis skipped")
            return state

        query = state["query"]
        language = state.get("language", "中文")
        initial = state.get("initial_analysis", "")
        conversation_history = state.get("conversation_history", "")

        try:
            context = f"Query: {query}\n\nInitial Analysis: {initial}"

            if conversation_history:
                context = f"Conversation History:\n{conversation_history}\n\n" + context

            system_prompt = (
                LANGUAGE_STYLES[language]["system_base"]
                + """

Provide detailed technical analysis for Arch/DEV tasks.

Output JSON with:
- requirements: Detailed requirements list
- architecture: Architecture description
- tech_stack: Recommended technologies
- clarifications: Questions needing clarification
- needs_code: true if code generation needed
- detailed_explanation: In-depth technical explanation"""
            )

            prompt = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", context)]
            )

            chain = prompt | self.llm | self.parser
            result = chain.invoke({})

            state["final_analysis"] = AnalysisResult(**result)
            logger.info("Detailed analysis completed")

        except Exception as e:
            logger.error(f"Detailed analysis failed: {e}", exc_info=True)

        return state
