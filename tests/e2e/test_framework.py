#!/usr/bin/env python3
"""Blueclaw v2.5 E2E Test Framework - Screenshot -> Analysis -> Fix -> Test loop"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

from playwright.async_api import Page


class Status(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    GAP = "gap"


@dataclass
class Checkpoint:
    name: str
    description: str
    screenshot_path: Optional[Path] = None
    status: Status = Status.PASS
    notes: str = ""


@dataclass
class Case:
    id: str
    module: str
    title: str
    description: str
    status: Status = Status.SKIP
    checkpoints: List[Checkpoint] = field(default_factory=list)
    gap_reason: str = ""
    fix_suggestion: str = ""
    duration_ms: int = 0


@dataclass
class Report:
    run_at: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    gaps: int = 0
    skipped: int = 0
    cases: List[Case] = field(default_factory=list)


class Framework:
    def __init__(self, page: Page, screenshot_dir: Path):
        self.page = page
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.current_case: Optional[Case] = None
        self.report = Report(run_at=datetime.now().isoformat())

    def start_case(self, case_id: str, module: str, title: str, description: str) -> Case:
        self.current_case = Case(id=case_id, module=module, title=title, description=description)
        self.report.cases.append(self.current_case)
        return self.current_case

    async def checkpoint(self, name: str, description: str, status: Status = Status.PASS, notes: str = "") -> Checkpoint:
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.current_case.id}_{name}_{timestamp}.png"
        path = self.screenshot_dir / filename
        await self.page.screenshot(path=str(path), full_page=False)

        cp = Checkpoint(name=name, description=description, screenshot_path=path, status=status, notes=notes)
        self.current_case.checkpoints.append(cp)
        return cp

    def mark_gap(self, reason: str, fix_suggestion: str = ""):
        self.current_case.status = Status.GAP
        self.current_case.gap_reason = reason
        self.current_case.fix_suggestion = fix_suggestion
        self.report.gaps += 1
        self.report.total += 1

    def mark_pass(self):
        self.current_case.status = Status.PASS
        self.report.passed += 1
        self.report.total += 1

    def mark_fail(self, reason: str = ""):
        self.current_case.status = Status.FAIL
        if reason:
            self.current_case.gap_reason = reason
        self.report.failed += 1
        self.report.total += 1
        raise AssertionError(reason or "Test marked as failed")
