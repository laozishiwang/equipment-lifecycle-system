-- MySQL 8: abort promptly if a metadata lock cannot be obtained.
SET SESSION lock_wait_timeout=5;
ALTER TABLE ems_inspection ADD COLUMN inspector_name VARCHAR(50) DEFAULT NULL, ALGORITHM=INSTANT;
ALTER TABLE ems_work_order ADD COLUMN reporter_name VARCHAR(50) DEFAULT NULL, ALGORITHM=INSTANT;
INSERT INTO sys_user(user_name,nick_name,status,del_flag,remark) SELECT 'ems_field_guest','现场扫码','1','0','禁止登录，仅作匿名现场记录归属' WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE user_name='ems_field_guest');
ALTER TABLE ems_inspection_photo_stage ADD COLUMN public_token CHAR(36) DEFAULT NULL, ALGORITHM=INSTANT;
ALTER TABLE ems_inspection_photo_stage ADD UNIQUE KEY uk_inspection_stage_public_token(public_token), ALGORITHM=INPLACE, LOCK=NONE;
