INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,`query`,route_name,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time,remark)
SELECT '通知管理',0,4,'notification',NULL,'','',1,0,'M','0','0','','message','admin',NOW(),'通知渠道配置'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=0 AND path='notification');
SET @notification_menu_id = (SELECT menu_id FROM sys_menu WHERE parent_id=0 AND path='notification' LIMIT 1);
INSERT IGNORE INTO sys_role_menu(role_id,menu_id) SELECT role_id,@notification_menu_id FROM sys_role_menu WHERE menu_id IN (SELECT menu_id FROM sys_menu WHERE parent_id=2 AND path='dingtalk');
UPDATE sys_menu SET parent_id=@notification_menu_id,order_num=1 WHERE parent_id=2 AND path='dingtalk';
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,`query`,route_name,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time,remark)
SELECT '邮箱通知',@notification_menu_id,2,'email','monitor/email/index','','',1,0,'C','0','0','monitor:email:config','email','admin',NOW(),'邮箱通知配置'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=@notification_menu_id AND path='email');
