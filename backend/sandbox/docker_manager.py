#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker Sandbox - 安全的代码执行环境
Week 20.5 实现：容器生命周期管理、代码执行隔离、文件操作
"""
import asyncio
import tempfile
import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

# 尝试导入 Docker SDK
try:
    import docker
    from docker.errors import NotFound, DockerException
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    print("[Sandbox] Docker SDK not available, using mock mode")


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error
        }


class DockerSandboxManager:
    """Docker 沙箱管理器"""
    
    def __init__(self):
        self._client = None
        self._containers: Dict[str, str] = {}  # task_id -> container_id
        self._work_dirs: Dict[str, str] = {}   # task_id -> work_dir path
        
        # 加载配置
        from backend.config.docker_config import (
            SANDBOX_IMAGE, FALLBACK_IMAGE, DEFAULT_TIMEOUT,
            MEMORY_LIMIT, CPU_QUOTA, SANDBOX_WORKDIR
        )
        self.image = SANDBOX_IMAGE
        self.fallback_image = FALLBACK_IMAGE
        self.timeout = DEFAULT_TIMEOUT
        self.memory_limit = MEMORY_LIMIT
        self.cpu_quota = CPU_QUOTA
        self.workdir = SANDBOX_WORKDIR
    
    def _get_client(self):
        """延迟初始化 Docker 客户端"""
        if self._client is None and DOCKER_AVAILABLE:
            try:
                self._client = docker.from_env()
                # 测试连接
                self._client.ping()
            except Exception as e:
                print(f"[Sandbox] Docker connection failed: {e}")
                self._client = None
        return self._client
    
    def _ensure_image(self) -> str:
        """确保镜像存在，返回可用镜像名"""
        client = self._get_client()
        if not client:
            return self.fallback_image
        
        try:
            client.images.get(self.image)
            return self.image
        except NotFound:
            print(f"[Sandbox] Image {self.image} not found, trying fallback")
            try:
                client.images.get(self.fallback_image)
                return self.fallback_image
            except NotFound:
                print(f"[Sandbox] Pulling fallback image {self.fallback_image}")
                try:
                    client.images.pull(self.fallback_image)
                    return self.fallback_image
                except Exception as e:
                    print(f"[Sandbox] Failed to pull image: {e}")
                    return self.fallback_image
        except Exception as e:
            print(f"[Sandbox] Error checking image: {e}")
            return self.fallback_image
    
    async def create_sandbox(self, task_id: str) -> str:
        """
        为任务创建沙箱容器
        返回容器 ID
        """
        # 检查是否已存在
        if task_id in self._containers:
            return self._containers[task_id]
        
        client = self._get_client()
        if not client:
            # Mock 模式
            self._containers[task_id] = f"mock-{task_id}"
            return self._containers[task_id]
        
        # 创建临时工作目录
        work_dir = tempfile.mkdtemp(prefix=f"blueclaw_{task_id}_")
        self._work_dirs[task_id] = work_dir
        
        image = self._ensure_image()
        
        try:
            container = client.containers.run(
                image,
                command="sleep 3600",  # 保持运行 1 小时
                detach=True,
                working_dir=self.workdir,
                volumes={work_dir: {"bind": self.workdir, "mode": "rw"}},
                network_mode="none",  # 隔离网络（可选，根据需要开启）
                mem_limit=self.memory_limit,
                cpu_quota=self.cpu_quota,
                name=f"blueclaw-sandbox-{task_id}",
                auto_remove=False,
                stdin_open=True,
                tty=False
            )
            
            self._containers[task_id] = container.id
            print(f"[Sandbox] Created: {container.id[:12]} for task {task_id}")
            return container.id
            
        except Exception as e:
            print(f"[Sandbox] Failed to create: {e}")
            # Mock 模式回退
            self._containers[task_id] = f"mock-{task_id}"
            return self._containers[task_id]
    
    async def execute_code(
        self,
        task_id: str,
        code: str,
        language: str = "python",
        timeout: Optional[int] = None
    ) -> SandboxResult:
        """
        在沙箱中执行代码
        """
        # 确保沙箱存在
        container_id = await self.create_sandbox(task_id)
        
        # Mock 模式
        if container_id.startswith("mock-"):
            return await self._mock_execute(code, language)
        
        client = self._get_client()
        if not client:
            return await self._mock_execute(code, language)
        
        try:
            container = client.containers.get(container_id)
        except Exception as e:
            print(f"[Sandbox] Container not found: {e}")
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=0,
                error=f"Container not found: {e}"
            )
        
        # 准备执行命令
        if language == "python":
            # 使用 -c 执行代码，处理引号
            escaped_code = code.replace("'", "'\\''")
            cmd = f"python3 -c '{escaped_code}'"
        elif language == "bash":
            escaped_code = code.replace("'", "'\\''")
            cmd = f"bash -c '{escaped_code}'"
        else:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=0,
                error=f"Unsupported language: {language}"
            )
        
        try:
            start_time = time.time()
            
            # 执行命令
            exec_result = container.exec_run(
                cmd,
                stdout=True,
                stderr=True,
                demux=True,
                timeout=timeout or self.timeout
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # 解析输出
            stdout = ""
            stderr = ""
            
            if exec_result.output:
                stdout_bytes, stderr_bytes = exec_result.output
                if stdout_bytes:
                    stdout = stdout_bytes.decode('utf-8', errors='replace')
                if stderr_bytes:
                    stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            return SandboxResult(
                success=exec_result.exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exec_result.exit_code,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=0,
                error=str(e)
            )
    
    async def execute_file(
        self,
        task_id: str,
        filename: str,
        content: str,
        language: str = "python"
    ) -> SandboxResult:
        """
        在沙箱中执行文件
        """
        # 确保沙箱存在
        container_id = await self.create_sandbox(task_id)
        
        # Mock 模式
        if container_id.startswith("mock-"):
            return await self._mock_execute(content, language)
        
        client = self._get_client()
        if not client:
            return await self._mock_execute(content, language)
        
        try:
            container = client.containers.get(container_id)
        except Exception as e:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=0,
                error=f"Container not found: {e}"
            )
        
        # 写入文件 - 使用 echo 简单实现
        file_path = f"{self.workdir}/{filename}"
        
        # 分段写入（避免命令过长）
        max_chunk = 1000
        chunks = [content[i:i+max_chunk] for i in range(0, len(content), max_chunk)]
        
        try:
            # 清空文件
            container.exec_run(f"truncate -s 0 {file_path}")
            
            for chunk in chunks:
                escaped = chunk.replace("'", "'\\''").replace("\\", "\\\\")
                container.exec_run(f"echo -n '{escaped}' >> {file_path}")
            
            # 执行文件
            if language == "python":
                run_cmd = f"python3 {file_path}"
            elif language == "bash":
                run_cmd = f"bash {file_path}"
            else:
                run_cmd = f"cat {file_path}"
            
            start_time = time.time()
            
            exec_result = container.exec_run(
                run_cmd,
                stdout=True,
                stderr=True,
                demux=True,
                timeout=self.timeout
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            stdout = ""
            stderr = ""
            
            if exec_result.output:
                stdout_bytes, stderr_bytes = exec_result.output
                if stdout_bytes:
                    stdout = stdout_bytes.decode('utf-8', errors='replace')
                if stderr_bytes:
                    stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            return SandboxResult(
                success=exec_result.exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exec_result.exit_code,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=0,
                error=str(e)
            )
    
    async def cleanup(self, task_id: str):
        """清理沙箱容器"""
        container_id = self._containers.get(task_id)
        
        if container_id and container_id.startswith("mock-"):
            del self._containers[task_id]
            return
        
        client = self._get_client()
        if not client or not container_id:
            return
        
        try:
            container = client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)
            print(f"[Sandbox] Cleaned up: {container_id[:12]}")
        except NotFound:
            pass
        except Exception as e:
            print(f"[Sandbox] Cleanup error: {e}")
        finally:
            if task_id in self._containers:
                del self._containers[task_id]
            
            # 清理临时目录
            if task_id in self._work_dirs:
                import shutil
                try:
                    shutil.rmtree(self._work_dirs[task_id], ignore_errors=True)
                except:
                    pass
                del self._work_dirs[task_id]
    
    async def read_file(self, task_id: str, path: str) -> str:
        """从沙箱读取文件"""
        container_id = self._containers.get(task_id)
        if not container_id:
            return f"Error: No sandbox for task {task_id}"
        
        if container_id.startswith("mock-"):
            return "# Mock file content"
        
        client = self._get_client()
        if not client:
            return "Error: Docker not available"
        
        try:
            container = client.containers.get(container_id)
            result = container.exec_run(f"cat {path}")
            
            if result.exit_code == 0:
                return result.output.decode('utf-8', errors='replace')
            else:
                return f"Error reading file: {result.output.decode('utf-8', errors='replace')}"
        except Exception as e:
            return f"Error: {e}"
    
    async def write_file(self, task_id: str, path: str, content: str):
        """写入文件到沙箱"""
        container_id = self._containers.get(task_id)
        if not container_id:
            raise ValueError(f"No sandbox for task: {task_id}")
        
        if container_id.startswith("mock-"):
            return
        
        client = self._get_client()
        if not client:
            return
        
        try:
            container = client.containers.get(container_id)
            
            # 分段写入
            max_chunk = 1000
            chunks = [content[i:i+max_chunk] for i in range(0, len(content), max_chunk)]
            
            container.exec_run(f"truncate -s 0 {path}")
            for chunk in chunks:
                escaped = chunk.replace("'", "'\\''").replace("\\", "\\\\")
                container.exec_run(f"echo -n '{escaped}' >> {path}")
                
        except Exception as e:
            print(f"[Sandbox] Write file error: {e}")
    
    async def _mock_execute(self, code: str, language: str) -> SandboxResult:
        """Mock 执行（当 Docker 不可用时）"""
        await asyncio.sleep(0.1)  # 模拟执行时间
        
        return SandboxResult(
            success=True,
            stdout=f"[MOCK] Executed {language} code:\n{code[:100]}...",
            stderr="",
            exit_code=0,
            execution_time_ms=100
        )
    
    async def list_containers(self) -> Dict[str, str]:
        """列出所有管理的容器"""
        return dict(self._containers)


# 全局实例
sandbox_manager = DockerSandboxManager()
