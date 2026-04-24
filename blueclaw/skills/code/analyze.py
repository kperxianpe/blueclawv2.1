#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Analyze Skill

Analyze code quality, structure, and issues.
"""

from pathlib import Path
from typing import Optional, List, Dict
import ast
from ..base import Skill, SkillResult
from ..registry import SkillRegistry


@SkillRegistry.register
class CodeAnalyzeSkill(Skill):
    name = "code_analyze"
    description = "分析代码质量、结构和潜在问题"
    category = "code"
    
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "代码文件路径"
            },
            "code": {
                "type": "string",
                "description": "直接传入代码字符串（与path二选一）"
            },
            "language": {
                "type": "string",
                "enum": ["python", "javascript", "auto"],
                "default": "auto",
                "description": "代码语言"
            }
        },
        "required": []
    }
    
    capabilities = {
        "can_handle": ["Python代码", "JavaScript代码", "语法分析", "代码结构"],
        "cannot_handle": ["编译后代码", "加密代码"],
        "typical_use_cases": [
            "代码质量检查",
            "发现潜在问题",
            "代码结构分析",
            "提取函数定义"
        ]
    }
    
    examples = [
        {
            "description": "分析Python文件",
            "input": {"path": "app.py"},
            "output": "Functions: 5, Classes: 2, Issues: 1..."
        },
        {
            "description": "分析代码字符串",
            "input": {"code": "def test(): pass", "language": "python"},
            "output": "AST analysis result..."
        }
    ]
    
    async def execute(self, path: str = None, code: str = None,
                     language: str = "auto") -> SkillResult:
        # Get code content
        if code is not None:
            source = code
            source_path = "<inline>"
        elif path is not None:
            file_path = Path(path)
            if not file_path.exists():
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"文件不存在: {path}"
                )
            try:
                source = file_path.read_text(encoding='utf-8')
                source_path = str(file_path)
            except Exception as e:
                return SkillResult(
                    success=False,
                    output=None,
                    error_message=f"读取文件失败: {e}"
                )
        else:
            return SkillResult(
                success=False,
                output=None,
                error_message="必须提供 path 或 code 参数"
            )
        
        # Detect language
        if language == "auto":
            language = self._detect_language(source_path)
        
        # Analyze based on language
        if language == "python":
            return self._analyze_python(source, source_path)
        else:
            return self._analyze_generic(source, source_path, language)
    
    def _detect_language(self, path: str) -> str:
        """Detect language from file path"""
        ext = Path(path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'javascript',
            '.jsx': 'javascript',
            '.tsx': 'javascript',
        }
        return lang_map.get(ext, 'generic')
    
    def _analyze_python(self, source: str, path: str) -> SkillResult:
        """Analyze Python code using AST"""
        issues = []
        metrics = {
            "functions": 0,
            "classes": 0,
            "imports": 0,
            "lines": len(source.split('\n')),
            "docstrings": 0
        }
        
        try:
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics["functions"] += 1
                    # Check for docstring
                    if ast.get_docstring(node):
                        metrics["docstrings"] += 1
                    else:
                        issues.append({
                            "type": "missing_docstring",
                            "line": node.lineno,
                            "message": f"函数 '{node.name}' 缺少文档字符串"
                        })
                
                elif isinstance(node, ast.ClassDef):
                    metrics["classes"] += 1
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics["imports"] += 1
                
                elif isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        issues.append({
                            "type": "bare_except",
                            "line": node.lineno,
                            "message": "使用了裸 except 语句，建议捕获具体异常"
                        })
            
            return SkillResult(
                success=True,
                output={
                    "language": "python",
                    "metrics": metrics,
                    "issues": issues,
                    "summary": f"{metrics['functions']} functions, {metrics['classes']} classes, {len(issues)} issues"
                },
                metadata={
                    "path": path,
                    "ast_valid": True
                }
            )
            
        except SyntaxError as e:
            return SkillResult(
                success=True,  # Analysis succeeded even with syntax error
                output={
                    "language": "python",
                    "syntax_error": {
                        "line": e.lineno,
                        "message": str(e)
                    },
                    "summary": "Syntax error found"
                },
                suggestion="修复语法错误后重新分析"
            )
    
    def _analyze_generic(self, source: str, path: str, language: str) -> SkillResult:
        """Generic code analysis"""
        lines = source.split('\n')
        
        # Basic metrics
        metrics = {
            "lines": len(lines),
            "code_lines": len([l for l in lines if l.strip()]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')]),
            "blank_lines": len([l for l in lines if not l.strip()])
        }
        
        return SkillResult(
            success=True,
            output={
                "language": language,
                "metrics": metrics,
                "summary": f"{metrics['code_lines']} lines of code"
            },
            metadata={"path": path}
        )
