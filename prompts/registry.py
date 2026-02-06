"""
Prompt Registry - 中央 Prompt 管理器

负责加载和管理所有 Prompt 模板，支持：
1. 从 v1.0 的 config/language_styles.py 加载传统 Prompt
2. 从 prompts/ 子目录动态加载新 Prompt 模板
3. 提供向后兼容的查询接口
"""

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional

# 导入 v1.0 的 language_styles（向后兼容）
try:
    from config.language_styles import LANGUAGE_STYLES
except ImportError:
    LANGUAGE_STYLES = {}
    logging.warning("无法导入 config.language_styles，将只使用新 Prompt 模板")

logger = logging.getLogger(__name__)


class PromptRegistry:
    """
    Prompt 中央注册表
    
    功能：
    - 加载 v1.0 的 LANGUAGE_STYLES 作为基础 Prompt
    - 动态扫描 prompts/ 目录，加载新的 Prompt 模板
    - 提供统一的查询接口
    - 支持多语言 Prompt
    
    使用示例：
        registry = get_prompt_registry()
        
        # 获取系统角色 Prompt
        analyst_prompt = registry.get("system", "analyst", language="中文")
        
        # 获取任务 Prompt
        task_prompt = registry.get("tasks", "understanding", language="中文")
        
        # 列出某个类别的所有 Prompt
        available_tasks = registry.list_category("tasks")
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        初始化 Prompt Registry
        
        Args:
            prompts_dir: Prompt 模板目录，默认为当前文件所在的 prompts/ 目录
        """
        self.prompts_dir = prompts_dir or Path(__file__).parent
        
        # 存储结构: {category: {name: prompt_text}}
        self.prompts: Dict[str, Dict[str, str]] = {
            "system": {},
            "tasks": {},
            "tools": {},
            "skills": {},
            "preferences": {}
        }
        
        # 加载顺序：先加载 v1.0，再加载新模板（新模板可以覆盖旧的）
        self._load_legacy_prompts()
        self._load_new_prompts()
        
        logger.info(f"PromptRegistry initialized with {self._count_prompts()} prompts")
    
    def _load_legacy_prompts(self):
        """
        加载 v1.0 的 LANGUAGE_STYLES
        
        将 v1.0 的 Prompt 映射到新的结构：
        - LANGUAGE_STYLES[lang]["system_base"] → prompts["system"][f"base_{lang}"]
        - LANGUAGE_STYLES[lang]["medical_disclaimer"] → prompts["system"][f"medical_disclaimer_{lang}"]
        - LANGUAGE_STYLES[lang]["legal_disclaimer"] → prompts["system"][f"legal_disclaimer_{lang}"]
        """
        if not LANGUAGE_STYLES:
            logger.warning("LANGUAGE_STYLES is empty, skipping legacy prompt loading")
            return
        
        for lang, styles in LANGUAGE_STYLES.items():
            # 系统基础 Prompt
            if "system_base" in styles:
                key = f"base_{lang}"
                self.prompts["system"][key] = styles["system_base"]
                logger.debug(f"Loaded legacy prompt: system/{key}")
            
            # 免责声明
            if "medical_disclaimer" in styles:
                key = f"medical_disclaimer_{lang}"
                self.prompts["system"][key] = styles["medical_disclaimer"]
                logger.debug(f"Loaded legacy prompt: system/{key}")
            
            if "legal_disclaimer" in styles:
                key = f"legal_disclaimer_{lang}"
                self.prompts["system"][key] = styles["legal_disclaimer"]
                logger.debug(f"Loaded legacy prompt: system/{key}")
        
        logger.info(f"Loaded {len(LANGUAGE_STYLES)} legacy language styles from v1.0")
    
    def _load_new_prompts(self):
        """
        从 prompts/ 子目录动态加载新 Prompt 模板
        
        扫描目录结构：
        prompts/
          ├── system/
          │   ├── analyst.py  (包含 ANALYST_中文, ANALYST_ENGLISH 等变量)
          │   └── coder.py
          ├── tasks/
          │   └── understanding.py
          ...
        
        约定：
        - 每个 .py 文件包含大写的 Prompt 变量
        - 变量名格式：NAME 或 NAME_LANGUAGE (如 ANALYST_中文)
        """
        categories = ["system", "tasks", "tools", "skills", "preferences"]
        
        for category in categories:
            category_dir = self.prompts_dir / category
            
            if not category_dir.exists() or not category_dir.is_dir():
                logger.debug(f"Category directory not found: {category_dir}")
                continue
            
            # 扫描目录下的所有 .py 文件
            for prompt_file in category_dir.glob("*.py"):
                if prompt_file.name.startswith("_"):
                    continue  # 跳过 __init__.py 等
                
                try:
                    self._load_prompt_file(category, prompt_file)
                except Exception as e:
                    logger.error(f"Failed to load {prompt_file}: {e}")
    
    def _load_prompt_file(self, category: str, prompt_file: Path):
        """
        加载单个 Prompt 文件
        
        Args:
            category: 类别名称 (system, tasks, etc.)
            prompt_file: Prompt 文件路径
        """
        module_name = prompt_file.stem  # 文件名（不含扩展名）
        
        # 动态导入模块
        try:
            # 构建模块路径：prompts.system.analyst
            module_path = f"prompts.{category}.{module_name}"
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.warning(f"Cannot import {module_path}: {e}")
            return
        
        # 提取所有大写变量（视为 Prompt 模板）
        loaded_count = 0
        for attr_name in dir(module):
            if not attr_name.isupper():
                continue  # 只处理大写变量
            
            prompt_content = getattr(module, attr_name)
            if not isinstance(prompt_content, str):
                continue  # 只处理字符串
            
            # 存储：将大写转为小写作为 key
            key = attr_name.lower()
            self.prompts[category][key] = prompt_content
            loaded_count += 1
            logger.debug(f"Loaded prompt: {category}/{key}")
        
        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} prompts from {category}/{module_name}.py")
    
    def get(
        self,
        category: str,
        name: str,
        language: str = "中文",
        default: Optional[str] = None
    ) -> str:
        """
        获取 Prompt 模板
        
        查找策略（按优先级）：
        1. 查找 {name}_{language} (如 "analyst_中文")
        2. 查找 {name} (通用模板)
        3. 如果是 system/base，回退到 v1.0 的 system_base
        4. 返回 default
        
        Args:
            category: 类别 (system, tasks, tools, skills, preferences)
            name: Prompt 名称
            language: 语言 (中文, English, 日本語)
            default: 默认值（如果找不到）
        
        Returns:
            Prompt 文本
        
        Raises:
            ValueError: 如果找不到且没有提供 default
        
        Examples:
            # 获取分析师角色 Prompt（中文版）
            prompt = registry.get("system", "analyst", language="中文")
            
            # 获取理解任务 Prompt
            prompt = registry.get("tasks", "understanding")
            
            # 提供默认值
            prompt = registry.get("system", "unknown", default="Default prompt")
        """
        if category not in self.prompts:
            if default is not None:
                return default
            raise ValueError(f"Unknown category: {category}")
        
        category_prompts = self.prompts[category]
        
        # 策略 1: 查找 name_language
        language_key = f"{name}_{language}"
        if language_key in category_prompts:
            return category_prompts[language_key]
        
        # 策略 2: 查找 name（通用模板）
        if name in category_prompts:
            return category_prompts[name]
        
        # 策略 3: 特殊处理 - 回退到 v1.0 的 system_base
        if category == "system" and name == "base":
            legacy_key = f"base_{language}"
            if legacy_key in category_prompts:
                return category_prompts[legacy_key]
        
        # 策略 4: 返回 default 或抛出异常
        if default is not None:
            return default
        
        raise ValueError(
            f"Prompt not found: {category}/{name} (language={language}). "
            f"Available: {list(category_prompts.keys())}"
        )
    
    def list_category(self, category: str) -> List[str]:
        """
        列出某个类别的所有 Prompt 名称
        
        Args:
            category: 类别名称
        
        Returns:
            Prompt 名称列表
        
        Examples:
            >>> registry.list_category("system")
            ['base_中文', 'base_english', 'analyst_中文', 'coder_中文']
        """
        return list(self.prompts.get(category, {}).keys())
    
    def has_prompt(self, category: str, name: str, language: str = "中文") -> bool:
        """
        检查 Prompt 是否存在
        
        Args:
            category: 类别
            name: 名称
            language: 语言
        
        Returns:
            是否存在
        """
        try:
            self.get(category, name, language=language)
            return True
        except ValueError:
            return False
    
    def _count_prompts(self) -> int:
        """统计 Prompt 总数"""
        return sum(len(prompts) for prompts in self.prompts.values())
    
    def get_all_categories(self) -> List[str]:
        """获取所有类别名称"""
        return list(self.prompts.keys())
    
    def print_summary(self):
        """打印 Registry 摘要信息（用于调试）"""
        print(f"\n{'='*60}")
        print("Prompt Registry Summary")
        print(f"{'='*60}")
        for category in self.get_all_categories():
            prompts = self.prompts[category]
            print(f"\n{category.upper()} ({len(prompts)} prompts):")
            for name in sorted(prompts.keys()):
                preview = prompts[name][:60].replace('\n', ' ')
                print(f"  - {name}: {preview}...")
        print(f"\n{'='*60}")
        print(f"Total: {self._count_prompts()} prompts")
        print(f"{'='*60}\n")


# 全局单例
_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """
    获取全局 Prompt Registry 单例
    
    Returns:
        PromptRegistry 实例
    
    Examples:
        >>> registry = get_prompt_registry()
        >>> prompt = registry.get("system", "analyst")
    """
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry


def reset_prompt_registry():
    """重置全局 Registry（主要用于测试）"""
    global _registry
    _registry = None


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    registry = get_prompt_registry()
    registry.print_summary()
    
    # 测试获取 v1.0 的 Prompt
    try:
        base_prompt = registry.get("system", "base", language="中文")
        print("\n✅ 成功获取 v1.0 的 system_base:")
        print(base_prompt[:100] + "...\n")
    except Exception as e:
        print(f"\n❌ 获取失败: {e}\n")
