"""Data models for the refactor agent."""

from typing import List, Dict, Optional, Set, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class RefactorType(str, Enum):
    """Types of refactoring operations."""
    EXTRACT_SERVICE = "extract_service"
    MERGE_SERVICES = "merge_services"
    SPLIT_SERVICE = "split_service"
    RENAME = "rename"
    RESTRUCTURE = "restructure"
    DEPENDENCY_INJECTION = "dependency_injection"
    INTERFACE_EXTRACTION = "interface_extraction"
    DATABASE_MIGRATION = "database_migration"
    API_VERSIONING = "api_versioning"
    REMOVE_DEAD_CODE = "remove_dead_code"


class SafetyLevel(str, Enum):
    """Safety levels for refactoring operations."""
    LOW = "low"      # Quick changes, minimal testing
    MEDIUM = "medium"  # Standard testing, some risk
    HIGH = "high"    # Extensive testing, minimal risk


class ServiceDependency(BaseModel):
    """Represents a dependency between services."""
    source: str
    target: str
    dependency_type: str  # 'api', 'database', 'message_queue', 'shared_lib'
    strength: float = Field(ge=0.0, le=1.0)  # 0-1 coupling strength
    calls: List[str] = []  # Specific API calls or operations


class CodeSmell(BaseModel):
    """Represents a detected code smell or anti-pattern."""
    type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    location: str
    description: str
    suggested_fix: Optional[str] = None
    effort_estimate: Optional[int] = None  # Hours


class ArchitectureAnalysis(BaseModel):
    """Results of architecture analysis."""
    services: Dict[str, Dict[str, Any]]
    dependencies: List[ServiceDependency]
    code_smells: List[CodeSmell]
    metrics: Dict[str, float]
    recommendations: List[str]
    risk_areas: List[Dict[str, Any]]


class RefactorStep(BaseModel):
    """A single step in the refactoring process."""
    id: str
    type: RefactorType
    description: str
    target_files: List[str]
    dependencies: List[str] = []  # IDs of steps this depends on
    estimated_effort: int  # Hours
    risk_level: str
    rollback_strategy: Optional[str] = None
    validation_steps: List[str] = []
    commit_message: Optional[str] = None


class RefactorPlan(BaseModel):
    """Complete refactoring plan."""
    id: str
    created_at: datetime
    target_architecture: str
    safety_level: SafetyLevel
    steps: List[RefactorStep]
    total_effort: int  # Hours
    risk_assessment: Dict[str, Any]
    success_criteria: List[str]
    rollback_plan: Optional[str] = None


class RegressionRisk(BaseModel):
    """Represents a potential regression risk."""
    type: str  # 'api_change', 'behavior_change', 'performance', 'security'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    affected_components: List[str]
    mitigation: Optional[str] = None
    test_suggestions: List[str] = []


class CodeChange(BaseModel):
    """Represents a code change."""
    file_path: str
    change_type: str  # 'add', 'modify', 'delete', 'rename'
    diff: str
    line_changes: Dict[str, int]  # {'added': n, 'removed': m}
    semantic_changes: List[str]  # High-level description of changes


class CommitInfo(BaseModel):
    """Information for a git commit."""
    message: str
    type: str  # 'feat', 'fix', 'refactor', 'test', 'docs', 'style', 'perf'
    scope: Optional[str] = None
    breaking_change: bool = False
    files: List[str] = []
    body: Optional[str] = None
    footer: Optional[str] = None


class RefactorResult(BaseModel):
    """Result of a refactoring operation."""
    step_id: str
    success: bool
    changes: List[CodeChange]
    regression_risks: List[RegressionRisk]
    commit_info: Optional[CommitInfo] = None
    error: Optional[str] = None
    rollback_performed: bool = False
    metrics_before: Dict[str, Any] = {}
    metrics_after: Dict[str, Any] = {}


class MigrationStrategy(BaseModel):
    """Strategy for migrating between architectures."""
    name: str
    description: str
    phases: List[Dict[str, Any]]
    prerequisites: List[str]
    risks: List[str]
    estimated_duration: int  # Days
    resource_requirements: Dict[str, Any]