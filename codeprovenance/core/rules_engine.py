"""
CodeProvenance Architectural Rules Engine
Evaluates codebase AST metrics against architectural boundaries and detects drift.
"""

from pathlib import Path
from fnmatch import fnmatch
from typing import List, Dict, Set, Tuple
from codeprovenance.core.models import (
    ArchitectureBlueprint,
    ArchitecturalLayer,
    FileASTMetrics,
    ArchitecturalViolation,
    ViolationSeverity,
    RefactoringRecommendation
)


DEFAULT_BLUEPRINT = ArchitectureBlueprint(
    project_name="Standard Multi-Tier / Clean Architecture",
    version="1.0.0",
    layers=[
        ArchitecturalLayer(
            name="presentation",
            path_patterns=["*api*", "*controllers*", "*routes*", "*views*", "*web*"],
            allowed_dependencies=["domain", "services", "core", "models", "utils"],
            description="HTTP Controllers, REST Endpoints, and View Layers"
        ),
        ArchitecturalLayer(
            name="services",
            path_patterns=["*service*", "*domain*", "*use_cases*", "*business*"],
            allowed_dependencies=["data", "persistence", "models", "core", "utils"],
            description="Core Business Logic and Domain Services"
        ),
        ArchitecturalLayer(
            name="data",
            path_patterns=["*data*", "*db*", "*models*", "*persistence*", "*repository*"],
            allowed_dependencies=["core", "utils"],
            description="Data Access Objects, Database Repositories, and Storage"
        ),
        ArchitecturalLayer(
            name="core",
            path_patterns=["*core*", "*utils*", "*common*", "*helpers*"],
            allowed_dependencies=[],
            description="Shared utilities and domain-agnostic helpers"
        )
    ],
    max_cyclomatic_complexity=12,
    max_file_lines=400,
    forbidden_imports={
        "presentation": ["sqlite3", "psycopg2", "mysql", "sqlalchemy.orm", "prisma", "pymongo"]
    }
)


class RulesEngine:

    def __init__(self, blueprint: ArchitectureBlueprint = DEFAULT_BLUEPRINT):
        self.blueprint = blueprint

    def assign_layer(self, file_path: str) -> str:
        """Determines which architectural layer a file belongs to."""
        normalized = file_path.lower().replace("\\", "/")
        for layer in self.blueprint.layers:
            for pattern in layer.path_patterns:
                if fnmatch(normalized, pattern) or pattern.replace("*", "") in normalized:
                    return layer.name
        return "unassigned"

    def detect_circular_dependencies(self, files: List[FileASTMetrics]) -> List[Tuple[str, str]]:
        """Finds direct or indirect circular import cycles using DFS."""
        graph: Dict[str, Set[str]] = {}
        for f in files:
            mod_name = Path(f.file_path).stem
            deps = set()
            for dep in f.internal_dependencies:
                dep_stem = dep.split(".")[-1]
                deps.add(dep_stem)
            graph[mod_name] = deps

        cycles: List[Tuple[str, str]] = []
        for node, neighbors in graph.items():
            for neighbor in neighbors:
                if neighbor in graph and node in graph[neighbor] and node < neighbor:
                    cycles.append((node, neighbor))

        return cycles

    def evaluate_codebase(self, files: List[FileASTMetrics]) -> Tuple[List[ArchitecturalViolation], List[RefactoringRecommendation]]:
        violations: List[ArchitecturalViolation] = []
        recommendations: List[RefactoringRecommendation] = []

        layer_map = {l.name: l for l in self.blueprint.layers}

        # 1. Check each file for layer boundary, complexity, and forbidden imports
        for f in files:
            layer_name = self.assign_layer(f.file_path)
            f.layer = layer_name

            # Complexity check
            if f.max_complexity > self.blueprint.max_cyclomatic_complexity:
                violations.append(ArchitecturalViolation(
                    id=f"viol-complexity-{Path(f.file_path).stem}",
                    rule_id="RULE-HIGH-COMPLEXITY",
                    file_path=f.file_path,
                    severity=ViolationSeverity.MEDIUM,
                    title=f"Excessive Cyclomatic Complexity ({f.max_complexity})",
                    description=f"Branching logic exceeds the configured ceiling of {self.blueprint.max_cyclomatic_complexity}. High risk of regression and testing overhead.",
                    suggested_fix="Extract nested conditionals or switch blocks into focused helper methods or strategy objects."
                ))
                recommendations.append(RefactoringRecommendation(
                    id=f"refactor-complexity-{Path(f.file_path).stem}",
                    file_path=f.file_path,
                    title="Decompose complex branching into Strategy Pattern",
                    issue=f"Max cyclomatic complexity is {f.max_complexity}",
                    suggested_diff=f"# Refactor: break down large handler in {f.file_path} into smaller pure functions.",
                    estimated_effort_mins=45
                ))

            # File size check
            if f.lines_of_code > self.blueprint.max_file_lines:
                violations.append(ArchitecturalViolation(
                    id=f"viol-lines-{Path(f.file_path).stem}",
                    rule_id="RULE-GOD-OBJECT",
                    file_path=f.file_path,
                    severity=ViolationSeverity.MEDIUM,
                    title=f"Large File Size ({f.lines_of_code} LOC)",
                    description=f"File exceeds maximum threshold of {self.blueprint.max_file_lines} lines of code. Indicates potential God Object anti-pattern.",
                    suggested_fix="Split responsibilities across distinct single-responsibility modules."
                ))

            # Forbidden direct imports
            if layer_name in self.blueprint.forbidden_imports:
                prohibited = self.blueprint.forbidden_imports[layer_name]
                for imp in f.imported_modules:
                    for bad in prohibited:
                        if bad in imp:
                            violations.append(ArchitecturalViolation(
                                id=f"viol-forbidden-{Path(f.file_path).stem}-{bad}",
                                rule_id="RULE-FORBIDDEN-IMPORT",
                                file_path=f.file_path,
                                severity=ViolationSeverity.CRITICAL,
                                title=f"Forbidden Direct Database Import '{bad}' in {layer_name.capitalize()}",
                                description=f"Presentation layer file '{f.file_path}' directly imports '{bad}', bypassing service abstraction boundaries.",
                                violating_import=imp,
                                suggested_fix="Route queries through a Service/Repository class instead of executing database calls in the controller."
                            ))
                            recommendations.append(RefactoringRecommendation(
                                id=f"refactor-decouple-{Path(f.file_path).stem}",
                                file_path=f.file_path,
                                title=f"Decouple direct '{bad}' dependency from {layer_name}",
                                issue=f"Direct import of database driver in presentation controller",
                                suggested_diff=f"- import {bad}\n+ from domain.services import DataService\n# Inject DataService via dependency injection.",
                                estimated_effort_mins=30
                            ))

            # Layer dependency boundaries
            if layer_name in layer_map:
                current_layer = layer_map[layer_name]
                for dep in f.internal_dependencies:
                    dep_layer = self.assign_layer(dep)
                    if dep_layer != "unassigned" and dep_layer != layer_name:
                        if dep_layer not in current_layer.allowed_dependencies:
                            violations.append(ArchitecturalViolation(
                                id=f"viol-layer-{Path(f.file_path).stem}-{dep_layer}",
                                rule_id="RULE-LAYER-VIOLATION",
                                file_path=f.file_path,
                                severity=ViolationSeverity.HIGH,
                                title=f"Architectural Inversion: {layer_name} -> {dep_layer}",
                                description=f"Layer '{layer_name}' imports from '{dep_layer}', which is not in its allowed dependency list: {current_layer.allowed_dependencies}.",
                                violating_import=dep,
                                suggested_fix=f"Invert dependency using interfaces or move shared types to the 'core' or 'models' layer."
                            ))

        # 2. Check circular dependencies
        cycles = self.detect_circular_dependencies(files)
        for c1, c2 in cycles:
            violations.append(ArchitecturalViolation(
                id=f"viol-cycle-{c1}-{c2}",
                rule_id="RULE-CIRCULAR-DEPENDENCY",
                file_path=f"{c1} <-> {c2}",
                severity=ViolationSeverity.HIGH,
                title=f"Circular Module Coupling ({c1} <-> {c2})",
                description=f"Modules '{c1}' and '{c2}' import each other, creating tight coupling and preventing isolated testing.",
                suggested_fix="Extract mutual dependencies into a common submodule or inject dependencies at runtime."
            ))

        return violations, recommendations
