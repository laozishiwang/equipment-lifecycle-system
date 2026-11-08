-- 业务模型草稿，尚未经过集成验证。
CREATE TABLE IF NOT EXISTS ems_equipment (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 code VARCHAR(64) NOT NULL UNIQUE,
 name VARCHAR(128) NOT NULL,
 model VARCHAR(128), location VARCHAR(255),
 status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_inspection (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 equipment_id BIGINT NOT NULL, inspector_id BIGINT NOT NULL,
 inspected_at DATETIME NOT NULL, result VARCHAR(32) NOT NULL, remark VARCHAR(1000),
 FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_work_order (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 equipment_id BIGINT NOT NULL, inspection_id BIGINT,
 reporter_id BIGINT NOT NULL, technician_id BIGINT,
 description VARCHAR(2000) NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'REPORTED',
 repair_description VARCHAR(2000), repair_date DATE,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id),
 FOREIGN KEY (inspection_id) REFERENCES ems_inspection(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 总额由费用明细汇总。
CREATE TABLE IF NOT EXISTS ems_repair_cost (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 work_order_id BIGINT NOT NULL,
 category VARCHAR(16) NOT NULL,
 description VARCHAR(255) NOT NULL,
 amount DECIMAL(12,2) NOT NULL,
 CONSTRAINT chk_cost_category CHECK (category IN ('LABOR','PARTS','OTHER')),
 CONSTRAINT chk_cost_amount CHECK (amount >= 0),
 KEY idx_cost_order (work_order_id),
 CONSTRAINT fk_cost_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

