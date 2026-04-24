# -*- coding: utf-8 -*-
"""
BoundaryChecker - 边界检查器

- 解析 .blueclaw/boundaries.yaml
- 文件范围检查（允许/禁止修改的文件模式）
- API 兼容性检查（函数签名变化检测）
- 依赖规则检查（循环依赖检测）
- 安全检查（敏感文件保护）
"""
import os
import re
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from blueclaw.adapter.ide.models import (
    CodebaseAnalysis, BoundaryRule, BoundaryCheckResult,
    ModificationPlan, FileDiff, CodeSymbol,
)


DEFAULT_SENSITIVE_FILES = {
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    ".aws/credentials", ".ssh/config",
    "secrets.yaml", "secrets.yml", "secrets.json",
    "passwords.txt", "token.txt",
}


class BoundaryChecker:
    """边界检查器"""

    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self.rules: List[BoundaryRule] = []
        self._load_config()

    def _load_config(self) -> None:
        """加载 .blueclaw/boundaries.yaml"""
        config_path = os.path.join(self.project_path, ".blueclaw", "boundaries.yaml")
        if not os.path.exists(config_path):
            # 使用默认规则：允许所有非敏感文件
            self.rules = [
                BoundaryRule(rule_type="deny", pattern="**/.env*", description="Environment files"),
                BoundaryRule(rule_type="deny", pattern="**/secrets.*", description="Secret files"),
                BoundaryRule(rule_type="deny", pattern="**/.ssh/**", description="SSH config"),
                BoundaryRule(rule_type="deny", pattern="**/.aws/**", description="AWS credentials"),
                BoundaryRule(rule_type="allow", pattern="**/*", description="Allow all other files"),
            ]
            return

        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for item in data.get("rules", []):
                self.rules.append(BoundaryRule(
                    rule_type=item.get("type", "allow"),
                    pattern=item.get("pattern", "**/*"),
                    description=item.get("description", ""),
                ))
        except Exception:
            # yaml 解析失败回退到默认规则
            self.rules = [BoundaryRule(rule_type="allow", pattern="**/*")]

    def check_modification_plan(
        self,
        plan: ModificationPlan,
        analysis: CodebaseAnalysis,
        diffs: Optional[List[FileDiff]] = None,
    ) -> BoundaryCheckResult:
        """检查修改计划是否符合边界约束"""
        violations: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {
            "files_checked": [],
            "api_changes": [],
            "circular_deps": [],
        }

        # 1. 文件范围检查
        for task in plan.tasks:
            file_ok, msg = self._check_file_allowed(task.file_path)
            details["files_checked"].append({
                "file": task.file_path,
                "allowed": file_ok,
                "message": msg,
            })
            if not file_ok:
                violations.append(f"File boundary violation: {task.file_path} - {msg}")

        # 2. API 兼容性检查
        if diffs:
            api_changes = self._check_api_compatibility(diffs, analysis)
            details["api_changes"] = api_changes
            for change in api_changes:
                if change.get("breaking"):
                    violations.append(
                        f"API compatibility violation: {change['file']} - {change['message']}"
                    )
                else:
                    warnings.append(
                        f"API change: {change['file']} - {change['message']}"
                    )

        # 3. 循环依赖检查
        circular = self._detect_circular_dependencies(analysis)
        details["circular_deps"] = circular
        if circular:
            for cycle in circular:
                warnings.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        # 4. 敏感文件检查
        for task in plan.tasks:
            basename = os.path.basename(task.file_path)
            if basename in DEFAULT_SENSITIVE_FILES:
                violations.append(f"Sensitive file protection: {task.file_path} cannot be modified")

        return BoundaryCheckResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            details=details,
        )

    def _check_file_allowed(self, file_path: str) -> tuple:
        """检查文件是否允许修改。返回 (allowed, message)"""
        # 从最后一条匹配的规则决定
        allowed = True
        matched_rule = None

        for rule in self.rules:
            if fnmatch.fnmatch(file_path, rule.pattern) or fnmatch.fnmatch(
                os.path.basename(file_path), rule.pattern
            ):
                matched_rule = rule
                allowed = (rule.rule_type == "allow")

        if matched_rule is None:
            # 默认拒绝（无规则匹配时保守策略）
            return False, "No matching boundary rule (default deny)"

        msg = matched_rule.description or f"Rule: {matched_rule.rule_type} {matched_rule.pattern}"
        return allowed, msg

    def _check_api_compatibility(
        self, diffs: List[FileDiff], analysis: CodebaseAnalysis
    ) -> List[Dict[str, Any]]:
        """检查 API 兼容性（简化：检测函数签名删除）"""
        changes: List[Dict[str, Any]] = []
        symbol_map = {f.path: f.symbols for f in analysis.files}

        for diff in diffs:
            # 统计删除行中是否包含函数/类定义
            deletions = [l for l in diff.hunks for l in l.lines if l.startswith("-")]
            for line in deletions:
                # 简单检测：删除行包含 def/class 可能破坏 API
                if re.search(r"^\s*(def|class)\s+\w+", line.lstrip("-")):
                    changes.append({
                        "file": diff.file_path,
                        "type": "removal",
                        "breaking": True,
                        "message": f"Removed symbol in {line.strip()[:60]}",
                    })
                # 检测参数变化
                if "def " in line and "(" in line:
                    changes.append({
                        "file": diff.file_path,
                        "type": "signature_change",
                        "breaking": True,
                        "message": f"Function signature changed in {line.strip()[:60]}",
                    })

        return changes

    def _detect_circular_dependencies(self, analysis: CodebaseAnalysis) -> List[List[str]]:
        """检测循环依赖"""
        graph: Dict[str, Set[str]] = defaultdict(set)
        all_files = {f.path for f in analysis.files}

        for dep in analysis.dependencies:
            if dep.source in all_files:
                # 尝试将 target 映射到文件路径
                target_file = self._resolve_import_to_file(dep.target, all_files)
                if target_file and target_file != dep.source:
                    graph[dep.source].add(target_file)

        # DFS 找环
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    # 发现环
                    cycle_start = path.index(neighbor) if neighbor in path else len(path)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle and cycle not in cycles:
                        cycles.append(cycle)
            rec_stack.remove(node)

        for node in list(all_files):
            if node not in visited:
                dfs(node, [node])

        return cycles

    def _resolve_import_to_file(self, import_name: str, all_files: Set[str]) -> Optional[str]:
        """将 import 模块名解析为文件路径（简化匹配）"""
        # 直接匹配
        if import_name in all_files:
            return import_name

        # 尝试 basename 匹配
        for f in all_files:
            basename = os.path.basename(f)
            name_no_ext = basename.rsplit(".", 1)[0]
            if name_no_ext == import_name:
                return f

        # 尝试路径包含匹配
        parts = import_name.replace(".", "/")
        for f in all_files:
            if parts in f.replace("\\", "/"):
                return f

        return None
