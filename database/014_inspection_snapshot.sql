SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_inspection_template_snapshot (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 inspection_id BIGINT NOT NULL,
 template_id BIGINT NOT NULL,
 template_name VARCHAR(120) NOT NULL,
 item_order INT NOT NULL,
 item_name VARCHAR(120) NOT NULL,
 standard_text VARCHAR(500) NOT NULL DEFAULT '',
 UNIQUE KEY uk_inspection_snapshot_order (inspection_id,item_order),
 CONSTRAINT fk_inspection_snapshot_record FOREIGN KEY (inspection_id) REFERENCES ems_inspection(id),
 CONSTRAINT fk_inspection_snapshot_template FOREIGN KEY (template_id) REFERENCES ems_inspection_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
