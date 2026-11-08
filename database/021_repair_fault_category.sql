-- Optional category per repair; existing repairs remain unchanged.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_repair_fault_category (
 repair_id BIGINT NOT NULL PRIMARY KEY,
 category VARCHAR(32) NOT NULL,
 CONSTRAINT chk_repair_fault_category CHECK (category IN ('MECHANICAL','ELECTRICAL','HYDRAULIC','CONTROL','OTHER')),
 CONSTRAINT fk_repair_fault_category_repair FOREIGN KEY (repair_id) REFERENCES ems_work_order_repair(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
