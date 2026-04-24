# -*- coding: utf-8 -*-
"""
CodeModelClient - 代码模型调用器

- Prompt 构造（任务描述 + 上下文 + 约束）
- 返回结果解析（diff 格式解析）
- 备选模型接口
- 调用日志和成本统计
"""
import re
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod

from blueclaw.adapter.ide.models import CodeModelResponse, FileDiff, DiffHunk


class BaseCodeModelClient(ABC):
    """代码模型客户端抽象基类"""

    @abstractmethod
    async def generate_code_changes(
        self,
        task_description: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]] = None,
    ) -> CodeModelResponse:
        """生成代码修改"""
        ...


class MockCodeModelClient(BaseCodeModelClient):
    """Mock 代码模型客户端（用于测试和演示）"""

    def __init__(self, response_template: Optional[str] = None):
        self.response_template = response_template
        self.call_log: List[Dict[str, Any]] = []

    async def generate_code_changes(
        self,
        task_description: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]] = None,
    ) -> CodeModelResponse:
        self.call_log.append({
            "task": task_description,
            "files": list(file_context.keys()),
            "constraints": constraints or [],
        })

        if self.response_template:
            diffs = self._parse_diff(self.response_template)
            return CodeModelResponse(
                success=True,
                diffs=diffs,
                explanation="Generated from mock template",
                tokens_used=100,
            )

        # 默认 mock 响应：在第一个文件末尾添加注释
        if file_context:
            first_file = list(file_context.keys())[0]
            content = file_context[first_file]
            lines = content.split("\n")
            hunks = [DiffHunk(
                old_start=len(lines),
                old_lines=0,
                new_start=len(lines) + 1,
                new_lines=2,
                lines=[
                    f"+ # Modified by CodeModel: {task_description[:50]}",
                    "+ # End of changes",
                ],
            )]
            return CodeModelResponse(
                success=True,
                diffs=[FileDiff(
                    file_path=first_file,
                    hunks=hunks,
                    additions=2,
                    deletions=0,
                )],
                explanation=f"Mock change applied to {first_file}",
                tokens_used=50,
            )

        return CodeModelResponse(
            success=False,
            explanation="No files provided",
            error="No file context",
        )

    def _parse_diff(self, diff_text: str) -> List[FileDiff]:
        """解析 unified diff 格式"""
        return parse_unified_diff(diff_text)


class KimiCodeClient(BaseCodeModelClient):
    """Kimi Code API 客户端（使用 OpenAI SDK 调用 Kimi/Moonshot API）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "moonshot-v1-8k",
    ):
        self.api_key = api_key
        self.base_url = base_url or "https://api.moonshot.cn/v1"
        self.model = model
        self.call_log: List[Dict[str, Any]] = []
        self.total_tokens_used = 0
        self._client = None

    def _get_client(self):
        """懒加载 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    async def generate_code_changes(
        self,
        task_description: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]] = None,
    ) -> CodeModelResponse:
        self.call_log.append({
            "task": task_description,
            "files": list(file_context.keys()),
            "constraints": constraints or [],
        })

        if not self.api_key or not self.api_key.strip():
            return CodeModelResponse(
                success=False,
                explanation="Kimi API key not configured",
                error="Missing KIMI_API_KEY",
                tokens_used=0,
            )

        prompt = self._build_prompt(task_description, file_context, constraints)

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior software engineer. Provide code changes in unified diff format only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
            )

            content = response.choices[0].message.content or ""
            usage = response.usage
            tokens_used = usage.total_tokens if usage else 0
            self.total_tokens_used += tokens_used

            # 去除 markdown 代码块标记
            content = self._strip_markdown(content)

            # 解析 diff
            diffs = parse_unified_diff(content)

            return CodeModelResponse(
                success=len(diffs) > 0,
                diffs=diffs,
                explanation=f"Generated {len(diffs)} file diff(s)" if diffs else "No diffs parsed",
                tokens_used=tokens_used,
                error=None if diffs else "Could not parse diffs from model response",
            )

        except Exception as e:
            return CodeModelResponse(
                success=False,
                explanation=f"API call failed: {e}",
                error=str(e),
                tokens_used=0,
            )

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """去除 markdown 代码块标记，提取其中的 diff 内容"""
        text = text.strip()
        # 去除开头的 ```diff 或 ```python 等
        if text.startswith("```"):
            # 找到第一个换行，跳过语言标识
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1:]
        # 去除结尾的 ```
        if text.endswith("```"):
            text = text[:-3].strip()
        return text

    def _build_prompt(
        self,
        task_description: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]],
    ) -> str:
        """构造 prompt"""
        lines = [
            "# Task",
            task_description,
            "",
            "# File Context",
        ]
        for path, content in file_context.items():
            lines.append(f"## {path}")
            lines.append("```python")
            lines.append(content[:5000])  # 截断避免过长
            lines.append("```")
            lines.append("")

        if constraints:
            lines.append("# Constraints")
            for c in constraints:
                lines.append(f"- {c}")
            lines.append("")

        lines.append("# Instructions")
        lines.append("Please provide the code changes in unified diff format.")
        lines.append("Only output the diff, no explanations.")
        lines.append("Example format:")
        lines.append("```")
        lines.append("diff --git a/file.py b/file.py")
        lines.append("--- a/file.py")
        lines.append("+++ b/file.py")
        lines.append("@@ -1,3 +1,5 @@")
        lines.append(" def foo():")
        lines.append("+    # new line")
        lines.append("     pass")
        lines.append("```")

        return "\n".join(lines)


def parse_unified_diff(diff_text: str) -> List[FileDiff]:
    """解析 unified diff 文本为结构化对象"""
    diffs: List[FileDiff] = []
    current_diff: Optional[FileDiff] = None
    current_hunk: Optional[DiffHunk] = None

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current_diff:
                if current_hunk:
                    current_diff.hunks.append(current_hunk)
                    current_hunk = None
                diffs.append(current_diff)
            # 解析文件路径
            parts = line.split()
            if len(parts) >= 4:
                old_path = parts[2][2:]  # a/path
                new_path = parts[3][2:]  # b/path
            else:
                old_path = new_path = ""
            current_diff = FileDiff(file_path=new_path, old_path=old_path)

        elif line.startswith("@@"):
            if current_hunk and current_diff:
                current_diff.hunks.append(current_hunk)
            # 解析 hunk 头: @@ -old_start,old_lines +new_start,new_lines @@
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if m:
                current_hunk = DiffHunk(
                    old_start=int(m.group(1)),
                    old_lines=int(m.group(2) or 1),
                    new_start=int(m.group(3)),
                    new_lines=int(m.group(4) or 1),
                )
            else:
                current_hunk = DiffHunk()

        elif current_hunk is not None:
            current_hunk.lines.append(line)
            if current_diff:
                if line.startswith("+") and not line.startswith("+++"):
                    current_diff.additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    current_diff.deletions += 1

    if current_diff:
        if current_hunk:
            current_diff.hunks.append(current_hunk)
        diffs.append(current_diff)

    return diffs
