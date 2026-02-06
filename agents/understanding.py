import logging
import json
import re

from config.language_styles import LANGUAGE_STYLES
from core.models import PipelineState, UnderstandingResult
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class UnderstandingAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.parser = JsonOutputParser(pydantic_object=UnderstandingResult)

    def understand(self, state: PipelineState) -> PipelineState:
        query = state["query"]
        language = state.get("language", "中文")

        try:
            # 构建系统提示(简洁版,避免模板变量冲突)
            analysis_instruction = """

Analyze user queries professionally to understand intent and requirements.

**CRITICAL**: Output ONLY a valid JSON object with these exact fields:
- intent: string (main user intention)
- domain: string (one of: "general", "Arch/DEV", "medical", "legal")
- requires_web_search: boolean (true if needs current/real-time information)
- requires_code: boolean (true if needs code generation)
- key_concepts: array of strings (key technical concepts)
- summary: string (brief professional summary)

**Rules**:
1. For medical/legal domains: ALWAYS set requires_web_search=true
2. For Arch/DEV with coding tasks: Set requires_code=true
3. DO NOT include any text before or after the JSON
4. Output MUST be valid, parseable JSON

**Domain Selection**:
- "general": General questions, conversations, information requests
- "Arch/DEV": Software architecture, coding, development tasks
- "medical": Health, medical, clinical questions
- "legal": Law, regulations, legal matters"""

            system_prompt = (
                LANGUAGE_STYLES[language]["system_base"] + analysis_instruction
            )

            prompt = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", "{query}")]
            )

            chain = prompt | self.llm
            response = chain.invoke({"query": query})
            
            # 提取 LLM 响应内容
            llm_output = response.content if hasattr(response, 'content') else str(response)
            
            # 尝试从响应中提取 JSON(容错处理)
            result = self._extract_json(llm_output)

            state["understanding"] = UnderstandingResult(**result)
            state["domain"] = state["understanding"].domain

            logger.info(f"Understanding: domain={state['domain']}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Understanding failed: {error_msg}", exc_info=True)

            # 检查是否是内容过滤错误
            if (
                "content_filter" in error_msg
                or "ResponsibleAIPolicyViolation" in error_msg
            ):
                state["error"] = (
                    "您的请求触发了内容安全策略。请调整您的问题后重试。如果您认为这是误判,请联系管理员。"
                )
            else:
                state["error"] = f"理解分析错误: {error_msg}"

        return state

    def _extract_json(self, text: str) -> dict:
        """
        从 LLM 输出中提取 JSON 对象(多层容错)
        
        Args:
            text: LLM 原始输出
            
        Returns:
            解析后的字典
        """
        # 清理文本
        text = text.strip()
        
        try:
            # 方法1: 直接解析整个文本
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 方法2: 提取 ```json 代码块
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # 方法3: 提取 ``` 代码块(不带语言标识)
        code_match = re.search(r'```\s*\n(.*?)\n```', text, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # 方法4: 提取 {} 包裹的 JSON 对象
        # 寻找第一个 { 和配对的 }
        try:
            start = text.index('{')
            brace_count = 0
            end = start
            
            for i, char in enumerate(text[start:], start=start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            pass
        
        # 方法5: Fallback - 返回默认值
        logger.warning(f"All JSON extraction methods failed. Raw output: {text[:300]}...")
        
        # 尝试从文本中推断 domain
        domain = "general"
        if any(kw in text.lower() for kw in ["code", "代码", "开发", "架构", "dev", "arch"]):
            domain = "Arch/DEV"
        elif any(kw in text.lower() for kw in ["medical", "health", "医疗", "健康"]):
            domain = "medical"
        elif any(kw in text.lower() for kw in ["legal", "law", "法律", "法规"]):
            domain = "legal"
        
        return {
            "intent": "用户咨询",
            "domain": domain,
            "requires_web_search": domain in ["medical", "legal"],
            "requires_code": domain == "Arch/DEV",
            "key_concepts": [],
            "summary": text[:150] if len(text) < 150 else text[:147] + "..."
        }
