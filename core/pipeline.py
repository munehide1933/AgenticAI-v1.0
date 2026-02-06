import logging
import time
import uuid
from typing import Any, AsyncIterator, Dict

from database.session import session_mgr
from workflows.builder import create_workflow

from core.models import PipelineState, ProcessingMode

logger = logging.getLogger(__name__)


class AgentPipeline:
    def __init__(self):
        self.workflow = create_workflow()

    def run(
        self,
        query: str,
        session_id: str,
        language: str = "中文",
        enable_deep_thinking: bool = False,
        enable_web_search: bool = False,
    ) -> Dict[str, Any]:
        """同步运行（保持向后兼容）"""
        trace_id = str(uuid.uuid4())
        start_time = time.time()

        if enable_deep_thinking:
            mode = ProcessingMode.DEEP_THINKING
        elif enable_web_search:
            mode = ProcessingMode.WEB_SEARCH
        else:
            mode = ProcessingMode.BASIC

        logger.info(f"Pipeline started: trace_id={trace_id}, mode={mode}")

        session_mgr.add_message(session_id, "user", query)

        # 获取上下文记忆（最近 5 轮对话）
        conversation_history = self._get_conversation_context(session_id, limit=10)

        initial_state: PipelineState = {
            "session_id": session_id,
            "domain": "general",
            "language": language,
            "query": query,
            "conversation_history": conversation_history,  # 新增：上下文记忆
            "processing_mode": mode,
            "understanding": None,
            "web_search_results": None,
            "initial_analysis": None,
            "reflection": None,
            "final_analysis": None,
            "artifacts": [],
            "final_answer": None,
            "error": None,
        }

        try:
            final_state = self.workflow.invoke(initial_state)

            for artifact in final_state.get("artifacts", []):
                session_mgr.save_artifact(session_id, artifact)

            answer = final_state.get("final_answer", "No response generated.")
            session_mgr.add_message(
                session_id,
                "assistant",
                answer,
                {"trace_id": trace_id, "mode": mode.value},
            )

            elapsed = time.time() - start_time
            logger.info(f"Pipeline completed: {elapsed:.2f}s")

            return {
                "trace_id": trace_id,
                "answer": answer,
                "understanding": final_state.get("understanding"),
                "web_search_results": final_state.get("web_search_results"),
                "reflection": final_state.get("reflection"),
                "final_analysis": final_state.get("final_analysis"),
                "artifacts": final_state.get("artifacts", []),
                "elapsed": elapsed,
                "processing_mode": mode.value,
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            error_msg = f"Error: {str(e)}"
            session_mgr.add_message(session_id, "assistant", error_msg)
            return {"trace_id": trace_id, "answer": error_msg, "error": str(e)}

    async def run_streaming(
        self,
        query: str,
        session_id: str,
        language: str = "中文",
        enable_deep_thinking: bool = False,
        enable_web_search: bool = False,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式运行（异步生成器）"""
        trace_id = str(uuid.uuid4())
        start_time = time.time()

        if enable_deep_thinking:
            mode = ProcessingMode.DEEP_THINKING
        elif enable_web_search:
            mode = ProcessingMode.WEB_SEARCH
        else:
            mode = ProcessingMode.BASIC

        logger.info(f"Pipeline streaming started: trace_id={trace_id}, mode={mode}")

        session_mgr.add_message(session_id, "user", query)

        # 获取上下文记忆
        conversation_history = self._get_conversation_context(session_id, limit=10)

        # 发送初始状态
        yield {
            "type": "status",
            "content": "🤔 正在理解您的问题...",
            "step": "understanding",
        }

        initial_state: PipelineState = {
            "session_id": session_id,
            "domain": "general",
            "language": language,
            "query": query,
            "conversation_history": conversation_history,
            "processing_mode": mode,
            "understanding": None,
            "web_search_results": None,
            "initial_analysis": None,
            "reflection": None,
            "final_analysis": None,
            "artifacts": [],
            "final_answer": None,
            "error": None,
        }

        try:
            # 逐步执行 workflow 并发送进度
            current_state = initial_state

            # Understanding
            from agents.understanding import UnderstandingAgent

            understanding_agent = UnderstandingAgent()
            current_state = understanding_agent.understand(current_state)

            if current_state.get("error"):
                yield {"type": "error", "content": current_state["error"]}
                return

            yield {
                "type": "status",
                "content": f"✅ 已识别为 **{current_state['domain']}** 领域",
                "step": "understanding_complete",
            }

            # Web Search (如果需要)
            understanding = current_state.get("understanding")
            if understanding and understanding.requires_web_search:
                yield {
                    "type": "status",
                    "content": "🌐 正在搜索相关信息...",
                    "step": "searching",
                }

                from agents.search import WebSearchAgent

                search_agent = WebSearchAgent()
                current_state = search_agent.search(current_state)

                web_results = current_state.get("web_search_results")
                if web_results and web_results.results:
                    yield {
                        "type": "status",
                        "content": f"✅ 找到 {len(web_results.results)} 条相关信息",
                        "step": "search_complete",
                    }
            # 使用流式分析
            yield {
                "type": "status",
                "content": "📝 正在分析...",
                "step": "analyzing",
            }
            from agents.analysis import InitialAnalysisAgent

            analysis_agent = InitialAnalysisAgent()

            # 使用流式分析
            async for event in analysis_agent.analyze_streaming(current_state):
                event_type = event.get("type")

                if event_type == "content":
                    # 直接传递内容事件
                    yield event
                elif event_type == "analysis_complete":
                    # 更新状态
                    current_state = event["state"]
                elif event_type == "error":
                    # 传递错误
                    yield event
                    return

            # Deep Thinking (如果启用)
            if mode == ProcessingMode.DEEP_THINKING:
                yield {
                    "type": "status",
                    "content": "🧠 正在深度反思...",
                    "step": "reflecting",
                }

                from agents.reflection import ReflectionAgent

                reflection_agent = ReflectionAgent()
                current_state = reflection_agent.reflect(current_state)

                if current_state.get("reflection"):
                    yield {
                        "type": "status",
                        "content": "✅ 反思完成，正在优化答案...",
                        "step": "reflection_complete",
                    }

            # Code Generation (如果需要)
            if understanding and understanding.requires_code:
                yield {
                    "type": "status",
                    "content": "💻 正在生成代码...",
                    "step": "coding",
                }

                from agents.analysis import DetailedAnalysisAgent

                detailed_agent = DetailedAnalysisAgent()
                current_state = detailed_agent.analyze(current_state)

                if (
                    current_state.get("final_analysis")
                    and current_state["final_analysis"].needs_code
                ):
                    from agents.code_generator import CodeGenerationAgent

                    code_agent = CodeGenerationAgent()
                    current_state = code_agent.generate(current_state)

                    if current_state.get("artifacts"):
                        yield {
                            "type": "status",
                            "content": f"✅ 已生成 {len(current_state['artifacts'])} 个代码文件",
                            "step": "code_complete",
                        }

            # Synthesis
            yield {
                "type": "status",
                "content": "📋 正在整理最终答案...",
                "step": "synthesizing",
            }

            from agents.synthesis import SynthesisAgent

            synthesis_agent = SynthesisAgent()
            current_state = synthesis_agent.synthesize(current_state)

            # 保存 artifacts
            for artifact in current_state.get("artifacts", []):
                session_mgr.save_artifact(session_id, artifact)

            # 发送最终答案
            answer = current_state.get("final_answer", "No response generated.")
            session_mgr.add_message(
                session_id,
                "assistant",
                answer,
                {"trace_id": trace_id, "mode": mode.value},
            )

            elapsed = time.time() - start_time

            yield {
                "type": "final",
                "content": answer,
                "metadata": {
                    "trace_id": trace_id,
                    "elapsed": elapsed,
                    "understanding": current_state.get("understanding"),
                    "artifacts": current_state.get("artifacts", []),
                },
            }

        except Exception as e:
            logger.error(f"Pipeline streaming failed: {e}", exc_info=True)
            yield {"type": "error", "content": f"处理出错: {str(e)}"}

    def _get_conversation_context(self, session_id: str, limit: int = 10) -> str:
        """获取对话上下文（最近 N 条消息）"""
        messages = session_mgr.get_messages(session_id, limit=limit)

        if not messages:
            return ""

        # 格式化为对话历史
        context_parts = []
        for msg in messages[-limit:]:  # 只取最后 limit 条
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200]  # 每条限制 200 字符
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)


pipeline = AgentPipeline()
