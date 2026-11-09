"""
CodeProvenance AST & Source Parser
Extracts imports, cyclomatic complexity, classes, and dependency relationships.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional
from codeprovenance.core.models import FileASTMetrics


class CodebaseParser:

    @staticmethod
    def calculate_cyclomatic_complexity_python(tree: ast.AST) -> int:
        """
        Calculates cyclomatic complexity using McCabe's metric:
        Complexity = 1 + number of branching decision points.
        """
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.IfExp):
                complexity += 1
        return complexity

    @classmethod
    def parse_python_file(cls, file_path: Path, project_root: Path) -> FileASTMetrics:
        """Parses a Python source file using standard library AST."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

        loc = len([l for l in content.splitlines() if l.strip() and not l.strip().startswith("#")])
        imported_modules: List[str] = []
        internal_deps: List[str] = []
        functions_count = 0
        classes_count = 0
        max_complexity = 1

        try:
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions_count += 1
                    func_complexity = cls.calculate_cyclomatic_complexity_python(node)
                    if func_complexity > max_complexity:
                        max_complexity = func_complexity
                elif isinstance(node, ast.ClassDef):
                    classes_count += 1
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.append(node.module)

            # Map imports to internal project relative modules
            rel_path = file_path.relative_to(project_root).as_posix()
            root_module_names = [p.stem for p in project_root.iterdir() if p.is_dir() or p.suffix == ".py"]
            
            for mod in imported_modules:
                top_pkg = mod.split(".")[0]
                if top_pkg in root_module_names:
                    internal_deps.append(mod)

        except SyntaxError:
            # Fallback regex parsing if file has syntax errors
            imported_modules = re.findall(r"^(?:from|import)\s+([\w\.]+)", content, re.MULTILINE)
            max_complexity = 2

        return FileASTMetrics(
            file_path=file_path.relative_to(project_root).as_posix(),
            lines_of_code=loc,
            functions_count=functions_count,
            classes_count=classes_count,
            max_complexity=max_complexity,
            imported_modules=sorted(list(set(imported_modules))),
            internal_dependencies=sorted(list(set(internal_deps)))
        )

    @classmethod
    def parse_javascript_file(cls, file_path: Path, project_root: Path) -> FileASTMetrics:
        """Parses JS / TS files using static regex heuristics."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

        loc = len([l for l in content.splitlines() if l.strip() and not l.strip().startswith("//")])
        
        # Match ES imports and CommonJS requires
        es_imports = re.findall(r"(?:import|from)\s+['\"]([^'\"]+)['\"]", content)
        require_imports = re.findall(r"require\(['\"]([^'\"]+)['\"]\)", content)
        all_imports = list(set(es_imports + require_imports))

        functions = len(re.findall(r"(?:function\s+\w+|=>|\b(?:async\s+)?function\b)", content))
        classes = len(re.findall(r"\bclass\s+\w+", content))

        # Decision branches
        branches = len(re.findall(r"\b(if|else if|for|while|case|catch)\b", content)) + 1

        internal_deps = [imp for imp in all_imports if imp.startswith(".") or "/" in imp]

        return FileASTMetrics(
            file_path=file_path.relative_to(project_root).as_posix(),
            lines_of_code=loc,
            functions_count=functions,
            classes_count=classes,
            max_complexity=branches,
            imported_modules=all_imports,
            internal_dependencies=internal_deps
        )

    @classmethod
    def parse_directory(cls, root_dir: Path) -> List[FileASTMetrics]:
        """Recursively parses all source code in the directory."""
        metrics: List[FileASTMetrics] = []
        ignored_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

        for p in root_dir.rglob("*"):
            if any(part in ignored_dirs for part in p.parts):
                continue
            if p.is_file():
                if p.suffix == ".py":
                    metrics.append(cls.parse_python_file(p, root_dir))
                elif p.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                    metrics.append(cls.parse_javascript_file(p, root_dir))

        return metrics
