# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.ide.boundary import BoundaryChecker
from blueclaw.adapter.ide.models import (
    ModificationPlan, ModificationTask, CodebaseAnalysis, FileAnalysis,
    DependencyEdge, FileDiff, DiffHunk,
)


@pytest.fixture
def sample_project():
    path = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(path, "src", "auth"))
        with open(os.path.join(path, "src", "auth", "login.py"), "w") as f:
            f.write("def login(): pass\n")
        with open(os.path.join(path, ".env"), "w") as f:
            f.write("SECRET=xyz\n")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_analysis(sample_project):
    return CodebaseAnalysis(
        project_path=sample_project,
        files=[
            FileAnalysis(path="src/auth/login.py", language="python", imports=[]),
        ],
        dependencies=[],
    )


@pytest.fixture
def sample_plan():
    return ModificationPlan(
        blueprint_id="bp-1",
        tasks=[
            ModificationTask(task_id="s1", file_path="src/auth/login.py", description="Edit login"),
        ],
    )


def test_boundary_default_rules_allow_normal_file(sample_project, sample_analysis, sample_plan):
    checker = BoundaryChecker(sample_project)
    result = checker.check_modification_plan(sample_plan, sample_analysis)
    assert result.allowed is True
    assert len(result.violations) == 0


def test_boundary_blocks_sensitive_file(sample_project, sample_analysis):
    checker = BoundaryChecker(sample_project)
    plan = ModificationPlan(
        blueprint_id="bp-1",
        tasks=[
            ModificationTask(task_id="s1", file_path=".env", description="Edit env"),
        ],
    )
    result = checker.check_modification_plan(plan, sample_analysis)
    assert result.allowed is False
    assert any("Sensitive file" in v for v in result.violations)


def test_boundary_custom_config_allow(sample_project, sample_analysis):
    os.makedirs(os.path.join(sample_project, ".blueclaw"))
    with open(os.path.join(sample_project, ".blueclaw", "boundaries.yaml"), "w") as f:
        f.write("rules:\n  - type: allow\n    pattern: 'src/**/*.py'\n    description: Allow Python source\n  - type: deny\n    pattern: '**/*.env'\n    description: Deny env files\n")
    checker = BoundaryChecker(sample_project)
    plan = ModificationPlan(
        blueprint_id="bp-1",
        tasks=[
            ModificationTask(task_id="s1", file_path="src/auth/login.py", description="Edit login"),
        ],
    )
    result = checker.check_modification_plan(plan, sample_analysis)
    assert result.allowed is True


def test_boundary_custom_config_deny(sample_project, sample_analysis):
    os.makedirs(os.path.join(sample_project, ".blueclaw"))
    with open(os.path.join(sample_project, ".blueclaw", "boundaries.yaml"), "w") as f:
        f.write("rules:\n  - type: deny\n    pattern: 'src/**/*.py'\n    description: Deny all python\n")
    checker = BoundaryChecker(sample_project)
    plan = ModificationPlan(
        blueprint_id="bp-1",
        tasks=[
            ModificationTask(task_id="s1", file_path="src/auth/login.py", description="Edit login"),
        ],
    )
    result = checker.check_modification_plan(plan, sample_analysis)
    assert result.allowed is False
    assert any("boundary violation" in v.lower() for v in result.violations)


def test_boundary_api_compatibility_removal(sample_project, sample_analysis):
    checker = BoundaryChecker(sample_project)
    plan = ModificationPlan(
        blueprint_id="bp-1",
        tasks=[
            ModificationTask(task_id="s1", file_path="src/auth/login.py", description="Edit login"),
        ],
    )
    diff = FileDiff(
        file_path="src/auth/login.py",
        hunks=[DiffHunk(
            old_start=1, old_lines=1, new_start=1, new_lines=0,
            lines=["- def login(): pass"],
        )],
        additions=0,
        deletions=1,
    )
    result = checker.check_modification_plan(plan, sample_analysis, diffs=[diff])
    assert len(result.violations) > 0
    assert any("API compatibility" in v for v in result.violations)


def test_boundary_circular_dependency_detection(sample_project):
    analysis = CodebaseAnalysis(
        project_path=sample_project,
        files=[
            FileAnalysis(path="a.py", language="python", imports=["b"]),
            FileAnalysis(path="b.py", language="python", imports=["c"]),
            FileAnalysis(path="c.py", language="python", imports=["a"]),
        ],
        dependencies=[
            DependencyEdge(source="a.py", target="b", edge_type="import"),
            DependencyEdge(source="b.py", target="c", edge_type="import"),
            DependencyEdge(source="c.py", target="a", edge_type="import"),
        ],
    )
    checker = BoundaryChecker(sample_project)
    plan = ModificationPlan(blueprint_id="bp-1", tasks=[])
    result = checker.check_modification_plan(plan, analysis)
    assert len(result.warnings) > 0
    assert any("Circular dependency" in w for w in result.warnings)


def test_boundary_no_violations_for_safe_change(sample_project, sample_analysis):
    checker = BoundaryChecker(sample_project)
    plan = ModificationPlan(
        blueprint_id="bp-1",
        tasks=[
            ModificationTask(task_id="s1", file_path="src/auth/login.py", description="Add logging"),
        ],
    )
    diff = FileDiff(
        file_path="src/auth/login.py",
        hunks=[DiffHunk(
            old_start=1, old_lines=1, new_start=1, new_lines=2,
            lines=["  def login():", "+     print('log')", "      pass"],
        )],
        additions=1,
        deletions=0,
    )
    result = checker.check_modification_plan(plan, sample_analysis, diffs=[diff])
    assert result.allowed is True
    # 添加操作不应触发 API breaking
    assert not any("API compatibility" in v for v in result.violations)
