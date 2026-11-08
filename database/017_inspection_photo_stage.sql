-- Additive anomaly-photo rule and staged upload metadata.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_inspection_photo_rule (
 template_id BIGINT NOT NULL PRIMARY KEY,
 require_abnormal_photo TINYINT NOT NULL DEFAULT 0,
 CONSTRAINT chk_inspection_photo_required CHECK (require_abnormal_photo IN (0,1)),
 CONSTRAINT fk_inspection_photo_rule_template FOREIGN KEY (template_id) REFERENCES ems_inspection_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_inspection_photo_stage (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 equipment_id BIGINT NOT NULL,
 uploaded_by BIGINT NOT NULL,
 stored_name VARCHAR(80) NOT NULL,
 media_type VARCHAR(32) NOT NULL,
 file_size INT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 expires_at DATETIME NOT NULL,
 inspection_id BIGINT NULL,
 UNIQUE KEY uk_inspection_stage_name (stored_name),
 KEY idx_inspection_stage_expiry (expires_at,id),
 CONSTRAINT fk_inspection_stage_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id),
 CONSTRAINT fk_inspection_stage_record FOREIGN KEY (inspection_id) REFERENCES ems_inspection(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
