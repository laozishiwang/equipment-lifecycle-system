-- Three-level fault code catalog. No seed values are assumed to be factory-approved.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_fault_code (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 code VARCHAR(64) NOT NULL,
 category VARCHAR(80) NOT NULL,
 part VARCHAR(80) NOT NULL,
 symptom VARCHAR(80) NOT NULL,
 status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
 created_by BIGINT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_by BIGINT NULL,
 updated_at DATETIME NULL,
 UNIQUE KEY uk_fault_code (code),
 UNIQUE KEY uk_fault_code_description (category,part,symptom),
 KEY idx_fault_code_status_id (status,id),
 CONSTRAINT chk_fault_code_status CHECK (status IN ('ACTIVE','INACTIVE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
