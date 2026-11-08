CREATE TABLE IF NOT EXISTS ems_work_order_assignment (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 work_order_id BIGINT NOT NULL,
 from_user_id BIGINT NOT NULL,
 to_user_id BIGINT NOT NULL,
 operator_id BIGINT NOT NULL,
 reason VARCHAR(1000) NOT NULL,
 assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_assignment_order (work_order_id,id),
 CONSTRAINT fk_assignment_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
