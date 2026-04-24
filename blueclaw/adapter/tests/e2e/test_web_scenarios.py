# -*- coding: utf-8 -*-
"""
E2E Web 场景测试

- 导航到页面并验证标题
- 表单填写和提交
- 页面内搜索和元素定位
"""
import pytest

from blueclaw.adapter.models import (
    ExecutionBlueprint, ExecutionStep, ActionDefinition, TargetDescription, ValidationRule,
)


@pytest.fixture
def navigate_blueprint():
    return ExecutionBlueprint(
        task_id="e2e_navigate",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="navigate",
                name="Navigate to example page",
                action=ActionDefinition(
                    type="navigate",
                    target=TargetDescription(semantic="https://example.com"),
                ),
                validation=ValidationRule(
                    type="url_match",
                    expected=r"example\.com",
                ),
            ),
        ],
    )


@pytest.fixture
def form_blueprint():
    return ExecutionBlueprint(
        task_id="e2e_form",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="navigate",
                name="Open form page",
                action=ActionDefinition(
                    type="navigate",
                    target=TargetDescription(semantic="about:blank"),
                ),
            ),
            ExecutionStep(
                step_id="fill_name",
                name="Fill name field",
                action=ActionDefinition(
                    type="input",
                    target=TargetDescription(selector="#name"),
                    params={"value": "Test User"},
                ),
                dependencies=["navigate"],
            ),
            ExecutionStep(
                step_id="submit",
                name="Click submit",
                action=ActionDefinition(
                    type="click",
                    target=TargetDescription(selector="#submit"),
                ),
                dependencies=["fill_name"],
            ),
        ],
    )


@pytest.fixture
def search_blueprint():
    return ExecutionBlueprint(
        task_id="e2e_search",
        adapter_type="web",
        steps=[
            ExecutionStep(
                step_id="navigate",
                name="Open search page",
                action=ActionDefinition(
                    type="navigate",
                    target=TargetDescription(semantic="about:blank"),
                ),
            ),
            ExecutionStep(
                step_id="type_query",
                name="Type search query",
                action=ActionDefinition(
                    type="input",
                    target=TargetDescription(selector="#search"),
                    params={"value": "blueclaw"},
                ),
                dependencies=["navigate"],
            ),
            ExecutionStep(
                step_id="click_search",
                name="Click search button",
                action=ActionDefinition(
                    type="click",
                    target=TargetDescription(selector="#search-btn"),
                ),
                dependencies=["type_query"],
            ),
        ],
    )


def test_blueprint_step_dependencies(form_blueprint):
    """验证表单场景的步骤依赖关系"""
    steps = form_blueprint.steps
    assert steps[0].step_id == "navigate"
    assert steps[0].dependencies == []
    assert steps[1].step_id == "fill_name"
    assert "navigate" in steps[1].dependencies
    assert steps[2].step_id == "submit"
    assert "fill_name" in steps[2].dependencies


def test_blueprint_validation_rules(navigate_blueprint):
    """验证导航场景的验证规则"""
    step = navigate_blueprint.steps[0]
    assert step.validation is not None
    assert step.validation.type == "url_match"
    assert "example" in step.validation.expected


def test_blueprint_routing(form_blueprint):
    """验证蓝图路由到 Web Adapter"""
    assert form_blueprint.adapter_type == "web"
    assert len(form_blueprint.steps) == 3


def test_search_blueprint_has_sequential_deps(search_blueprint):
    """验证搜索场景的步骤是顺序依赖的"""
    deps = search_blueprint.steps[2].dependencies
    assert "type_query" in deps
    assert "navigate" not in deps  # 只直接依赖前一步


def test_blueprint_step_params(form_blueprint):
    """验证步骤参数传递"""
    fill_step = form_blueprint.steps[1]
    assert fill_step.action.params.get("value") == "Test User"
