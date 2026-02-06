import logging

from config.language_styles import LANGUAGE_STYLES
from core.models import PipelineState, ProcessingMode, ReflectionResult
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ReflectionAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.parser = JsonOutputParser(pydantic_object=ReflectionResult)

    def reflect(self, state: PipelineState) -> PipelineState:
        if state["processing_mode"] != ProcessingMode.DEEP_THINKING:
            logger.info("Reflection skipped")
            return state

        initial_analysis = state.get("initial_analysis")
        if not initial_analysis:
            return state

        language = state.get("language", "中文")

        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """%s

Perform self-reflection on your initial analysis. Critically evaluate:
1. Strengths of this analysis
2. Potential weaknesses or gaps
3. Improvements that can be made
4. Provide a refined, improved answer

Output JSON with: strengths (list), weaknesses (list), improvements (list), refined_answer (string)"""
                        % LANGUAGE_STYLES[language]["system_base"],
                    ),
                    (
                        "human",
                        f"Initial Analysis:\n{initial_analysis}\n\nPerform critical self-reflection.",
                    ),
                ]
            )

            chain = prompt | self.llm | self.parser
            result = chain.invoke({})

            state["reflection"] = ReflectionResult(**result)
            logger.info("Reflection completed")

        except Exception as e:
            logger.error(f"Reflection failed: {e}", exc_info=True)

        return state
