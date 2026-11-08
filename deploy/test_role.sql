INSERT INTO sys_role(role_id,role_name,role_key,role_sort,status) VALUES (9001,'Smoke worker','smoke_worker',1,'0') ON DUPLICATE KEY UPDATE status='0';
INSERT INTO sys_user(user_id,dept_id,user_name,nick_name,password,status) SELECT 9001,100,'smoke_worker','Smoke worker',password,'0' FROM sys_user WHERE user_id=1 ON DUPLICATE KEY UPDATE status='0';
INSERT IGNORE INTO sys_user_role(user_id,role_id) VALUES (9001,9001);
INSERT IGNORE INTO sys_role_menu(role_id,menu_id) SELECT 9001,menu_id FROM sys_menu WHERE perms='equipment:order:report';
