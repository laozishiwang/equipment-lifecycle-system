CREATE TABLE IF NOT EXISTS ems_equipment_profile (
 equipment_id BIGINT NOT NULL PRIMARY KEY,
 manufacturer VARCHAR(128),
 serial_number VARCHAR(128),
 purchase_date DATE,
 warranty_until DATE,
 CONSTRAINT fk_profile_equipment FOREIGN KEY (equipment_id) REFERENCES ems_equipment(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
