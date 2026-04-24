# -*- coding: utf-8 -*-
import pytest

from blueclaw.adapter.ide.codemodel import (
    MockCodeModelClient, KimiCodeClient, parse_unified_diff,
)
from blueclaw.adapter.ide.models import CodeModelResponse, FileDiff, DiffHunk


@pytest.mark.asyncio
async def test_mock_client_generates_diff():
    client = MockCodeModelClient()
    result = await client.generate_code_changes(
        task_description="Add logging",
        file_context={"main.py": "def main(): pass\n"},
    )
    assert result.success is True
    assert len(result.diffs) > 0
    assert result.diffs[0].file_path == "main.py"
    assert result.diffs[0].additions > 0


@pytest.mark.asyncio
async def test_mock_client_logs_calls():
    client = MockCodeModelClient()
    await client.generate_code_changes(
        task_description="Add logging",
        file_context={"main.py": "def main(): pass\n"},
        constraints=["Use print"],
    )
    assert len(client.call_log) == 1
    assert client.call_log[0]["task"] == "Add logging"
    assert client.call_log[0]["constraints"] == ["Use print"]


@pytest.mark.asyncio
async def test_mock_client_with_template():
    diff_text = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
 def main():
+    print("hello")
     pass
"""
    client = MockCodeModelClient(response_template=diff_text)
    result = await client.generate_code_changes(
        task_description="Add print",
        file_context={"main.py": "def main(): pass\n"},
    )
    assert result.success is True
    assert len(result.diffs) == 1
    assert result.diffs[0].file_path == "main.py"


@pytest.mark.asyncio
async def test_kimi_code_client_not_configured():
    client = KimiCodeClient(api_key=None)
    result = await client.generate_code_changes(
        task_description="Add logging",
        file_context={"main.py": "def main(): pass\n"},
    )
    assert result.success is False
    assert "not configured" in result.explanation.lower()


def test_parse_unified_diff_basic():
    diff_text = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
 def main():
+    print("hello")
     pass
"""
    diffs = parse_unified_diff(diff_text)
    assert len(diffs) == 1
    assert diffs[0].file_path == "main.py"
    assert len(diffs[0].hunks) == 1
    assert diffs[0].hunks[0].old_start == 1
    assert diffs[0].hunks[0].new_start == 1
    assert diffs[0].additions == 1


def test_parse_unified_diff_multiple_files():
    diff_text = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1,2 @@
+# comment
 pass

diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1 +1 @@
-old
+new
"""
    diffs = parse_unified_diff(diff_text)
    assert len(diffs) == 2
    assert diffs[0].file_path == "a.py"
    assert diffs[1].file_path == "b.py"


def test_parse_unified_diff_empty():
    diffs = parse_unified_diff("")
    assert diffs == []
