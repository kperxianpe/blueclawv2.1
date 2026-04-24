# -*- coding: utf-8 -*-
"""
CodebaseAnalyzer - 代码库分析器

支持语言：Python, JavaScript, TypeScript, Java
- AST 解析（Tree-sitter）
- 依赖图提取
- 模块边界识别
- 接口定义提取
"""
import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from blueclaw.adapter.ide.models import (
    CodebaseAnalysis, FileAnalysis, CodeSymbol, DependencyEdge,
)


# 语言检测映射
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
}

# 忽略的文件/目录
DEFAULT_IGNORE_PATTERNS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv",
    "dist", "build", "target", ".pytest_cache", "__pycache__",
}


class CodebaseAnalyzer:
    """代码库分析器"""

    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self._tree_sitter_parsers: Dict[str, Any] = {}

    def _get_parser(self, language: str) -> Optional[Any]:
        """懒加载 Tree-sitter parser"""
        if language in self._tree_sitter_parsers:
            return self._tree_sitter_parsers[language]

        try:
            from tree_sitter import Language, Parser
            lang_module = None
            if language == "python":
                from tree_sitter_python import language as py_lang
                lang_module = py_lang
            elif language == "javascript":
                from tree_sitter_javascript import language as js_lang
                lang_module = js_lang
            elif language == "typescript":
                from tree_sitter_typescript import language as ts_lang
                lang_module = ts_lang
            elif language == "java":
                from tree_sitter_java import language as java_lang
                lang_module = java_lang

            if lang_module:
                parser = Parser(Language(lang_module()))
                self._tree_sitter_parsers[language] = parser
                return parser
        except Exception:
            pass
        return None

    def analyze(self, max_files: int = 500) -> CodebaseAnalysis:
        """分析整个代码库"""
        files: List[FileAnalysis] = []
        dependencies: List[DependencyEdge] = []
        languages: Dict[str, int] = {}
        total_lines = 0

        for file_path in self._scan_files(max_files):
            rel_path = os.path.relpath(file_path, self.project_path)
            ext = os.path.splitext(file_path)[1].lower()
            language = LANGUAGE_MAP.get(ext, "unknown")

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
            except Exception:
                continue

            line_count = source.count("\n") + 1
            total_lines += line_count
            languages[language] = languages.get(language, 0) + 1

            file_analysis = self._analyze_file(rel_path, language, source)
            file_analysis.line_count = line_count
            files.append(file_analysis)

            # 提取依赖边
            for imp in file_analysis.imports:
                dependencies.append(DependencyEdge(
                    source=rel_path,
                    target=imp,
                    edge_type="import",
                ))

        return CodebaseAnalysis(
            project_path=self.project_path,
            files=files,
            dependencies=dependencies,
            languages=languages,
            total_files=len(files),
            total_lines=total_lines,
        )

    def _scan_files(self, max_files: int) -> List[str]:
        """扫描项目文件"""
        result: List[str] = []
        for root, dirs, filenames in os.walk(self.project_path):
            # 过滤忽略目录
            dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_PATTERNS]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in LANGUAGE_MAP:
                    result.append(os.path.join(root, fname))
                    if len(result) >= max_files:
                        return result
        return result

    def _analyze_file(self, rel_path: str, language: str, source: str) -> FileAnalysis:
        """分析单个文件"""
        if language == "python":
            return self._analyze_python(rel_path, source)

        parser = self._get_parser(language)
        if parser:
            return self._analyze_with_tree_sitter(rel_path, language, source, parser)

        # fallback: regex-based extraction
        return self._analyze_with_regex(rel_path, language, source)

    def _analyze_python(self, rel_path: str, source: str) -> FileAnalysis:
        """使用内置 ast 模块分析 Python"""
        imports: List[str] = []
        symbols: List[CodeSymbol] = []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return FileAnalysis(path=rel_path, language="python")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
            elif isinstance(node, ast.FunctionDef):
                params = [a.arg for a in node.args.args]
                symbols.append(CodeSymbol(
                    name=node.name,
                    symbol_type="function",
                    line_start=getattr(node, 'lineno', 0),
                    line_end=getattr(node, 'end_lineno', 0),
                    signature=f"def {node.name}({', '.join(params)})",
                    parameters=params,
                ))
            elif isinstance(node, ast.ClassDef):
                symbols.append(CodeSymbol(
                    name=node.name,
                    symbol_type="class",
                    line_start=getattr(node, 'lineno', 0),
                    line_end=getattr(node, 'end_lineno', 0),
                ))

        return FileAnalysis(
            path=rel_path,
            language="python",
            imports=imports,
            symbols=symbols,
        )

    def _analyze_with_tree_sitter(
        self, rel_path: str, language: str, source: str, parser: Any
    ) -> FileAnalysis:
        """使用 Tree-sitter 分析"""
        imports: List[str] = []
        symbols: List[CodeSymbol] = []

        try:
            tree = parser.parse(source.encode("utf-8"))
            root = tree.root_node
        except Exception:
            return FileAnalysis(path=rel_path, language=language)

        def walk(node):
            if language in ("javascript", "typescript"):
                if node.type == "import_statement":
                    # import x from 'y'
                    text = source[node.start_byte:node.end_byte]
                    m = re.search(r"from\s+['\"]([^'\"]+)['\"]", text)
                    if m:
                        imports.append(m.group(1))
                elif node.type == "import":
                    text = source[node.start_byte:node.end_byte]
                    m = re.search(r"require\(['\"]([^'\"]+)['\"]\)", text)
                    if m:
                        imports.append(m.group(1))
                elif node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbols.append(CodeSymbol(
                            name=name_node.text.decode("utf-8"),
                            symbol_type="function",
                            line_start=name_node.start_point[0] + 1,
                        ))
                elif node.type == "class_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbols.append(CodeSymbol(
                            name=name_node.text.decode("utf-8"),
                            symbol_type="class",
                            line_start=name_node.start_point[0] + 1,
                        ))
            elif language == "java":
                if node.type == "import_declaration":
                    text = source[node.start_byte:node.end_byte]
                    m = re.search(r"import\s+([^;]+);", text)
                    if m:
                        imports.append(m.group(1).strip())
                elif node.type == "class_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbols.append(CodeSymbol(
                            name=name_node.text.decode("utf-8"),
                            symbol_type="class",
                            line_start=name_node.start_point[0] + 1,
                        ))
                elif node.type == "method_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbols.append(CodeSymbol(
                            name=name_node.text.decode("utf-8"),
                            symbol_type="function",
                            line_start=name_node.start_point[0] + 1,
                        ))

            for child in node.children:
                walk(child)

        walk(root)
        return FileAnalysis(
            path=rel_path,
            language=language,
            imports=imports,
            symbols=symbols,
        )

    def _analyze_with_regex(self, rel_path: str, language: str, source: str) -> FileAnalysis:
        """基于正则的轻量分析（fallback）"""
        imports: List[str] = []
        symbols: List[CodeSymbol] = []

        # 通用 import 正则
        for line in source.split("\n"):
            line = line.strip()
            if line.startswith("import "):
                parts = line.split()
                if len(parts) >= 2:
                    imports.append(parts[1].rstrip(";"))
            elif line.startswith("from ") and " import " in line:
                parts = line.split()
                imports.append(parts[1])
            elif line.startswith("def "):
                m = re.match(r"def\s+(\w+)", line)
                if m:
                    symbols.append(CodeSymbol(name=m.group(1), symbol_type="function"))
            elif line.startswith("class "):
                m = re.match(r"class\s+(\w+)", line)
                if m:
                    symbols.append(CodeSymbol(name=m.group(1), symbol_type="class"))

        return FileAnalysis(
            path=rel_path,
            language=language,
            imports=imports,
            symbols=symbols,
        )

    def find_dependents(self, analysis: CodebaseAnalysis, file_path: str) -> List[str]:
        """查找依赖于指定文件的文件列表（反向追踪）"""
        # 简化：通过模块名匹配
        result: Set[str] = set()
        module_name = file_path.replace("/", ".").replace("\\", ".")
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        for dep in analysis.dependencies:
            if dep.target == base_name or dep.target in module_name:
                result.add(dep.source)
        return sorted(result)

    def get_symbol_map(self, analysis: CodebaseAnalysis) -> Dict[str, List[CodeSymbol]]:
        """获取全局符号映射（文件路径 -> 符号列表）"""
        return {f.path: f.symbols for f in analysis.files}
