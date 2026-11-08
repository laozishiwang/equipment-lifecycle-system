CREATE TABLE IF NOT EXISTS ems_equipment_location_history (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 equipment_id BIGINT NOT NULL,
 location VARCHAR(255),
 changed_by BIGINT NOT NULL,
 changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_location_equipment (equipment_id,id),
 CONSTRAINT fk_location_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
