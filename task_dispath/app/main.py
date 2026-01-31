from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from task_dispath.app.core.database import SessionLocal
from task_dispath.app.schemas.task import TaskRequest, TaskResponse
from task_dispath.app.services.sandbox_service import SandboxService
from task_dispath.app.services.task_service import (
    append_log,
    create_artifacts,
    create_task_record,
    finish_task_record,
)
from task_dispath.app.core.config import settings

app = FastAPI(title="Task Dispatch Service")


def get_db() -> Session:
    """获取数据库会话。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""

    return {"status": "ok"}


@app.post("/tasks/claude", response_model=TaskResponse)
async def create_task(
    payload: TaskRequest, db: Session = Depends(get_db)
) -> TaskResponse:
    """创建任务记录并返回任务信息。"""

    if not payload.session_id.strip() or not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="session_id 和 prompt 必填")
    if not payload.skills:
        raise HTTPException(status_code=400, detail="必须选择 skills")
    if not payload.mcps:
        raise HTTPException(status_code=400, detail="必须选择 mcps")

    skills = list(dict.fromkeys(settings.default_skills + payload.skills))
    mcps = list(dict.fromkeys(settings.default_mcps + payload.mcps))

    record = create_task_record(
        db,
        session_id=payload.session_id,
        prompt=payload.prompt,
        skills=skills,
        mcps=mcps,
    )

    return TaskResponse(task_id=record.id, session_id=record.session_id, status=record.status)


@app.post("/tasks/claude/{task_id}/stream")
async def stream_task(
    task_id: str,
    payload: TaskRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """执行任务并流式输出日志。"""

    if not payload.session_id.strip() or not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="session_id 和 prompt 必填")
    if not payload.skills:
        raise HTTPException(status_code=400, detail="必须选择 skills")
    if not payload.mcps:
        raise HTTPException(status_code=400, detail="必须选择 mcps")

    skills = list(dict.fromkeys(settings.default_skills + payload.skills))
    mcps = list(dict.fromkeys(settings.default_mcps + payload.mcps))
    sandbox_service = SandboxService()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        logs: list[str] = []
        stream_generator, result_future = await sandbox_service.stream_task(
            payload.session_id, payload.prompt, skills, mcps
        )
        async for line in stream_generator:
            logs.append(line)
            append_log(db, task_id, "stdout", line)
            yield f"{line}\n".encode("utf-8")

        result = await result_future
        artifacts = [
            line.replace(f"{settings.base_download_url}/", "")
            for line in logs
            if line.startswith(settings.base_download_url)
        ]
        finish_task_record(db, task_id, result.success, result.message, artifacts)
        if artifacts:
            create_artifacts(
                db,
                task_id,
                [(path, f"{settings.base_download_url}/{path}") for path in artifacts],
            )

    return StreamingResponse(event_stream(), media_type="text/plain")
