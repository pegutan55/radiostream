CREATE TABLE execution_logs (
    source_id TEXT NOT NULL,
    id INTEGER NOT NULL,
    message TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    PRIMARY KEY (source_id, id)
);

CREATE INDEX execution_logs_executed_at_idx
ON execution_logs (executed_at);