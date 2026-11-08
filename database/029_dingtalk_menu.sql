-- 管理员从系统监控进入钉钉通知配置；菜单 ID 自动生成，避免与已有数据冲突。
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,`query`,route_name,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time,remark)
SELECT '钉钉群通知',2,7,'dingtalk','monitor/dingtalk/index','','',1,0,'C','0','0','monitor:dingtalk:config','message','admin',NOW(),'设备报修与维修完成通知'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=2 AND path='dingtalk');
