-- Additive table; binary data lives in the existing private upload volume.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_inspection_photo (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 inspection_id BIGINT NOT NULL,
 stored_name VARCHAR(80) NOT NULL,
 media_type VARCHAR(32) NOT NULL,
 file_size INT NOT NULL,
 uploaded_by BIGINT NOT NULL,
 uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uk_inspection_photo_name (stored_name),
 KEY idx_inspection_photo_record (inspection_id,id),
 CONSTRAINT fk_inspection_photo_record FOREIGN KEY (inspection_id) REFERENCES ems_inspection(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
