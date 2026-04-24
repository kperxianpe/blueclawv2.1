# -*- coding: utf-8 -*-
"""
E2E 混合场景测试

- Web 抓取 + IDE 数据处理的混合流程
- 模拟跨 Adapter 协作
"""
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.models import (
    ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription,
)
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.codemodel import MockCodeModelClient
from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.models import SandboxConfig


@pytest.fixture
def mixed_project():
    """创建混合项目：Web 数据抓取脚本 + 数据处理模块"""
    path = tempfile.mkdtemp()
    try:
        # Web 抓取脚本
        with open(os.path.join(path, "scraper.py"), "w") as f:
            f.write('''"""Price scraper module."""

import json

def fetch_prices(url):
    """Fetch prices from e-commerce site."""
    # TODO: implement real scraping
    return []

def save_to_csv(data, path):
    """Save price data to CSV."""
    import csv
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["product", "price"])
        for item in data:
            writer.writerow([item["name"], item["price"]])
''')
        # 数据分析模块
        with open(os.path.join(path, "analyzer.py"), "w") as f:
            f.write('''"""Price analysis module."""

def average_price(prices):
    """Calculate average price."""
    if not prices:
        return 0
    return sum(prices) / len(prices)

def price_trend(prices):
    """Detect price trend."""
    if len(prices) < 2:
        return "stable"
    if prices[-1] > prices[0]:
        return "up"
    return "down"
''')
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_mixed_web_ide_blueprint_structure():
    """验证混合蓝图的步骤结构"""
    blueprint = ExecutionBlueprint(
        task_id="e2e_monitoring",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="fetch_jd",
                name="Fetch JD prices",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic="https://jd.com")),
            ),
            ExecutionStep(
                step_id="fetch_taobao",
                name="Fetch Taobao prices",
                action=ActionDefinition(type="navigate", target=TargetDescription(semantic="https://taobao.com")),
            ),
            ExecutionStep(
                step_id="process_data",
                name="Process and analyze prices",
                action=ActionDefinition(
                    type="execute_command",
                    target=TargetDescription(semantic="analyzer.py"),
                    params={"command": "python analyzer.py"},
                ),
                dependencies=["fetch_jd", "fetch_taobao"],
            ),
        ],
    )

    assert len(blueprint.steps) == 3
    # 前两个步骤无依赖（可并行）
    assert blueprint.steps[0].dependencies == []
    assert blueprint.steps[1].dependencies == []
    # 第三个步骤依赖前两个
    assert "fetch_jd" in blueprint.steps[2].dependencies
    assert "fetch_taobao" in blueprint.steps[2].dependencies


@pytest.mark.asyncio
async def test_mixed_ide_data_processing(mixed_project):
    """模拟：抓取数据后 IDE 生成处理代码"""
    analyzer = CodebaseAnalyzer(mixed_project)
    analysis = analyzer.analyze()

    assert analysis.total_files == 2

    # Mock LLM 给 scraper 添加错误处理
    diff_text = '''diff --git a/scraper.py b/scraper.py
--- a/scraper.py
+++ b/scraper.py
@@ -3,4 +3,6 @@
 def fetch_prices(url):
     """Fetch prices from e-commerce site."""
+    if not url:
+        raise ValueError("URL cannot be empty")
     # TODO: implement real scraping
     return []
'''
    code_model = MockCodeModelClient(response_template=diff_text)
    response = await code_model.generate_code_changes(
        task_description="Add input validation to fetch_prices",
        file_context={"scraper.py": open(os.path.join(mixed_project, "scraper.py")).read()},
    )

    sandbox = SandboxValidator(mixed_project, config=SandboxConfig(check_tests=False))
    validation = await sandbox.validate(response.diffs)

    assert validation.success is True

    applier = IncrementApplier(mixed_project)
    result = applier.apply_diffs(response.diffs, auto_commit=False)
    assert result.success is True

    with open(os.path.join(mixed_project, "scraper.py"), "r") as f:
        content = f.read()
    assert "ValueError" in content


def test_mixed_cross_adapter_data_flow():
    """验证跨 Adapter 的数据流设计"""
    web_result = {"prices": [100, 200, 150]}

    # Web Adapter 输出 -> IDE Adapter 输入
    ide_blueprint = ExecutionBlueprint(
        task_id="analyze_prices",
        adapter_type="ide",
        steps=[
            ExecutionStep(
                step_id="generate_report",
                name="Generate price report",
                action=ActionDefinition(
                    type="edit_file",
                    target=TargetDescription(semantic="report.md"),
                    params={"data": web_result},
                ),
            ),
        ],
    )

    assert ide_blueprint.adapter_type == "ide"
    assert ide_blueprint.steps[0].action.params["data"] == web_result
