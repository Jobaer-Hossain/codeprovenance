"""
CodeProvenance Automated Unit Tests
"""

import unittest
from pathlib import Path
from codeprovenance.core.parser import CodebaseParser
from codeprovenance.core.rules_engine import RulesEngine, DEFAULT_BLUEPRINT
from codeprovenance.core.drift_tracker import DriftTracker
from codeprovenance.core.models import FileASTMetrics


class TestCodeProvenance(unittest.TestCase):

    def test_layer_assignment(self):
        engine = RulesEngine(DEFAULT_BLUEPRINT)
        self.assertEqual(engine.assign_layer("src/api/user_controller.py"), "presentation")
        self.assertEqual(engine.assign_layer("src/services/auth_service.py"), "services")
        self.assertEqual(engine.assign_layer("src/data/user_repository.py"), "data")
        self.assertEqual(engine.assign_layer("src/core/security.py"), "core")

    def test_forbidden_import_detection(self):
        engine = RulesEngine(DEFAULT_BLUEPRINT)
        bad_file = FileASTMetrics(
            file_path="src/api/orders_controller.py",
            lines_of_code=80,
            functions_count=4,
            classes_count=1,
            max_complexity=3,
            imported_modules=["sqlite3", "fastapi"],
            internal_dependencies=[]
        )
        violations, _ = engine.evaluate_codebase([bad_file])
        forbidden = [v for v in violations if v.rule_id == "RULE-FORBIDDEN-IMPORT"]
        self.assertEqual(len(forbidden), 1)
        self.assertEqual(forbidden[0].severity, "critical")

    def test_circular_dependency_detection(self):
        engine = RulesEngine(DEFAULT_BLUEPRINT)
        mod_a = FileASTMetrics(
            file_path="src/services/service_a.py",
            lines_of_code=40,
            functions_count=2,
            classes_count=1,
            max_complexity=2,
            imported_modules=[],
            internal_dependencies=["services.service_b"]
        )
        mod_b = FileASTMetrics(
            file_path="src/services/service_b.py",
            lines_of_code=40,
            functions_count=2,
            classes_count=1,
            max_complexity=2,
            imported_modules=[],
            internal_dependencies=["services.service_a"]
        )
        violations, _ = engine.evaluate_codebase([mod_a, mod_b])
        cycles = [v for v in violations if v.rule_id == "RULE-CIRCULAR-DEPENDENCY"]
        self.assertGreaterEqual(len(cycles), 1)

    def test_drift_score_calculation(self):
        tracker = DriftTracker()
        report = tracker.scan_project(Path(__file__).resolve().parent.parent)
        self.assertGreater(report.total_files, 0)
        self.assertGreaterEqual(report.compliance_score_pct, 0.0)
        self.assertLessEqual(report.compliance_score_pct, 100.0)


if __name__ == "__main__":
    unittest.main()
