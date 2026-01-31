import datetime
import uuid

from sqlalchemy.orm import Session

from task_dispath.app.models.task import TaskArtifact, TaskLog, TaskRecord


def create_task_record(
    session: Session,
    session_id: str,
    prompt: str,
    skills: list[str],
    mcps: list[str],
) -> TaskRecord:
    """创建任务记录。"""

    task_id = str(uuid.uuid4())
    record = TaskRecord(
        id=task_id,
        session_id=session_id,
        prompt=prompt,
        skills=skills,
        mcps=mcps,
        status="running",
        started_at=datetime.datetime.utcnow(),
    )
    session.add(record)
    session.commit()
    return record


def append_log(session: Session, task_id: str, stream: str, content: str) -> None:
    """追加任务日志。"""

    log = TaskLog(task_id=task_id, stream=stream, content=content)
    session.add(log)
    session.commit()


def finish_task_record(
    session: Session,
    task_id: str,
    success: bool,
    message: str,
    output_files: list[str],
) -> None:
    """更新任务完成状态。"""

    record = session.get(TaskRecord, task_id)
    if not record:
        return
    record.status = "success" if success else "failed"
    record.success = success
    record.message = message
    record.output_files = output_files
    record.finished_at = datetime.datetime.utcnow()
    session.add(record)
    session.commit()


def create_artifacts(
    session: Session, task_id: str, artifacts: list[tuple[str, str]]
) -> None:
    """写入任务产出。"""

    for file_path, download_url in artifacts:
        session.add(
            TaskArtifact(task_id=task_id, file_path=file_path, download_url=download_url)
        )
    session.commit()
