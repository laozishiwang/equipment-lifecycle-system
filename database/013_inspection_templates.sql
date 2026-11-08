-- Additive schema for draft inspection templates. Existing inspection records are untouched.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_inspection_template (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(120) NOT NULL,
 status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
 created_by BIGINT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT chk_inspection_template_status CHECK (status IN ('ACTIVE','INACTIVE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_inspection_template_item (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 template_id BIGINT NOT NULL,
 item_name VARCHAR(120) NOT NULL,
 standard_text VARCHAR(500) NOT NULL DEFAULT '',
 sort_order INT NOT NULL DEFAULT 0,
 KEY idx_inspection_template_item (template_id,sort_order,id),
 CONSTRAINT fk_inspection_template_item FOREIGN KEY (template_id) REFERENCES ems_inspection_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_equipment_inspection_template (
 equipment_id BIGINT NOT NULL PRIMARY KEY,
 template_id BIGINT NOT NULL,
 KEY idx_equipment_inspection_template (template_id),
 CONSTRAINT fk_equipment_inspection_template_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id),
 CONSTRAINT fk_equipment_inspection_template_template FOREIGN KEY (template_id) REFERENCES ems_inspection_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
