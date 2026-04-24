# Blueclaw IDE Adapter Module
from blueclaw.adapter.ide.models import (
    CodeSymbol,
    FileAnalysis,
    DependencyEdge,
    CodebaseAnalysis,
    ModificationTask,
    ModificationPlan,
    BoundaryRule,
    BoundaryCheckResult,
    DiffHunk,
    FileDiff,
    CodeModelResponse,
    SandboxConfig,
    ValidationCheck,
    SandboxValidationResult,
    ApplyResult,
    GitStatus,
    LoopConfig,
    LoopIteration,
    LoopResult,
)
from blueclaw.adapter.ide.analyzer import CodebaseAnalyzer
from blueclaw.adapter.ide.planner import ArchitecturePlanner
from blueclaw.adapter.ide.boundary import BoundaryChecker
from blueclaw.adapter.ide.codemodel import (
    BaseCodeModelClient,
    MockCodeModelClient,
    KimiCodeClient,
    parse_unified_diff,
)
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.loop import ModificationLoop
