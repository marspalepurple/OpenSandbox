-- 任务记录表
CREATE TABLE IF NOT EXISTS task_records (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    prompt TEXT NOT NULL,
    skills JSON NOT NULL,
    mcps JSON NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    success BOOLEAN NULL,
    message TEXT NULL,
    output_files JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_records_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务日志表
CREATE TABLE IF NOT EXISTS task_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    stream VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_logs_task_id (task_id),
    CONSTRAINT fk_task_logs_task_id FOREIGN KEY (task_id) REFERENCES task_records(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务产出表
CREATE TABLE IF NOT EXISTS task_artifacts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    download_url VARCHAR(512) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_artifacts_task_id (task_id),
    CONSTRAINT fk_task_artifacts_task_id FOREIGN KEY (task_id) REFERENCES task_records(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
