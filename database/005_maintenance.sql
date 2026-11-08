CREATE TABLE IF NOT EXISTS ems_maintenance_plan (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 equipment_id BIGINT NOT NULL,
 title VARCHAR(128) NOT NULL,
 interval_days INT NOT NULL,
 next_due DATE NOT NULL,
 active TINYINT NOT NULL DEFAULT 1,
 created_by BIGINT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT chk_maintenance_interval CHECK (interval_days BETWEEN 1 AND 3650),
 KEY idx_maintenance_due (active,next_due),
 CONSTRAINT fk_maintenance_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_maintenance_record (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 plan_id BIGINT NOT NULL,
 completed_by BIGINT NOT NULL,
 completed_date DATE NOT NULL,
 notes VARCHAR(2000) NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_maintenance_record_plan (plan_id,id),
 CONSTRAINT fk_maintenance_record_plan FOREIGN KEY (plan_id) REFERENCES ems_maintenance_plan(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
