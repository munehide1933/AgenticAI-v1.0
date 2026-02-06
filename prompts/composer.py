"""
Prompt Composer - Prompt 组合器

负责将多层 Prompt 组合成完整的系统提示词：
1. System Role (角色定义)
2. Task Definition (任务描述)
3. Available Tools (可用工具)
4. Reasoning Skills (推理技能)
5. User Preferences (用户偏好)
"""

import logging
from typing import Dict, List, Optional

from prompts.registry import get_prompt_registry

logger = logging.getLogger(__name__)


class PromptComposer:
    """
    Prompt 组合器
    
    实现分层 Prompt 架构，支持：
    - 灵活组合多个 Prompt 片段
    - 向后兼容 v1.0 的 Prompt
    - 错误容忍（某个部分缺失不会导致失败）
    
    使用示例:
        composer = get_prompt_composer()
        
        # 基础用法
        prompt = composer.compose(
            system_role="analyst",
            task="understanding",
            language="中文"
        )
        
        # 高级用法：包含工具和技能
        prompt = composer.compose(
            system_role="analyst",
            task="react",
            tools=["web_search", "code_search"],
            skills=["chain_of_thought"],
            language="中文"
        )
    """
    
    def __init__(self):
        """初始化 Composer"""
        self.registry = get_prompt_registry()
    
    def compose(
        self,
        system_role: str,
        task: Optional[str] = None,
        tools: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        user_preferences: Optional[Dict] = None,
        language: str = "中文",
        **kwargs
    ) -> str:
        """
        组合多层 Prompt
        
        组合顺序：
        1. System Role (角色定义) - 必需
        2. Task Definition (任务描述) - 可选
        3. Available Tools (可用工具) - 可选
        4. Reasoning Skills (推理技能) - 可选
        5. User Preferences (用户偏好) - 可选
        6. Additional Context (额外上下文) - 可选
        
        Args:
            system_role: 系统角色名称 (如 "analyst", "coder", "base")
            task: 任务名称 (如 "understanding", "code_generation")
            tools: 可用工具列表 (如 ["web_search", "code_search"])
            skills: 启用的推理技能 (如 ["chain_of_thought"])
            user_preferences: 用户偏好字典
            language: 语言 (中文, English, 日本語)
            **kwargs: 额外的模板变量（用于字符串格式化）
        
        Returns:
            完整的系统提示词
        
        Examples:
            # 基础分析任务
            prompt = composer.compose(
                system_role="analyst",
                task="understanding",
                language="中文"
            )
            
            # ReAct 任务（包含工具）
            prompt = composer.compose(
                system_role="analyst",
                task="react",
                tools=["web_search", "calculator"],
                skills=["chain_of_thought"],
                language="English"
            )
        """
        parts = []
        
        # 1. System Role（必需）
        try:
            role_prompt = self.registry.get("system", system_role, language=language)
            parts.append(self._format_section("ROLE", role_prompt))
        except ValueError:
            # 如果新 Prompt 不存在，尝试回退到 v1.0 的 base
            logger.warning(f"Role '{system_role}' not found, falling back to 'base'")
            try:
                role_prompt = self.registry.get("system", "base", language=language)
                parts.append(role_prompt)  # v1.0 格式不需要 section
            except ValueError as e:
                logger.error(f"Failed to load any system role: {e}")
                # 继续执行，不抛出异常
        
        # 2. Task Definition（可选）
        if task:
            try:
                task_prompt = self.registry.get("tasks", task, language=language)
                parts.append(self._format_section("TASK", task_prompt))
            except ValueError:
                logger.debug(f"Task '{task}' not found, skipping")
        
        # 3. Tools（可选）
        if tools:
            tools_section = self._compose_tools(tools, language)
            if tools_section:
                parts.append(self._format_section("AVAILABLE TOOLS", tools_section))
        
        # 4. Skills（可选）
        if skills:
            skills_section = self._compose_skills(skills, language)
            if skills_section:
                parts.append(self._format_section("REASONING SKILLS", skills_section))
        
        # 5. User Preferences（可选）
        if user_preferences:
            prefs_section = self._format_preferences(user_preferences)
            if prefs_section:
                parts.append(self._format_section("USER PREFERENCES", prefs_section))
        
        # 6. Additional Context（可选）
        if kwargs:
            # 只在有额外上下文时添加
            context_str = "\n".join(f"- {k}: {v}" for k, v in kwargs.items())
            parts.append(self._format_section("ADDITIONAL CONTEXT", context_str))
        
        # 组合所有部分
        full_prompt = "\n\n".join(parts)
        
        # 替换模板变量
        # 添加默认变量
        format_vars = {
            "language": language,
            **kwargs
        }
        
        try:
            full_prompt = full_prompt.format(**format_vars)
        except KeyError as e:
            logger.warning(f"Template variable not provided: {e}")
            # 不完全替换也可以继续使用
        
        return full_prompt
    
    def _compose_tools(self, tool_names: List[str], language: str) -> str:
        """
        组合工具说明
        
        Args:
            tool_names: 工具名称列表
            language: 语言
        
        Returns:
            工具说明文本
        """
        tool_descriptions = []
        
        for tool_name in tool_names:
            try:
                tool_prompt = self.registry.get("tools", tool_name, language=language)
                tool_descriptions.append(f"### {tool_name}\n\n{tool_prompt}")
            except ValueError:
                logger.debug(f"Tool description not found: {tool_name}")
                # 生成默认描述
                tool_descriptions.append(
                    f"### {tool_name}\n\nTool: {tool_name} (no description available)"
                )
        
        return "\n\n".join(tool_descriptions) if tool_descriptions else ""
    
    def _compose_skills(self, skill_names: List[str], language: str) -> str:
        """
        组合推理技能
        
        Args:
            skill_names: 技能名称列表
            language: 语言
        
        Returns:
            技能说明文本
        """
        skill_descriptions = []
        
        for skill_name in skill_names:
            try:
                skill_prompt = self.registry.get("skills", skill_name, language=language)
                skill_descriptions.append(skill_prompt)
            except ValueError:
                logger.debug(f"Skill not found: {skill_name}")
        
        return "\n\n".join(skill_descriptions) if skill_descriptions else ""
    
    def _format_preferences(self, preferences: Dict) -> str:
        """
        格式化用户偏好
        
        Args:
            preferences: 用户偏好字典
        
        Returns:
            格式化的偏好文本
        """
        if not preferences:
            return ""
        
        lines = []
        for key, value in preferences.items():
            # 转换 key 为可读格式
            readable_key = key.replace("_", " ").title()
            lines.append(f"- **{readable_key}**: {value}")
        
        return "\n".join(lines)
    
    def _format_section(self, title: str, content: str) -> str:
        """
        格式化章节
        
        Args:
            title: 章节标题
            content: 章节内容
        
        Returns:
            格式化的章节文本
        """
        return f"## {title}\n\n{content}"
    
    def compose_simple(self, system_role: str, language: str = "中文") -> str:
        """
        简化版本：只组合系统角色
        
        这个方法用于快速迁移 v1.0 代码，例如：
        
        旧代码:
            from config.language_styles import LANGUAGE_STYLES
            system_prompt = LANGUAGE_STYLES[language]["system_base"]
        
        新代码:
            from prompts.composer import get_prompt_composer
            composer = get_prompt_composer()
            system_prompt = composer.compose_simple("base", language=language)
        
        Args:
            system_role: 系统角色
            language: 语言
        
        Returns:
            系统提示词
        """
        return self.compose(system_role=system_role, language=language)
    
    def validate_composition(
        self,
        system_role: str,
        task: Optional[str] = None,
        tools: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        language: str = "中文"
    ) -> Dict[str, bool]:
        """
        验证组合的各个部分是否可用
        
        用于调试和测试
        
        Args:
            system_role: 系统角色
            task: 任务
            tools: 工具列表
            skills: 技能列表
            language: 语言
        
        Returns:
            验证结果字典
        
        Examples:
            >>> composer = get_prompt_composer()
            >>> result = composer.validate_composition(
            ...     system_role="analyst",
            ...     task="understanding",
            ...     tools=["web_search"],
            ...     language="中文"
            ... )
            >>> print(result)
            {
                'system_role': True,
                'task': True,
                'tools': {'web_search': True},
                'skills': {}
            }
        """
        result = {
            "system_role": self.registry.has_prompt("system", system_role, language),
            "task": self.registry.has_prompt("tasks", task, language) if task else None,
            "tools": {},
            "skills": {}
        }
        
        if tools:
            for tool in tools:
                result["tools"][tool] = self.registry.has_prompt("tools", tool, language)
        
        if skills:
            for skill in skills:
                result["skills"][skill] = self.registry.has_prompt("skills", skill, language)
        
        return result


# 全局单例
_composer: Optional[PromptComposer] = None


def get_prompt_composer() -> PromptComposer:
    """
    获取全局 Prompt Composer 单例
    
    Returns:
        PromptComposer 实例
    
    Examples:
        >>> composer = get_prompt_composer()
        >>> prompt = composer.compose(
        ...     system_role="analyst",
        ...     task="understanding"
        ... )
    """
    global _composer
    if _composer is None:
        _composer = PromptComposer()
    return _composer


def reset_prompt_composer():
    """重置全局 Composer（主要用于测试）"""
    global _composer
    _composer = None


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    composer = get_prompt_composer()
    
    # 测试 1: 简单组合
    print("\n" + "="*60)
    print("Test 1: Simple Composition")
    print("="*60)
    
    prompt = composer.compose_simple("base", language="中文")
    print(prompt[:200] + "...\n")
    
    # 测试 2: 验证组合
    print("="*60)
    print("Test 2: Validation")
    print("="*60)
    
    validation = composer.validate_composition(
        system_role="analyst",
        task="understanding",
        language="中文"
    )
    print(validation)
    print()
