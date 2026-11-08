-- Additive migration: existing inspections remain unchanged.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_inspection_item (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  inspection_id BIGINT NOT NULL,
  item_name VARCHAR(120) NOT NULL,
  result VARCHAR(16) NOT NULL,
  remark VARCHAR(500) NOT NULL DEFAULT '',
  KEY idx_inspection_item (inspection_id,id),
  CONSTRAINT chk_inspection_item_result CHECK (result IN ('NORMAL','ABNORMAL')),
  CONSTRAINT fk_inspection_item_inspection FOREIGN KEY (inspection_id) REFERENCES ems_inspection(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
