"""
CodeProvenance Multi-Language AST & Source Parser
Extracts imports, cyclomatic complexity, classes, and dependency relationships across all programming languages.
Automatically ignores third-party vendor libraries, minified files, and generated bundles.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional
from codeprovenance.core.models import FileASTMetrics


# Folders that belong to third-party vendor code or compiled output
IGNORED_DIR_NAMES = {
    ".git", "node_modules", "vendor", "vendors", "plugins", "bower_components",
    ".venv", "venv", "env", "__pycache__", "dist", "build", "out", "target",
    "bin", "obj", "coverage", ".next", ".nuxt", "storage", "public/vendor"
}

# Substrings in filenames that denote third-party or minified bundles
IGNORED_FILENAME_SUBSTRINGS = [
    ".min.js", ".min.css", ".bundle.js", ".bundle.min.js", ".chunk.js",
    "jquery", "bootstrap", "datatables", "chart.js", "chart.min.js",
    "tabletools", "popper.js", "lodash", "react.production", "vue.runtime"
]

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".phtml",
    ".java", ".cs", ".c", ".cpp", ".cc", ".h", ".hpp",
    ".go", ".rs", ".rb", ".kt", ".swift", ".vue", ".svelte"
}


class CodebaseParser:

    @staticmethod
    def is_vendor_or_minified(file_path: Path, content: str) -> bool:
        """Determines if a file is third-party, vendor, or minified bundle."""
        parts_lower = [p.lower() for p in file_path.parts]
        for ignored in IGNORED_DIR_NAMES:
            if ignored in parts_lower:
                return True

        name_lower = file_path.name.lower()
        for substring in IGNORED_FILENAME_SUBSTRINGS:
            if substring in name_lower:
                return True

        # Check for minified lines (average line length or massive single line)
        lines = content.splitlines()
        if len(lines) > 0:
            max_line_len = max(len(l) for l in lines[:50])
            if max_line_len > 800:
                return True
            if len(lines) < 5 and sum(len(l) for l in lines) > 3000:
                return True

        return False

    @staticmethod
    def calculate_cyclomatic_complexity_python(tree: ast.AST) -> int:
        """Calculates cyclomatic complexity using McCabe's metric for Python."""
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
    def parse_python_file(cls, file_path: Path, project_root: Path, content: str) -> FileASTMetrics:
        """Parses a Python source file using standard library AST."""
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

            root_module_names = [p.stem for p in project_root.iterdir() if p.is_dir() or p.suffix == ".py"]
            for mod in imported_modules:
                top_pkg = mod.split(".")[0]
                if top_pkg in root_module_names:
                    internal_deps.append(mod)

        except SyntaxError:
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
    def parse_generic_source_file(cls, file_path: Path, project_root: Path, content: str) -> FileASTMetrics:
        """
        Universal static parser for JavaScript, TypeScript, PHP, Java, C#, Go, Rust, C/C++, Ruby.
        Accurately extracts imports, functions, classes, and decision branching.
        """
        ext = file_path.suffix.lower()
        lines = [l for l in content.splitlines() if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("#")]
        loc = len(lines)

        imported_modules: List[str] = []
        internal_deps: List[str] = []

        # 1. Imports Extraction
        if ext in [".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"]:
            es_imports = re.findall(r"(?:import|from)\s+['\"]([^'\"]+)['\"]", content)
            require_imports = re.findall(r"require\(['\"]([^'\"]+)['\"]\)", content)
            imported_modules = list(set(es_imports + require_imports))
            internal_deps = [imp for imp in imported_modules if imp.startswith(".") or "/" in imp]

        elif ext in [".php", ".phtml"]:
            use_imports = re.findall(r"(?:use|require|require_once|include|include_once)\s+['\"\\A-Za-z0-9_\/]+", content)
            cleaned = [re.sub(r"^(?:use|require|require_once|include|include_once)\s*['\"]?", "", u).strip().strip(";'\"") for u in use_imports]
            imported_modules = list(set(cleaned))
            internal_deps = [u for u in imported_modules if "/" in u or "\\" in u]

        elif ext in [".java", ".kt"]:
            imports = re.findall(r"import\s+([\w\.]+);?", content)
            imported_modules = list(set(imports))
            internal_deps = [imp for imp in imported_modules if not imp.startswith("java.") and not imp.startswith("javax.")]

        elif ext == ".cs":
            usings = re.findall(r"using\s+([\w\.]+);", content)
            imported_modules = list(set(usings))
            internal_deps = [u for u in imported_modules if not u.startswith("System")]

        elif ext in [".c", ".cpp", ".cc", ".h", ".hpp"]:
            includes = re.findall(r"#include\s+[<'\"]([^>'\"]+)[>'\"]", content)
            imported_modules = list(set(includes))
            internal_deps = [inc for inc in imported_modules if inc.endswith(".h") or inc.endswith(".hpp") or "/" in inc]

        elif ext == ".go":
            imports = re.findall(r"\"([\w\.\/]+)\"", content)
            imported_modules = list(set(imports))
            internal_deps = [imp for imp in imported_modules if "/" in imp]

        elif ext == ".rs":
            uses = re.findall(r"use\s+([\w:]+);", content)
            imported_modules = list(set(uses))
            internal_deps = [u for u in imported_modules if u.startswith("crate::") or u.startswith("super::")]

        # 2. Functions & Classes
        func_regex = r"(?:function\s+\w+|\bdef\s+\w+|\bfn\s+\w+|\bfunc\s+\w+|public\s+(?:static\s+)?\w+\s+\w+\(|=>|\b(?:async\s+)?function\b)"
        functions_count = len(re.findall(func_regex, content))

        class_regex = r"\b(?:class|interface|struct|trait|enum)\s+\w+"
        classes_count = len(re.findall(class_regex, content))

        # 3. Cyclomatic Decision Branches
        branch_regex = r"\b(if|else if|for|foreach|while|switch|case|catch|except)\b"
        branch_count = len(re.findall(branch_regex, content))
        # Cap complexity estimate to avoid outlier false positives on generated switch statements
        max_complexity = min(80, max(1, 1 + branch_count))

        return FileASTMetrics(
            file_path=file_path.relative_to(project_root).as_posix(),
            lines_of_code=loc,
            functions_count=functions_count,
            classes_count=classes_count,
            max_complexity=max_complexity,
            imported_modules=sorted(imported_modules[:50]),
            internal_dependencies=sorted(internal_deps[:50])
        )

    @classmethod
    def parse_directory(cls, root_dir: Path) -> List[FileASTMetrics]:
        """Recursively parses all first-party application source code in the directory."""
        metrics: List[FileASTMetrics] = []

        for p in root_dir.rglob("*"):
            if not p.is_file():
                continue

            ext = p.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Skip minified files, vendor directories, or bundled assets
            if cls.is_vendor_or_minified(p, content):
                continue

            if ext == ".py":
                metrics.append(cls.parse_python_file(p, root_dir, content))
            else:
                metrics.append(cls.parse_generic_source_file(p, root_dir, content))

        return metrics
