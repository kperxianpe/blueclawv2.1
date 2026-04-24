# -*- coding: utf-8 -*-
"""
IDE 模块数据模型
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# ========== Existing models (Week 26-27) ==========

class CodeSymbol(BaseModel):
    """代码符号（函数/类/变量）"""
    name: str
    symbol_type: str  # function / class / method / variable
    line_start: int = 0
    line_end: int = 0
    signature: str = ""
    docstring: str = ""
    parameters: List[str] = Field(default_factory=list)
    returns: Optional[str] = None


class FileAnalysis(BaseModel):
    """单个文件的分析结果"""
    path: str
    language: str = ""
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    symbols: List[CodeSymbol] = Field(default_factory=list)
    line_count: int = 0


class DependencyEdge(BaseModel):
    """依赖边"""
    source: str  # 源文件路径
    target: str  # 目标文件路径或模块名
    edge_type: str = "import"  # import / inherit / call


class CodebaseAnalysis(BaseModel):
    """代码库分析结果"""
    project_path: str = ""
    files: List[FileAnalysis] = Field(default_factory=list)
    dependencies: List[DependencyEdge] = Field(default_factory=list)
    languages: Dict[str, int] = Field(default_factory=dict)  # language -> file count
    total_files: int = 0
    total_lines: int = 0


class ModificationTask(BaseModel):
    """单个修改任务"""
    task_id: str
    file_path: str
    description: str = ""
    task_type: str = "edit"  # edit / create / delete
    dependencies: List[str] = Field(default_factory=list)  # 依赖的其他 task_id
    estimated_lines: int = 0


class ModificationPlan(BaseModel):
    """架构规划结果"""
    blueprint_id: str = ""
    tasks: List[ModificationTask] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)  # task_id 拓扑排序
    estimated_duration_ms: float = 0.0
    conflicts: List[str] = Field(default_factory=list)


class BoundaryRule(BaseModel):
    """边界规则"""
    rule_type: str  # allow / deny / protected
    pattern: str  # glob pattern
    description: str = ""


class BoundaryCheckResult(BaseModel):
    """边界检查结果"""
    allowed: bool = True
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class DiffHunk(BaseModel):
    """Diff 片段"""
    old_start: int = 0
    old_lines: int = 0
    new_start: int = 0
    new_lines: int = 0
    lines: List[str] = Field(default_factory=list)


class FileDiff(BaseModel):
    """文件级 Diff"""
    file_path: str
    old_path: Optional[str] = None
    hunks: List[DiffHunk] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0


class CodeModelResponse(BaseModel):
    """代码模型响应"""
    success: bool = False
    diffs: List[FileDiff] = Field(default_factory=list)
    explanation: str = ""
    tokens_used: int = 0
    error: Optional[str] = None


# ========== Week 27: Sandbox Validation ==========

class SandboxConfig(BaseModel):
    """沙盒配置"""
    enabled: bool = True
    use_docker: bool = False  # 回退到本地临时目录
    timeout_seconds: int = 60
    env_vars: Dict[str, str] = Field(default_factory=dict)
    # 验证阶段开关
    check_syntax: bool = True
    check_static_analysis: bool = False  # 需要 pylint/eslint 安装
    check_tests: bool = True


class ValidationCheck(BaseModel):
    """单项验证结果"""
    check_type: str  # syntax / static_analysis / test / compile
    passed: bool
    details: str = ""
    duration_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""


class SandboxValidationResult(BaseModel):
    """沙盒验证结果"""
    success: bool = False
    checks: List[ValidationCheck] = Field(default_factory=list)
    summary: str = ""
    total_duration_ms: float = 0.0
    error: Optional[str] = None

    @property
    def passed_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if c.passed]

    @property
    def failed_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if not c.passed]


# ========== Week 27: Incremental Applier ==========

class ApplyResult(BaseModel):
    """增量应用结果"""
    success: bool = False
    committed: bool = False
    commit_hash: str = ""
    commit_message: str = ""
    files_changed: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    rollback_available: bool = False
    pre_apply_head: str = ""  # 回滚用的原始 HEAD


class GitStatus(BaseModel):
    """Git 状态"""
    branch: str = ""
    is_clean: bool = True
    modified_files: List[str] = Field(default_factory=list)
    untracked_files: List[str] = Field(default_factory=list)
    has_conflicts: bool = False


# ========== Week 27: Modification Loop ==========

class LoopConfig(BaseModel):
    """循环控制器配置"""
    max_iterations: int = 3
    enable_auto_apply: bool = False  # 验证通过后是否自动应用
    pause_on_failure: bool = True    # 重试耗尽后是否暂停
    feedback_full_context: bool = True  # 反馈时包含完整上下文


class LoopIteration(BaseModel):
    """单次迭代记录"""
    iteration: int
    code_model_response: Optional[CodeModelResponse] = None
    validation_result: Optional[SandboxValidationResult] = None
    error_feedback: str = ""
    duration_ms: float = 0.0


class LoopResult(BaseModel):
    """循环控制最终结果"""
    success: bool = False
    iterations: int = 0
    iteration_history: List[LoopIteration] = Field(default_factory=list)
    final_validation: Optional[SandboxValidationResult] = None
    final_apply: Optional[ApplyResult] = None
    error: Optional[str] = None
    debug_log: List[str] = Field(default_factory=list)
    paused_for_human: bool = False


# ========== NEW: IDE Workspace & File API Models ==========

class WorkspaceInfo(BaseModel):
    """工作区信息"""
    root_path: str
    name: str
    language_distribution: Dict[str, int] = Field(default_factory=dict)


class FileEntry(BaseModel):
    """文件/目录条目"""
    name: str
    path: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    modified_time: Optional[float] = None
    language: Optional[str] = None


class FileTreeResponse(BaseModel):
    """文件树响应"""
    path: str
    entries: List[FileEntry] = Field(default_factory=list)


class FileContent(BaseModel):
    """文件内容响应"""
    path: str
    content: str
    language: str
    line_count: int
    encoding: str = "utf-8"


class FileWriteRequest(BaseModel):
    """写入文件请求"""
    path: str
    content: str
    encoding: str = "utf-8"


class FileCreateRequest(BaseModel):
    """创建文件/目录请求"""
    path: str
    type: Literal["file", "directory"]


class FileRenameRequest(BaseModel):
    """重命名请求"""
    old_path: str
    new_path: str


class FileOperationResult(BaseModel):
    """文件操作结果"""
    success: bool
    path: str
    message: str = ""
    error: Optional[str] = None


# ========== NEW: Process Runner Models ==========

class RunRequest(BaseModel):
    """执行代码请求"""
    path: Optional[str] = None
    command: Optional[str] = None
    cwd: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 30


class RunResult(BaseModel):
    """执行结果"""
    run_id: str
    command: str
    status: Literal["running", "completed", "failed", "killed"]
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0


class RunOutputChunk(BaseModel):
    """执行输出块（SSE/WebSocket 用）"""
    run_id: str
    type: Literal["stdout", "stderr", "exit", "error"]
    data: str = ""
    exit_code: Optional[int] = None


# ========== NEW: Test Runner Models ==========

class TestRunRequest(BaseModel):
    """运行测试请求"""
    path: str = ""          # 测试目录或文件
    runner: Literal["pytest", "unittest"] = "pytest"
    pattern: str = "test_*.py"
    cwd: Optional[str] = None


class TestCaseResult(BaseModel):
    """单个测试结果"""
    name: str
    status: Literal["passed", "failed", "skipped", "error"]
    duration_ms: float = 0.0
    error: Optional[str] = None
    traceback: Optional[str] = None


class TestRunResult(BaseModel):
    """测试运行结果"""
    test_run_id: str
    status: Literal["running", "completed", "failed"]
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    cases: List[TestCaseResult] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0


# ========== NEW: KimiCode API Models ==========

class KimiCodeChatMessage(BaseModel):
    """KimiCode 聊天消息"""
    role: Literal["system", "user", "assistant"]
    content: str


class KimiCodeChatRequest(BaseModel):
    """KimiCode 聊天请求"""
    session_id: Optional[str] = None
    messages: List[KimiCodeChatMessage]
    context: Optional[Dict[str, Any]] = None  # {active_file, selected_code, line_start, line_end}
    stream: bool = True


class KimiCodeGenerateRequest(BaseModel):
    """KimiCode 代码生成请求"""
    prompt: str
    language: Optional[str] = None
    context_files: Dict[str, str] = Field(default_factory=dict)


class KimiCodeGenerateResponse(BaseModel):
    """KimiCode 代码生成响应"""
    code: str
    language: str
    explanation: str = ""
    tokens_used: int = 0


class KimiCodeInlineRequest(BaseModel):
    """KimiCode 内联补全请求"""
    path: str
    prefix: str
    suffix: str = ""
    language: Optional[str] = None


class KimiCodeInlineResponse(BaseModel):
    """KimiCode 内联补全响应"""
    completion: str
    confidence: float = 0.0
    tokens_used: int = 0


class KimiCodeDiffRequest(BaseModel):
    """KimiCode Diff 请求"""
    session_id: Optional[str] = None
    prompt: str
    context_files: Dict[str, str] = Field(default_factory=dict)


class KimiCodeDiffResponse(BaseModel):
    """KimiCode Diff 响应"""
    diff_id: str
    diffs: List[FileDiff] = Field(default_factory=list)
    explanation: str = ""


class KimiCodeDiffPreviewResponse(BaseModel):
    """Diff 预览响应"""
    diff_id: str
    preview: Dict[str, Dict[str, str]] = Field(default_factory=dict)  # file -> {old, new}


class KimiCodeDiffApplyRequest(BaseModel):
    """Diff 应用请求"""
    diff_id: str


class KimiCodeDiffApplyResponse(BaseModel):
    """Diff 应用响应"""
    success: bool
    applied_files: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class KimiCodeSessionInfo(BaseModel):
    """KimiCode 会话信息"""
    session_id: str
    created_at: float
    message_count: int = 0
    context_file_count: int = 0
