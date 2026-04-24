# -*- coding: utf-8 -*-
"""
IncrementApplier - 增量应用器

- 验证通过后应用到主代码库
- Git 操作封装（status/add/commit）
- 提交信息自动生成
- 冲突检测
- 回滚机制
"""
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from blueclaw.adapter.ide.models import (
    ApplyResult, GitStatus, FileDiff,
)


class IncrementApplier:
    """增量应用器"""

    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self._git_available = self._check_git()

    def _check_git(self) -> bool:
        """检查项目是否是 Git 仓库"""
        git_dir = os.path.join(self.project_path, ".git")
        return os.path.isdir(git_dir)

    def _git(self, args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """执行 git 命令"""
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd or self.project_path,
        )

    def apply_diffs(
        self,
        diffs: List[FileDiff],
        auto_commit: bool = True,
        commit_message: Optional[str] = None,
    ) -> ApplyResult:
        """应用 diff 到工作区，可选自动 commit"""
        if not self._git_available:
            return self._apply_without_git(diffs)

        # 1. 记录当前 HEAD（用于回滚）
        head_proc = self._git(["rev-parse", "HEAD"])
        pre_apply_head = head_proc.stdout.strip() if head_proc.returncode == 0 else ""

        # 2. 检查冲突
        status = self.get_git_status()
        if status.has_conflicts:
            return ApplyResult(
                success=False,
                error=f"Repository has merge conflicts: {status.modified_files}",
            )

        # 3. 应用每个 diff 到文件系统
        changed_files: List[str] = []
        for diff in diffs:
            file_path = os.path.join(self.project_path, diff.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            original_lines: List[str] = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    original_lines = f.read().splitlines()

            new_lines = self._apply_hunks(original_lines, diff.hunks)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
                if new_lines:
                    f.write("\n")
            changed_files.append(diff.file_path)

        # 4. Git add
        if changed_files:
            self._git(["add"] + changed_files)

        # 5. 自动 commit
        commit_hash = ""
        final_message = commit_message or self._generate_commit_message(diffs)
        if auto_commit and changed_files:
            commit_proc = self._git(["commit", "-m", final_message])
            if commit_proc.returncode != 0:
                return ApplyResult(
                    success=False,
                    files_changed=changed_files,
                    error=f"Git commit failed: {commit_proc.stderr}",
                    pre_apply_head=pre_apply_head,
                )
            # 获取 commit hash
            hash_proc = self._git(["rev-parse", "HEAD"])
            commit_hash = hash_proc.stdout.strip()

        return ApplyResult(
            success=True,
            committed=auto_commit and bool(changed_files),
            commit_hash=commit_hash,
            commit_message=final_message,
            files_changed=changed_files,
            rollback_available=bool(pre_apply_head),
            pre_apply_head=pre_apply_head,
        )

    def _apply_without_git(self, diffs: List[FileDiff]) -> ApplyResult:
        """在没有 Git 的情况下直接应用 diff"""
        changed_files: List[str] = []
        for diff in diffs:
            file_path = os.path.join(self.project_path, diff.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            original_lines: List[str] = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    original_lines = f.read().splitlines()
            new_lines = self._apply_hunks(original_lines, diff.hunks)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
                if new_lines:
                    f.write("\n")
            changed_files.append(diff.file_path)

        return ApplyResult(
            success=True,
            committed=False,
            commit_message="Applied without git",
            files_changed=changed_files,
            error="Warning: No git repository found, changes applied directly",
        )

    def _apply_hunks(self, original_lines: List[str], hunks: List[Any]) -> List[str]:
        """应用 diff hunks"""
        result = list(original_lines)
        for hunk in reversed(hunks):
            old_start = max(0, hunk.old_start - 1)
            new_lines_hunk: List[str] = []
            for line in hunk.lines:
                if line.startswith("+") and not line.startswith("+++"):
                    new_lines_hunk.append(line[1:])
                elif line.startswith("-") and not line.startswith("---"):
                    continue
                elif line.startswith(" "):
                    new_lines_hunk.append(line[1:])
                elif line.startswith("\\"):
                    continue
                else:
                    new_lines_hunk.append(line)
            result = result[:old_start] + new_lines_hunk + result[old_start + hunk.old_lines:]
        return result

    def get_git_status(self) -> GitStatus:
        """获取 Git 状态"""
        if not self._git_available:
            return GitStatus(branch="", is_clean=True)

        branch_proc = self._git(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else ""

        status_proc = self._git(["status", "--porcelain"])
        modified: List[str] = []
        untracked: List[str] = []
        has_conflicts = False

        if status_proc.returncode == 0:
            for line in status_proc.stdout.splitlines():
                if len(line) < 3:
                    continue
                code = line[:2]
                fpath = line[3:].strip()
                if "U" in code or code == "DD" or code == "AA":
                    has_conflicts = True
                if code.strip():  # 任何非空状态码
                    if code == "??":
                        untracked.append(fpath)
                    else:
                        modified.append(fpath)

        return GitStatus(
            branch=branch,
            is_clean=len(modified) == 0 and len(untracked) == 0,
            modified_files=modified,
            untracked_files=untracked,
            has_conflicts=has_conflicts,
        )

    def rollback(self, pre_apply_head: str) -> ApplyResult:
        """回滚到指定 HEAD"""
        if not self._git_available or not pre_apply_head:
            return ApplyResult(
                success=False,
                error="Rollback not available: no git or no pre-apply HEAD",
            )

        # 先 abort 任何 merge/rebase
        self._git(["merge", "--abort"])
        self._git(["rebase", "--abort"])

        reset_proc = self._git(["reset", "--hard", pre_apply_head])
        if reset_proc.returncode != 0:
            return ApplyResult(
                success=False,
                error=f"Rollback failed: {reset_proc.stderr}",
            )

        return ApplyResult(
            success=True,
            rollback_available=False,
            commit_message=f"Rolled back to {pre_apply_head[:8]}",
        )

    def revert_last_commit(self) -> ApplyResult:
        """Revert 最后一次 commit"""
        if not self._git_available:
            return ApplyResult(success=False, error="No git repository")

        revert_proc = self._git(["revert", "--no-edit", "HEAD"])
        if revert_proc.returncode != 0:
            return ApplyResult(
                success=False,
                error=f"Revert failed: {revert_proc.stderr}",
            )

        hash_proc = self._git(["rev-parse", "HEAD"])
        return ApplyResult(
            success=True,
            committed=True,
            commit_hash=hash_proc.stdout.strip(),
            commit_message="Reverted last commit",
        )

    def _generate_commit_message(self, diffs: List[FileDiff]) -> str:
        """自动生成提交信息"""
        files = [d.file_path for d in diffs]
        total_additions = sum(d.additions for d in diffs)
        total_deletions = sum(d.deletions for d in diffs)

        # 推断类型
        change_type = "refactor"
        if any("fix" in f.lower() or "bug" in f.lower() for f in files):
            change_type = "fix"
        elif any("test" in f.lower() for f in files):
            change_type = "test"
        elif any("feat" in f.lower() for f in files):
            change_type = "feat"

        # 主要文件（取第一个）
        scope = os.path.splitext(os.path.basename(files[0]))[0] if files else "project"

        lines = [
            f"{change_type}({scope}): automated code modification",
            "",
            f"- Files changed: {', '.join(files)}",
            f"- Additions: {total_additions}, Deletions: {total_deletions}",
            "",
            "Modified by BlueClaw IDE Adapter",
        ]
        return "\n".join(lines)
