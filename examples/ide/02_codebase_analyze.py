#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 02: Codebase Analysis

Demonstrates analyzing a project with CodebaseAnalyzer:
1. Create a mini project with Python files
2. Run analyzer to extract symbols, imports, dependencies
3. Print analysis summary

Run: python examples/ide/02_codebase_analyze.py
"""
import os
import tempfile

from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer


def main():
    tmpdir = tempfile.mkdtemp()
    print(f"[INFO] Analyzing: {tmpdir}")

    # Create sample files
    os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)

    with open(os.path.join(tmpdir, "src", "utils.py"), "w", encoding="utf-8") as f:
        f.write("""import json\n\ndef load_config(path):\n    with open(path) as f:\n        return json.load(f)\n""")

    with open(os.path.join(tmpdir, "src", "main.py"), "w", encoding="utf-8") as f:
        f.write("""from utils import load_config\n\ndef run():\n    cfg = load_config('config.json')\n    print(cfg)\n""")

    analyzer = CodebaseAnalyzer(project_path=tmpdir)
    analysis = analyzer.analyze(max_files=500)

    print(f"[RESULT] Total files: {analysis.total_files}")
    print(f"[RESULT] Total lines: {analysis.total_lines}")
    print(f"[RESULT] Languages: {analysis.languages}")
    print(f"[RESULT] Files analyzed:")
    for fa in analysis.files:
        symbols = ", ".join([s.name for s in fa.symbols[:5]])
        print(f"  - {fa.path} ({fa.language}): {len(fa.symbols)} symbols [{symbols}]")

    if analysis.dependencies:
        print(f"[RESULT] Dependencies:")
        for dep in analysis.dependencies:
            print(f"  {dep.source} -> {dep.target} ({dep.edge_type})")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 02 complete.")


if __name__ == "__main__":
    main()
