-- 可重复执行的角色模板；不创建用户、不分配账号。部署前须审核职责。
INSERT INTO sys_role(role_name,role_key,role_sort,data_scope,menu_check_strictly,dept_check_strictly,status,del_flag,create_by,create_time)
SELECT '现场工人','ems_worker',10,'3',1,1,'0','0','admin',NOW() WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key='ems_worker');
INSERT INTO sys_role(role_name,role_key,role_sort,data_scope,menu_check_strictly,dept_check_strictly,status,del_flag,create_by,create_time)
SELECT '维修人员','ems_technician',11,'3',1,1,'0','0','admin',NOW() WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key='ems_technician');
INSERT INTO sys_role(role_name,role_key,role_sort,data_scope,menu_check_strictly,dept_check_strictly,status,del_flag,create_by,create_time)
SELECT '设备主任','ems_director',12,'1',1,1,'0','0','admin',NOW() WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key='ems_director');
SET @worker_role=(SELECT role_id FROM sys_role WHERE role_key='ems_worker' LIMIT 1);
SET @tech_role=(SELECT role_id FROM sys_role WHERE role_key='ems_technician' LIMIT 1);
SET @director_role=(SELECT role_id FROM sys_role WHERE role_key='ems_director' LIMIT 1);
SET @equipment_menu=(SELECT menu_id FROM sys_menu WHERE parent_id=0 AND path='equipment' LIMIT 1);
INSERT IGNORE INTO sys_role_menu(role_id,menu_id)
SELECT r.role_id,m.menu_id FROM (SELECT @worker_role role_id UNION ALL SELECT @tech_role UNION ALL SELECT @director_role) r
JOIN sys_menu m ON m.menu_id=@equipment_menu OR m.perms IN ('equipment:asset:list','equipment:asset:query','equipment:order:list','equipment:order:report','equipment:order:photo','equipment:inspection:list','equipment:inspection:add');
INSERT IGNORE INTO sys_role_menu(role_id,menu_id)
SELECT @tech_role,menu_id FROM sys_menu WHERE perms IN ('equipment:order:accept','equipment:order:arrive','equipment:order:complete','equipment:order:trial','equipment:maintenance:list','equipment:maintenance:complete');
INSERT IGNORE INTO sys_role_menu(role_id,menu_id)
SELECT @director_role,menu_id FROM sys_menu WHERE perms LIKE 'equipment:%';



