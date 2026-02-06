import logging
import re

from config.language_styles import LANGUAGE_STYLES
from core.models import CodeArtifact, PipelineState
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class CodeGenerationAgent(BaseAgent):
    def __init__(self):
        super().__init__(use_coder=True)
        self.parser = StrOutputParser()

    def generate(self, state: PipelineState) -> PipelineState:
        analysis = state.get("final_analysis")

        if not analysis or not analysis.needs_code:
            logger.info("Code generation skipped")
            return state

        language = state.get("language", "中文")

        try:
            prompt = self._build_code_prompt(analysis, language)

            chain = (
                ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            f"{LANGUAGE_STYLES[language]['system_base']}\\n\\nGenerate comprehensive, production-ready code with detailed comments.",
                        ),
                        ("human", prompt),
                    ]
                )
                | self.llm
                | self.parser
            )

            response = chain.invoke({})
            artifact = self._parse_code_response(response)

            if artifact:
                state.setdefault("artifacts", []).append(artifact)
                logger.info(f"Code generated: {artifact.title}")

        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)

        return state

    def _build_code_prompt(self, analysis, language):
        prompt = f"""Generate code based on:
    
    Requirements:
    {chr(10).join(f"- {r}" for r in analysis.requirements)}
    
    Architecture:
    {analysis.architecture or "Not specified"}
    
    Tech Stack:
    {", ".join(analysis.tech_stack or [])}
    
    Format:
    TITLE: [title]
    LANGUAGE: [language]
    CODE:
    ```
    [code]
    ```
    EXPLANATION:
    [explanation]
    DEPENDENCIES:
    [dependencies]
    """
        return prompt

    def _parse_code_response(self, response):
        try:
            title = re.search(r"TITLE:\\s*(.+)", response)
            title = title.group(1).strip() if title else "Generated Code"

            lang = re.search(r"LANGUAGE:\\s*(\\w+)", response)
            lang = lang.group(1).strip().lower() if lang else "python"

            code_blocks = re.findall(r"```[\\w]*\\n(.*?)```", response, re.DOTALL)
            code = code_blocks[0].strip() if code_blocks else ""

            explanation = re.search(
                r"EXPLANATION:\\s*(.+?)(?:DEPENDENCIES:|$)", response, re.DOTALL
            )
            explanation = explanation.group(1).strip() if explanation else ""

            deps = re.findall(r"DEPENDENCIES:\\s*(.+)", response, re.DOTALL)
            dependencies = (
                [d.strip() for d in deps[0].split("\\n") if d.strip()] if deps else None
            )

            if code:
                return CodeArtifact(
                    title=title,
                    language=lang,
                    code=code,
                    explanation=explanation,
                    dependencies=dependencies,
                )
        except Exception as e:
            logger.error(f"Parse code failed: {e}", exc_info=True)

        return None
