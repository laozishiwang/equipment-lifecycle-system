-- Associate newly recorded costs with their repair; legacy costs remain unassigned.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_repair_cost_link (
 cost_id BIGINT NOT NULL PRIMARY KEY,
 repair_id BIGINT NOT NULL,
 KEY idx_repair_cost_link_repair (repair_id),
 CONSTRAINT fk_repair_cost_link_cost FOREIGN KEY (cost_id) REFERENCES ems_repair_cost(id),
 CONSTRAINT fk_repair_cost_link_repair FOREIGN KEY (repair_id) REFERENCES ems_work_order_repair(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
