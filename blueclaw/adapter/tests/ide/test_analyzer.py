# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import pytest

from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.models import CodebaseAnalysis


@pytest.fixture
def sample_project():
    """创建一个示例项目目录"""
    path = tempfile.mkdtemp()
    try:
        # Python 文件
        os.makedirs(os.path.join(path, "src", "auth"))
        os.makedirs(os.path.join(path, "src", "utils"))
        with open(os.path.join(path, "src", "auth", "login.py"), "w") as f:
            f.write("""import logging\nfrom utils.logger import get_logger\n\ndef login(username, password):\n    logger = get_logger()\n    logger.info(f\"User {username} logging in\")\n    return True\n\nclass AuthService:\n    def authenticate(self, user, pwd):\n        return login(user, pwd)\n""")
        with open(os.path.join(path, "src", "utils", "logger.py"), "w") as f:
            f.write("""import os\n\ndef get_logger():\n    return Logger()\n\nclass Logger:\n    def info(self, msg):\n        print(msg)\n""")
        # JavaScript 文件
        os.makedirs(os.path.join(path, "frontend", "src"))
        with open(os.path.join(path, "frontend", "src", "app.js"), "w") as f:
            f.write("""import React from 'react';\nimport { LoginForm } from './components/LoginForm';\n\nfunction App() {\n    return <LoginForm />;\n}\n\nclass AppComponent extends React.Component {\n    render() {\n        return <div>App</div>;\n    }\n}\n""")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_analyzer_scans_files(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    assert result.total_files >= 3
    paths = [f.path for f in result.files]
    assert any("login.py" in p for p in paths)
    assert any("logger.py" in p for p in paths)
    assert any("app.js" in p for p in paths)


def test_analyzer_detects_languages(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    assert "python" in result.languages
    assert "javascript" in result.languages
    assert result.languages["python"] >= 2


def test_analyzer_extracts_imports_python(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    login_file = next((f for f in result.files if "login.py" in f.path), None)
    assert login_file is not None
    assert "logging" in login_file.imports
    assert "utils.logger" in login_file.imports or "get_logger" in str(login_file.imports)


def test_analyzer_extracts_symbols_python(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    login_file = next((f for f in result.files if "login.py" in f.path), None)
    assert login_file is not None
    names = {s.name for s in login_file.symbols}
    assert "login" in names
    assert "AuthService" in names


def test_analyzer_extracts_symbols_js(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    app_file = next((f for f in result.files if "app.js" in f.path), None)
    assert app_file is not None
    names = {s.name for s in app_file.symbols}
    assert "App" in names
    assert "AppComponent" in names


def test_analyzer_dependency_graph(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    assert len(result.dependencies) > 0
    # login.py 应该依赖 logger
    login_deps = [d for d in result.dependencies if "login.py" in d.source]
    assert len(login_deps) > 0


def test_find_dependents(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    dependents = analyzer.find_dependents(result, "src/utils/logger.py")
    assert len(dependents) > 0
    assert any("login.py" in d for d in dependents)


def test_get_symbol_map(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    symbol_map = analyzer.get_symbol_map(result)
    assert len(symbol_map) > 0
    for path, symbols in symbol_map.items():
        assert isinstance(symbols, list)


def test_analyzer_ignores_unwanted_dirs():
    path = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(path, "node_modules", "pkg"))
        os.makedirs(os.path.join(path, "src"))
        with open(os.path.join(path, "node_modules", "pkg", "index.js"), "w") as f:
            f.write("module.exports = {};\n")
        with open(os.path.join(path, "src", "main.py"), "w") as f:
            f.write("print('hello')\n")
        analyzer = CodebaseAnalyzer(path)
        result = analyzer.analyze()
        paths = [f.path for f in result.files]
        assert any("main.py" in p for p in paths)
        assert not any("node_modules" in p for p in paths)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_analyzer_line_count(sample_project):
    analyzer = CodebaseAnalyzer(sample_project)
    result = analyzer.analyze()
    assert result.total_lines > 0
    for f in result.files:
        assert f.line_count >= 0
