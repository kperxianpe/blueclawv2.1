#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 03: Boundary Check

Demonstrates protecting files from modification:
1. Set up allow/deny/protected rules
2. Check a list of candidate files
3. Review violations and warnings

Run: python examples/ide/03_boundary_check.py
"""
from blueclaw.adapter.ide.boundary import BoundaryChecker, BoundaryRule


def main():
    rules = [
        BoundaryRule(rule_type="allow", pattern="src/**/*.py", description="Main source"),
        BoundaryRule(rule_type="deny", pattern="**/node_modules/**", description="Dependencies"),
        BoundaryRule(rule_type="deny", pattern="**/__pycache__/**", description="Cache"),
        BoundaryRule(rule_type="protected", pattern="**/*.secret", description="Secrets"),
        BoundaryRule(rule_type="protected", pattern="**/*.key", description="Keys"),
    ]

    checker = BoundaryChecker(rules)

    candidates = [
        "src/main.py",
        "src/utils.py",
        "tests/test_main.py",
        "config.secret",
        "deploy.key",
        "node_modules/lodash/index.js",
        "__pycache__/main.cpython-312.pyc",
    ]

    print(f"[INFO] Checking {len(candidates)} files against {len(rules)} rules")
    result = checker.check(candidates)

    print(f"[RESULT] Allowed: {result.allowed}")
    if result.violations:
        print(f"[RESULT] Violations ({len(result.violations)}):")
        for v in result.violations:
            print(f"  - {v}")
    if result.warnings:
        print(f"[RESULT] Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  - {w}")

    print("[DONE] Example 03 complete.")


if __name__ == "__main__":
    main()
