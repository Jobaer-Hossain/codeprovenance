"""
CodeProvenance Data Models
Defines schema definitions for architectural rules, AST parsing, layer violations, and drift metrics.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Set
from enum import Enum
from datetime import datetime


class ViolationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArchitecturalLayer(BaseModel):
    name: str = Field(..., description="Name of the architectural layer, e.g., 'presentation', 'domain', 'data'")
    path_patterns: List[str] = Field(..., description="Glob patterns that map files to this layer")
    allowed_dependencies: List[str] = Field(default_factory=list, description="Layers this layer is allowed to import")
    description: str = ""


class ArchitecturalRule(BaseModel):
    id: str
    name: str
    description: str
    severity: ViolationSeverity = ViolationSeverity.HIGH
    rule_type: str = Field(..., description="'layer_boundary', 'circular_dependency', 'max_complexity', 'forbidden_import'")


class ArchitectureBlueprint(BaseModel):
    project_name: str
    version: str = "1.0.0"
    layers: List[ArchitecturalLayer]
    max_cyclomatic_complexity: int = 12
    max_file_lines: int = 400
    forbidden_imports: Dict[str, List[str]] = Field(default_factory=dict, description="e.g. {'api': ['sqlite3', 'psycopg2']}")


class FileASTMetrics(BaseModel):
    file_path: str
    layer: Optional[str] = None
    lines_of_code: int
    functions_count: int
    classes_count: int
    max_complexity: int
    imported_modules: List[str]
    internal_dependencies: List[str]


class ArchitecturalViolation(BaseModel):
    id: str
    rule_id: str
    file_path: str
    line_number: Optional[int] = None
    severity: ViolationSeverity
    title: str
    description: str
    violating_import: Optional[str] = None
    suggested_fix: str


class RefactoringRecommendation(BaseModel):
    id: str
    file_path: str
    title: str
    issue: str
    suggested_diff: str
    estimated_effort_mins: int


class CodebaseDriftReport(BaseModel):
    scanned_at: datetime
    root_path: str
    total_files: int
    total_loc: int
    compliance_score_pct: float = Field(..., description="0-100% architectural health score")
    drift_status: str = Field(..., description="'Healthy', 'Moderate Drift', 'Severe Architectural Degradation'")
    violations: List[ArchitecturalViolation]
    refactoring_recommendations: List[RefactoringRecommendation]
    layer_distribution: Dict[str, int]
    dependency_graph: Dict[str, List[str]]
