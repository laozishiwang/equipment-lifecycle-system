CREATE TABLE IF NOT EXISTS ems_work_order_photo (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 work_order_id BIGINT NOT NULL,
 stored_name VARCHAR(80) NOT NULL,
 media_type VARCHAR(32) NOT NULL,
 file_size INT NOT NULL,
 uploaded_by BIGINT NOT NULL,
 uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uk_photo_name (stored_name),
 KEY idx_photo_order (work_order_id,id),
 CONSTRAINT fk_photo_order FOREIGN KEY (work_order_id) REFERENCES ems_work_order(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
