# -*- coding: utf-8 -*-
import pytest

from blueclaw.adapter.web.locator import WebLocator
from blueclaw.adapter.web.models import WebElement
from blueclaw.adapter.models import TargetDescription


def make_elements():
    return [
        WebElement(id="btn1", tag="button", text="Submit", selector="button#btn1", bbox={"x": 10, "y": 20, "width": 80, "height": 30}),
        WebElement(id="inp1", tag="input", placeholder="Search", selector="input#q", bbox={"x": 10, "y": 60, "width": 200, "height": 30}),
        WebElement(id="link1", tag="a", text="About us", selector="a.about", bbox={"x": 300, "y": 20, "width": 60, "height": 20}),
    ]


@pytest.mark.asyncio
async def test_locate_by_semantic_exact():
    locator = WebLocator()
    elems = make_elements()
    result = await locator.locate(TargetDescription(semantic="Submit"), elems)
    assert result.found is True
    assert result.strategy == "semantic"
    assert result.element.id == "btn1"


@pytest.mark.asyncio
async def test_locate_by_semantic_placeholder():
    locator = WebLocator()
    elems = make_elements()
    result = await locator.locate(TargetDescription(semantic="Search"), elems)
    assert result.found is True
    assert result.element.id == "inp1"


@pytest.mark.asyncio
async def test_locate_by_selector():
    locator = WebLocator()
    elems = make_elements()
    result = await locator.locate(TargetDescription(selector="a.about"), elems)
    assert result.found is True
    assert result.strategy == "selector"


@pytest.mark.asyncio
async def test_locate_by_coordinate():
    locator = WebLocator()
    elems = make_elements()
    result = await locator.locate(TargetDescription(coordinates={"x": 305, "y": 25}), elems)
    assert result.found is True
    assert result.strategy == "coordinate"
    assert result.element.id == "link1"


@pytest.mark.asyncio
async def test_locate_failure():
    locator = WebLocator()
    elems = make_elements()
    result = await locator.locate(TargetDescription(semantic="Nonexistent"), elems)
    assert result.found is False
    assert result.fallback_reason is not None
