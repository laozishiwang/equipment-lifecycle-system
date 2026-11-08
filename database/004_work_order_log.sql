CREATE TABLE IF NOT EXISTS ems_work_order_log (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 work_order_id BIGINT NOT NULL,
 from_status VARCHAR(32) NOT NULL,
 to_status VARCHAR(32) NOT NULL,
 operator_id BIGINT NOT NULL,
 operated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_work_order_log (work_order_id,id),
 CONSTRAINT fk_work_order_log_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
