from pydantic import BaseModel, Field


class Settings(BaseModel):
    """服务配置。"""

    mysql_dsn: str = "mysql+pymysql://sandbox:sandbox@localhost:3306/sandbox"
    sandbox_domain: str = "localhost:8080"
    sandbox_api_key: str | None = None
    sandbox_image: str = (
        "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.1"
    )
    default_skills: list[str] = Field(
        default_factory=lambda: ["ppt", "excel", "zip", "browse_user"]
    )
    default_mcps: list[str] = Field(default_factory=lambda: ["tapd"])
    mcp_config_path: str = "/data/all_mcp.json"
    skills_path: str = "/data/skills"
    base_download_url: str = "https://base-api/download"
    claude_auth_token: str | None = None
    claude_base_url: str | None = None
    claude_model: str = "claude_sonnet4"
    sandbox_entrypoint: list[str] = Field(
        default_factory=lambda: ["/opt/opensandbox/code-interpreter.sh"]
    )
    runtime_env: dict[str, str] = Field(
        default_factory=lambda: {
            "PYTHON_VERSION": "3.11",
            "JAVA_VERSION": "17",
            "NODE_VERSION": "20",
            "GO_VERSION": "1.24",
        }
    )


settings = Settings()
