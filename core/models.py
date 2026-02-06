from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel


class ProcessingMode(str, Enum):
    BASIC = "basic"
    DEEP_THINKING = "deep_thinking"
    WEB_SEARCH = "web_search"


class UnderstandingResult(BaseModel):
    intent: str
    domain: Literal["general", "Arch/DEV", "medical", "legal"]
    requires_web_search: bool = False
    requires_code: bool = False
    key_concepts: List[str] = []
    summary: str


class WebSearchResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    summary: str


class ReflectionResult(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    improvements: List[str]
    refined_answer: str


class AnalysisResult(BaseModel):
    requirements: List[str]
    architecture: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    clarifications: Optional[List[str]] = None
    needs_code: bool = False
    detailed_explanation: Optional[str] = None


class CodeArtifact(BaseModel):
    title: str
    language: str
    code: str
    explanation: str
    dependencies: Optional[List[str]] = None


class PipelineState(TypedDict):
    session_id: str
    domain: str
    language: str
    query: str
    conversation_history: str  # 新增：对话历史上下文
    processing_mode: ProcessingMode
    understanding: Optional[UnderstandingResult]
    web_search_results: Optional[WebSearchResult]
    initial_analysis: Optional[str]
    reflection: Optional[ReflectionResult]
    final_analysis: Optional[AnalysisResult]
    artifacts: List[CodeArtifact]
    final_answer: Optional[str]
    error: Optional[str]
