INSERT INTO sys_user(user_id,dept_id,user_name,nick_name,password,status) SELECT 9010,100,'role_worker_test','Role worker',password,'0' FROM sys_user WHERE user_id=1 ON DUPLICATE KEY UPDATE status='0';
INSERT INTO sys_user(user_id,dept_id,user_name,nick_name,password,status) SELECT 9011,100,'role_tech_test','Role tech',password,'0' FROM sys_user WHERE user_id=1 ON DUPLICATE KEY UPDATE status='0';
INSERT INTO sys_user(user_id,dept_id,user_name,nick_name,password,status) SELECT 9012,100,'role_director_test','Role director',password,'0' FROM sys_user WHERE user_id=1 ON DUPLICATE KEY UPDATE status='0';
INSERT IGNORE INTO sys_user_role(user_id,role_id) SELECT 9010,role_id FROM sys_role WHERE role_key='ems_worker';
INSERT IGNORE INTO sys_user_role(user_id,role_id) SELECT 9011,role_id FROM sys_role WHERE role_key='ems_technician';
INSERT IGNORE INTO sys_user_role(user_id,role_id) SELECT 9012,role_id FROM sys_role WHERE role_key='ems_director';
