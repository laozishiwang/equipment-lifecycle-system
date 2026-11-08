-- Optional ownership metadata only; it does not enforce department access control.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_equipment_department (
 equipment_id BIGINT NOT NULL PRIMARY KEY,
 dept_id BIGINT NOT NULL,
 KEY idx_equipment_department_dept (dept_id),
 CONSTRAINT fk_equipment_department_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id),
 CONSTRAINT fk_equipment_department_dept FOREIGN KEY (dept_id) REFERENCES sys_dept(dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_equipment_department_history (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 equipment_id BIGINT NOT NULL,
 old_dept_id BIGINT NULL,
 old_dept_name VARCHAR(30) NULL,
 new_dept_id BIGINT NULL,
 new_dept_name VARCHAR(30) NULL,
 changed_by BIGINT NOT NULL,
 changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_equipment_department_history (equipment_id,id),
 CONSTRAINT fk_equipment_department_history_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
