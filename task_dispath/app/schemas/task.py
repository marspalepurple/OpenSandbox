from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """任务请求。"""

    session_id: str = Field(..., description="会话 ID")
    prompt: str = Field(..., description="用户任务内容")
    skills: list[str] | None = Field(default=None, description="选定 skills")
    mcps: list[str] | None = Field(default=None, description="选定 mcps")


class TaskResponse(BaseModel):
    """任务响应。"""

    task_id: str
    session_id: str
    status: str
