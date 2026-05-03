import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.test_generation.analyzer_agent import CodeAnalyzerAgent


class TestCodeAnalyzerAgent:
    """Unit tests for CodeAnalyzerAgent."""

    def test_analyze_simple_project(self):
        """Test analyzing a simple project with one Python file."""
        agent = CodeAnalyzerAgent()

        # Create a temporary directory with a simple Python file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            py_file = temp_path / "example.py"
            py_file.write_text("""
def add(a: int, b: int) -> int:
    '''Add two numbers.'''
    return a + b

class Calculator:
    def multiply(self, x: int, y: int) -> int:
        return x * y
""")

            result = agent.analyze(str(temp_path))

            assert result["total_files"] == 1
            assert result["total_functions"] == 1  # add (top-level function)
            assert result["total_classes"] == 1
            assert len(result["files"]) == 1

            file_info = result["files"][0]
            assert len(file_info["functions"]) == 1  # only add
            assert len(file_info["classes"]) == 1

            # Check function info
            func_names = [f["name"] for f in file_info["functions"]]
            assert "add" in func_names

            # Check class info
            class_info = file_info["classes"][0]
            assert class_info["name"] == "Calculator"
            assert "multiply" in class_info["methods"]

    def test_extract_function_info(self):
        """Test extracting function information from AST node."""
        import ast

        agent = CodeAnalyzerAgent()

        # Create a function AST node
        source = """
def test_func(param1: str, param2: int = 42) -> bool:
    '''Test function docstring.'''
    if param1:
        return True
    return False
"""
        tree = ast.parse(source)
        func_node = tree.body[0]

        test_index = []
        result = agent._extract_function_info(func_node, test_index)

        assert result["name"] == "test_func"
        assert len(result["parameters"]) == 2
        assert result["parameters"][0]["name"] == "param1"
        assert result["parameters"][1]["name"] == "param2"
        assert result["return_type"] == "bool"
        assert result["docstring"] == "Test function docstring."
        assert result["complexity"] == 2  # base + if statement
        assert result["has_tests"] is False

    def test_calculate_complexity(self):
        """Test calculating cyclomatic complexity."""
        import ast

        agent = CodeAnalyzerAgent()

        # Simple function
        simple_source = "def simple(): pass"
        simple_tree = ast.parse(simple_source)
        assert agent._calculate_complexity(simple_tree.body[0]) == 1

        # Function with if statement
        if_source = """
def complex_func():
    if True:
        pass
    for i in range(10):
        pass
    while False:
        pass
"""
        if_tree = ast.parse(if_source)
        complexity = agent._calculate_complexity(if_tree.body[0])
        assert complexity == 4  # base + if + for + while

    def test_has_tests(self):
        """Test checking if a function has corresponding tests."""
        agent = CodeAnalyzerAgent()

        # Test index with matching test
        test_index = ["def test_my_function(): pass", "my_function()"]
        assert agent._has_tests("my_function", test_index) is True

        # Test index without matching test
        test_index_no_match = ["def test_other(): pass"]
        assert agent._has_tests("my_function", test_index_no_match) is False

        # Empty test index
        assert agent._has_tests("my_function", []) is False

    def test_classify_import(self):
        """Test classifying import types."""
        agent = CodeAnalyzerAgent()

        local_modules = {"mypackage", "utils"}

        # Standard library
        assert agent._classify_import("os", local_modules) == "standard"
        assert agent._classify_import("sys.path", local_modules) == "standard"

        # Local module
        assert agent._classify_import("mypackage", local_modules) == "local"
        assert agent._classify_import("mypackage.submodule", local_modules) == "local"

        # Third party
        assert agent._classify_import("requests", local_modules) == "third_party"
        assert agent._classify_import("numpy.array", local_modules) == "third_party"

        # Relative import
        assert agent._classify_import("mypackage", local_modules, level=1) == "local"