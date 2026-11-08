INSERT INTO sys_role(role_id,role_name,role_key,role_sort,status) VALUES (9002,'Smoke technician','smoke_tech',1,'0') ON DUPLICATE KEY UPDATE status='0';
INSERT INTO sys_user(user_id,dept_id,user_name,nick_name,password,status) SELECT 9002,100,'smoke_tech_a','Smoke tech A',password,'0' FROM sys_user WHERE user_id=1 ON DUPLICATE KEY UPDATE status='0';
INSERT INTO sys_user(user_id,dept_id,user_name,nick_name,password,status) SELECT 9003,100,'smoke_tech_b','Smoke tech B',password,'0' FROM sys_user WHERE user_id=1 ON DUPLICATE KEY UPDATE status='0';
INSERT IGNORE INTO sys_user_role(user_id,role_id) VALUES (9002,9002),(9003,9002);
INSERT IGNORE INTO sys_role_menu(role_id,menu_id) SELECT 9002,menu_id FROM sys_menu WHERE perms IN ('equipment:order:accept','equipment:order:complete');
