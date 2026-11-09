"""
CodeProvenance Drift Tracker & Health Scoring
Calculates codebase architectural compliance score and tracks architectural erosion.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict
from codeprovenance.core.models import (
    CodebaseDriftReport,
    FileASTMetrics,
    ArchitecturalViolation,
    ViolationSeverity,
    RefactoringRecommendation
)
from codeprovenance.core.rules_engine import RulesEngine, DEFAULT_BLUEPRINT
from codeprovenance.core.parser import CodebaseParser


class DriftTracker:

    def __init__(self, rules_engine: RulesEngine = None):
        self.rules_engine = rules_engine or RulesEngine(DEFAULT_BLUEPRINT)

    def scan_project(self, target_dir: Path) -> CodebaseDriftReport:
        """Runs a complete AST analysis and architectural drift audit on a codebase directory."""
        target_path = Path(target_dir).resolve()
        parsed_files = CodebaseParser.parse_directory(target_path)

        violations, refactorings = self.rules_engine.evaluate_codebase(parsed_files)

        total_files = len(parsed_files)
        total_loc = sum(f.lines_of_code for f in parsed_files)

        # Layer distribution
        layer_dist: Dict[str, int] = {}
        for f in parsed_files:
            layer = f.layer or "unassigned"
            layer_dist[layer] = layer_dist.get(layer, 0) + 1

        # Dependency graph
        dep_graph: Dict[str, List[str]] = {}
        for f in parsed_files:
            dep_graph[f.file_path] = f.internal_dependencies

        # Calculate Compliance Score (100 base)
        penalty = 0.0
        for v in violations:
            if v.severity == ViolationSeverity.CRITICAL:
                penalty += 15.0
            elif v.severity == ViolationSeverity.HIGH:
                penalty += 10.0
            elif v.severity == ViolationSeverity.MEDIUM:
                penalty += 5.0
            else:
                penalty += 2.0

        score = max(0.0, min(100.0, 100.0 - penalty))

        if score >= 90.0:
            status = "Healthy (Strict Compliance)"
        elif score >= 70.0:
            status = "Moderate Drift (Refactoring Recommended)"
        else:
            status = "Critical Architectural Degradation"

        return CodebaseDriftReport(
            scanned_at=datetime.now(),
            root_path=str(target_path),
            total_files=total_files,
            total_loc=total_loc,
            compliance_score_pct=round(score, 1),
            drift_status=status,
            violations=violations,
            refactoring_recommendations=refactorings,
            layer_distribution=layer_dist,
            dependency_graph=dep_graph
        )
