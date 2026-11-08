CREATE TABLE IF NOT EXISTS ems_work_order_cancellation (
 work_order_id BIGINT NOT NULL PRIMARY KEY,
 cancelled_by BIGINT NOT NULL,
 cancellation_type VARCHAR(16) NOT NULL,
 reason VARCHAR(1000) NOT NULL,
 cancelled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT chk_cancel_type CHECK (cancellation_type IN ('WITHDRAW','ADMIN')),
 CONSTRAINT fk_cancellation_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
