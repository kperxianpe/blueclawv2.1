# -*- coding: utf-8 -*-
"""
ModificationLoop - 修改循环控制器

- 调用代码模型生成修改
- 沙盒验证
- 验证失败时反馈错误信息给代码模型
- 重试逻辑（最多 N 次）
- 重试耗尽后暂停/升级人工
- 完整调试信息记录
"""
import time
from typing import List, Optional, Dict, Any

from blueclaw.adapter.ide.models import (
    LoopConfig, LoopResult, LoopIteration,
    SandboxValidationResult, ApplyResult,
    CodeModelResponse, FileDiff,
)
from blueclaw.adapter.ide.codemodel import BaseCodeModelClient, MockCodeModelClient
from blueclaw.adapter.ide.sandbox import SandboxValidator
from blueclaw.adapter.ide.applier import IncrementApplier


class ModificationLoop:
    """修改循环控制器

    Pipeline: CodeModel -> Sandbox Validate -> (retry on fail) -> Apply
    """

    def __init__(
        self,
        code_model: BaseCodeModelClient,
        sandbox: SandboxValidator,
        applier: Optional[IncrementApplier] = None,
        config: Optional[LoopConfig] = None,
    ):
        self.code_model = code_model
        self.sandbox = sandbox
        self.applier = applier
        self.config = config or LoopConfig()

    async def run(
        self,
        task_description: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]] = None,
    ) -> LoopResult:
        """运行完整的修改-验证-应用循环"""
        result = LoopResult()
        iteration = 0
        debug_log: List[str] = []

        debug_log.append(f"[Loop] Starting modification loop for: {task_description[:80]}")
        debug_log.append(f"[Loop] Max iterations: {self.config.max_iterations}")

        last_validation: Optional[SandboxValidationResult] = None
        last_response: Optional[CodeModelResponse] = None

        while iteration < self.config.max_iterations:
            iteration += 1
            iter_start = time.time()
            iter_record = LoopIteration(iteration=iteration)

            debug_log.append(f"[Loop] === Iteration {iteration}/{self.config.max_iterations} ===")

            # 1. 调用代码模型
            debug_log.append("[Loop] Calling code model...")
            try:
                # 构建 feedback context（如果是重试）
                feedback = self._build_feedback(last_validation) if last_validation else ""
                full_task = task_description
                if feedback:
                    full_task = f"{task_description}\n\n# Previous attempt failed:\n{feedback}"

                response = await self.code_model.generate_code_changes(
                    task_description=full_task,
                    file_context=file_context,
                    constraints=constraints,
                )
                last_response = response
                iter_record.code_model_response = response
                debug_log.append(f"[Loop] Code model returned: success={response.success}, diffs={len(response.diffs)}")
            except Exception as e:
                debug_log.append(f"[Loop] Code model error: {e}")
                result.debug_log = debug_log
                result.error = f"Code model call failed: {e}"
                return result

            if not response.success or not response.diffs:
                debug_log.append("[Loop] Code model returned no diffs, stopping.")
                result.error = response.error or "No diffs generated"
                result.debug_log = debug_log
                return result

            # 2. 沙盒验证
            debug_log.append("[Loop] Running sandbox validation...")
            try:
                validation = await self.sandbox.validate(response.diffs)
                last_validation = validation
                iter_record.validation_result = validation
                iter_record.duration_ms = (time.time() - iter_start) * 1000
                debug_log.append(f"[Loop] Validation: {validation.summary}")
                for check in validation.checks:
                    debug_log.append(f"[Loop]   - {check.check_type}: {'PASS' if check.passed else 'FAIL'} - {check.details}")
            except Exception as e:
                debug_log.append(f"[Loop] Sandbox error: {e}")
                iter_record.duration_ms = (time.time() - iter_start) * 1000
                result.iteration_history.append(iter_record)
                result.error = f"Sandbox validation failed: {e}"
                result.debug_log = debug_log
                return result

            result.iteration_history.append(iter_record)

            # 3. 检查验证结果
            if validation.success:
                debug_log.append("[Loop] Validation passed!")
                result.success = True
                result.final_validation = validation
                break

            # 验证失败，准备重试
            iter_record.error_feedback = self._build_feedback(validation)
            debug_log.append(f"[Loop] Validation failed, feedback prepared for retry.")

        # 循环结束
        result.iterations = iteration
        result.debug_log = debug_log

        if not result.success:
            debug_log.append(f"[Loop] All {iteration} iterations exhausted.")
            if self.config.pause_on_failure:
                debug_log.append("[Loop] Paused for human intervention.")
                result.paused_for_human = True
                result.error = f"Validation failed after {iteration} attempts. Paused for human review."
            else:
                result.error = f"Validation failed after {iteration} attempts."
            return result

        # 4. 可选：应用到主库
        if self.config.enable_auto_apply and self.applier and last_response:
            debug_log.append("[Loop] Applying changes to main repository...")
            try:
                apply_result = self.applier.apply_diffs(last_response.diffs, auto_commit=True)
                result.final_apply = apply_result
                if apply_result.success:
                    debug_log.append(f"[Loop] Applied successfully. Commit: {apply_result.commit_hash[:8] if apply_result.commit_hash else 'N/A'}")
                else:
                    debug_log.append(f"[Loop] Apply failed: {apply_result.error}")
                    result.error = apply_result.error
            except Exception as e:
                debug_log.append(f"[Loop] Apply error: {e}")
                result.error = f"Apply failed: {e}"

        return result

    def _build_feedback(self, validation: SandboxValidationResult) -> str:
        """将验证失败信息格式化为代码模型的反馈"""
        lines: List[str] = []
        lines.append("The previous code changes failed validation. Please fix the following issues:")
        lines.append("")

        for check in validation.failed_checks:
            lines.append(f"## {check.check_type.upper()} FAILED")
            lines.append(f"Details: {check.details}")
            if check.stderr:
                # 截断过长的 stderr
                stderr = check.stderr[:2000]
                lines.append(f"Error output:")
                lines.append("```")
                lines.append(stderr)
                lines.append("```")
            lines.append("")

        if self.config.feedback_full_context and validation.checks:
            lines.append("## All Checks")
            for check in validation.checks:
                status = "PASS" if check.passed else "FAIL"
                lines.append(f"- [{status}] {check.check_type}: {check.details}")

        return "\n".join(lines)
