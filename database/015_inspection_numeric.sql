-- Additive numeric inspection data. Existing template and inspection rows remain unchanged.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_inspection_numeric_rule (
 template_item_id BIGINT NOT NULL PRIMARY KEY,
 lower_bound DECIMAL(13,4) NULL,
 upper_bound DECIMAL(13,4) NULL,
 unit VARCHAR(32) NOT NULL DEFAULT '',
 CONSTRAINT chk_numeric_rule_bounds CHECK ((lower_bound IS NOT NULL OR upper_bound IS NOT NULL) AND (lower_bound IS NULL OR upper_bound IS NULL OR lower_bound<=upper_bound)),
 CONSTRAINT fk_numeric_rule_item FOREIGN KEY (template_item_id) REFERENCES ems_inspection_template_item(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ems_inspection_numeric_observation (
 inspection_item_id BIGINT NOT NULL PRIMARY KEY,
 measured_value DECIMAL(13,4) NOT NULL,
 lower_bound DECIMAL(13,4) NULL,
 upper_bound DECIMAL(13,4) NULL,
 unit VARCHAR(32) NOT NULL DEFAULT '',
 CONSTRAINT fk_numeric_observation_item FOREIGN KEY (inspection_item_id) REFERENCES ems_inspection_item(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
