# Task Dispatch Service

该目录为独立的任务分发服务（FastAPI），用于在沙盒中运行 `claude-code`，并将任务记录、输出信息写入 MySQL。

## 数据库结构（MySQL）

### `task_records`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | VARCHAR(36) | 任务主键（UUID） |
| session_id | VARCHAR(128) | 会话 ID |
| prompt | TEXT | 用户输入任务 |
| skills | JSON | 选定 skills |
| mcps | JSON | 选定 mcps |
| status | VARCHAR(32) | 任务状态（running/success/failed） |
| started_at | DATETIME | 任务开始时间 |
| finished_at | DATETIME | 任务结束时间 |
| success | BOOLEAN | 是否成功 |
| message | TEXT | 任务结果描述 |
| output_files | JSON | 输出文件列表 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### `task_logs`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT | 主键 |
| task_id | VARCHAR(36) | 任务 ID |
| stream | VARCHAR(16) | stdout/stderr/system |
| content | TEXT | 日志内容 |
| created_at | DATETIME | 日志时间 |

### `task_artifacts`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT | 主键 |
| task_id | VARCHAR(36) | 任务 ID |
| file_path | VARCHAR(512) | 沙盒内文件路径 |
| download_url | VARCHAR(512) | 对外下载地址 |
| created_at | DATETIME | 记录时间 |

## 代码结构

```
app/
  main.py                # FastAPI 入口
  core/
    config.py            # 配置
    database.py          # 数据库连接
  models/
    task.py              # SQLAlchemy 模型
  schemas/
    task.py              # 请求/响应模型
  services/
    sandbox_service.py   # 沙盒执行逻辑
    task_service.py      # 任务记录与状态维护
  utils/
    streaming.py         # 流式输出工具
```

## 启动方式

```bash
uvicorn task_dispath.app.main:app --host 0.0.0.0 --port 8000
```
