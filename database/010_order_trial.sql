CREATE TABLE IF NOT EXISTS ems_work_order_repair (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 work_order_id BIGINT NOT NULL,
 technician_id BIGINT NOT NULL,
 repair_date DATE NOT NULL,
 description VARCHAR(2000) NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_repair_order (work_order_id,id),
 CONSTRAINT fk_repair_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_work_order_trial (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 work_order_id BIGINT NOT NULL,
 technician_id BIGINT NOT NULL,
 result VARCHAR(16) NOT NULL,
 notes VARCHAR(1000),
 tested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_trial_order (work_order_id,id),
 CONSTRAINT chk_trial_result CHECK (result IN ('PASS','FAIL')),
 CONSTRAINT fk_trial_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
