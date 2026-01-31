import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import timedelta

from opensandbox import Sandbox
from opensandbox.config import ConnectionConfig
from opensandbox.models.execd import ExecutionHandlers, RunCommandOpts

from task_dispath.app.core.config import settings


class SandboxResult:
    """沙盒执行结果。"""

    def __init__(
        self,
        success: bool,
        message: str,
        logs: list[str],
        artifacts: list[str],
    ) -> None:
        self.success = success
        self.message = message
        self.logs = logs
        self.artifacts = artifacts


class SandboxService:
    """沙盒执行服务。"""

    def __init__(self) -> None:
        self._config = ConnectionConfig(
            domain=settings.sandbox_domain,
            api_key=settings.sandbox_api_key,
            request_timeout=timedelta(seconds=60),
        )

    async def run_task(
        self, session_id: str, prompt: str, skills: list[str], mcps: list[str]
    ) -> SandboxResult:
        """在沙盒中执行任务并返回结果。"""

        env = self._build_env()
        sandbox = await Sandbox.create(
            settings.sandbox_image,
            connection_config=self._config,
            env=env,
            entrypoint=settings.sandbox_entrypoint,
        )
        logs: list[str] = []
        artifacts: list[str] = []
        success = False
        message = ""

        async with sandbox:
            work_dir = f"/data/context/{session_id}/work"
            artifact_dir = f"/data/context/{session_id}/artifact"
            task_context_dir = f"/data/context/{session_id}/task-context"

            await sandbox.commands.run(f"mkdir -p {work_dir} {artifact_dir}")

            await self._validate_skills(sandbox, skills)
            await self._validate_mcps(sandbox, mcps)

            install_exec = await sandbox.commands.run(
                "npm i -g @anthropic-ai/claude-code@latest"
            )
            logs.extend(self._format_logs("install", install_exec))

            run_exec = await sandbox.commands.run(
                f"claude {json.dumps(prompt)}",
                opts=RunCommandOpts(working_directory=work_dir),
            )
            logs.extend(self._format_logs("run", run_exec))

            await sandbox.commands.run(f"mkdir -p {task_context_dir}")
            await sandbox.commands.run(f"cp -r {work_dir} {task_context_dir}")
            await sandbox.commands.run(
                f"if [ -d {work_dir}/artifact ]; then cp -r {work_dir}/artifact/* {artifact_dir}; fi"
            )

            artifact_exec = await sandbox.commands.run(
                f"if [ -d {artifact_dir} ]; then ls -1 {artifact_dir}; fi"
            )
            artifacts = [
                msg.text.strip()
                for msg in artifact_exec.logs.stdout
                if msg.text.strip()
            ]

            success = run_exec.error is None
            message = "任务执行成功" if success else "任务执行失败"

            await sandbox.kill()

        return SandboxResult(
            success=success, message=message, logs=logs, artifacts=artifacts
        )

    async def stream_task(
        self, session_id: str, prompt: str, skills: list[str], mcps: list[str]
    ) -> tuple[AsyncGenerator[str, None], asyncio.Future[SandboxResult]]:
        """流式执行任务，实时输出日志。"""

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        result_future: asyncio.Future[SandboxResult] = (
            asyncio.get_running_loop().create_future()
        )

        asyncio.create_task(
            self._execute_task(
                session_id=session_id,
                prompt=prompt,
                skills=skills,
                mcps=mcps,
                queue=queue,
                result_future=result_future,
            )
        )

        async def generator() -> AsyncGenerator[str, None]:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item

        return generator(), result_future

    async def _execute_task(
        self,
        session_id: str,
        prompt: str,
        skills: list[str],
        mcps: list[str],
        queue: asyncio.Queue[str | None],
        result_future: asyncio.Future[SandboxResult],
    ) -> None:
        """实际执行任务并将日志写入队列。"""

        logs: list[str] = []
        artifacts: list[str] = []
        success = False
        message = ""
        sandbox = None
        try:
            env = self._build_env()
            sandbox = await Sandbox.create(
                settings.sandbox_image,
                connection_config=self._config,
                env=env,
                entrypoint=settings.sandbox_entrypoint,
            )

            async with sandbox:
                work_dir = f"/data/context/{session_id}/work"
                artifact_dir = f"/data/context/{session_id}/artifact"
                task_context_dir = f"/data/context/{session_id}/task-context"

                await sandbox.commands.run(f"mkdir -p {work_dir} {artifact_dir}")

                await self._validate_skills(sandbox, skills)
                await self._validate_mcps(sandbox, mcps)

                install_handlers = self._build_handlers("install", logs, queue)
                await sandbox.commands.run(
                    "npm i -g @anthropic-ai/claude-code@latest",
                    handlers=install_handlers,
                )

                run_handlers = self._build_handlers("run", logs, queue)
                run_exec = await sandbox.commands.run(
                    f"claude {json.dumps(prompt)}",
                    opts=RunCommandOpts(working_directory=work_dir),
                    handlers=run_handlers,
                )

                await sandbox.commands.run(f"mkdir -p {task_context_dir}")
                await sandbox.commands.run(f"cp -r {work_dir} {task_context_dir}")
                await sandbox.commands.run(
                    f"if [ -d {work_dir}/artifact ]; then cp -r {work_dir}/artifact/* {artifact_dir}; fi"
                )

                artifact_exec = await sandbox.commands.run(
                    f"if [ -d {artifact_dir} ]; then ls -1 {artifact_dir}; fi"
                )
                artifacts = [
                    msg.text.strip()
                    for msg in artifact_exec.logs.stdout
                    if msg.text.strip()
                ]

                if artifacts:
                    await self._queue_line(queue, logs, "产出文件:")
                    for item in artifacts:
                        download_url = f"{settings.base_download_url}/{item}"
                        await self._queue_line(queue, logs, download_url)

                success = run_exec.error is None
                message = "任务执行成功" if success else "任务执行失败"
        except Exception as exc:  # noqa: BLE001
            message = f"任务执行失败: {exc}"
            await self._queue_line(queue, logs, message)
        finally:
            if sandbox is not None:
                await sandbox.kill()
            result_future.set_result(
                SandboxResult(
                    success=success,
                    message=message,
                    logs=logs,
                    artifacts=artifacts,
                )
            )
            await queue.put(None)

    async def _validate_skills(self, sandbox: Sandbox, skills: list[str]) -> None:
        """验证沙盒中的技能是否存在。"""

        exec_result = await sandbox.commands.run(f"ls -1 {settings.skills_path}")
        available = {msg.text.strip() for msg in exec_result.logs.stdout}
        missing = [skill for skill in skills if skill not in available]
        if missing:
            raise RuntimeError(f"技能不存在: {', '.join(missing)}")

    async def _validate_mcps(self, sandbox: Sandbox, mcps: list[str]) -> None:
        """验证沙盒中的 MCP 是否存在。"""

        cmd = (
            "python - <<'PY'\n"
            "import json\n"
            f"with open('{settings.mcp_config_path}', 'r', encoding='utf-8') as f:\n"
            "    data = json.load(f)\n"
            "print('\n'.join(data.keys()))\n"
            "PY"
        )
        exec_result = await sandbox.commands.run(cmd)
        available = {msg.text.strip() for msg in exec_result.logs.stdout}
        missing = [mcp for mcp in mcps if mcp not in available]
        if missing:
            raise RuntimeError(f"MCP 不存在: {', '.join(missing)}")

    def _format_logs(self, prefix: str, execution) -> list[str]:
        """格式化执行日志。"""

        formatted: list[str] = []
        for msg in execution.logs.stdout:
            formatted.append(f"[{prefix}][stdout] {msg.text}")
        for msg in execution.logs.stderr:
            formatted.append(f"[{prefix}][stderr] {msg.text}")
        if execution.error:
            formatted.append(
                f"[{prefix}][error] {execution.error.name}: {execution.error.value}"
            )
        return formatted

    def _build_env(self) -> dict[str, str]:
        """构建沙盒环境变量。"""

        env = {
            "ANTHROPIC_AUTH_TOKEN": settings.claude_auth_token,
            "ANTHROPIC_BASE_URL": settings.claude_base_url,
            "ANTHROPIC_MODEL": settings.claude_model,
            "IS_SANDBOX": "1",
            **settings.runtime_env,
        }
        return {key: value for key, value in env.items() if value is not None}

    def _build_handlers(
        self, prefix: str, logs: list[str], queue: asyncio.Queue[str | None]
    ) -> ExecutionHandlers:
        """构建执行日志处理器。"""

        async def on_stdout(msg) -> None:  # type: ignore[no-untyped-def]
            await self._queue_line(queue, logs, f"[{prefix}][stdout] {msg.text}")

        async def on_stderr(msg) -> None:  # type: ignore[no-untyped-def]
            await self._queue_line(queue, logs, f"[{prefix}][stderr] {msg.text}")

        async def on_error(err) -> None:  # type: ignore[no-untyped-def]
            await self._queue_line(
                queue, logs, f"[{prefix}][error] {getattr(err, 'message', err)}"
            )

        return ExecutionHandlers(
            on_stdout=on_stdout,
            on_stderr=on_stderr,
            on_error=on_error,
        )

    async def _queue_line(
        self,
        queue: asyncio.Queue[str | None],
        logs: list[str],
        line: str,
    ) -> None:
        """将日志写入队列与缓存。"""

        logs.append(line)
        await queue.put(line)
