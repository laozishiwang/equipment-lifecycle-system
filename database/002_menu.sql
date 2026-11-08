-- 在若依系统表导入后执行；首次安装用，重复执行前请核对菜单。
INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
SELECT '设备管理', 0, 90, 'equipment', NULL, 1, 0, 'M', '0', '0', '', 'component', 'admin', NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=0 AND path='equipment');
SET @ems_parent = (SELECT menu_id FROM sys_menu WHERE parent_id=0 AND path='equipment' LIMIT 1);
INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
SELECT '设备台账', @ems_parent, 1, 'assets', 'equipment/assets/index', 1, 0, 'C', '0', '0', 'equipment:asset:list', 'list', 'admin', NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=@ems_parent AND path='assets');
SET @ems_asset = (SELECT menu_id FROM sys_menu WHERE parent_id=@ems_parent AND path='assets' LIMIT 1);
INSERT INTO sys_menu (menu_name, parent_id, order_num, path, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
SELECT '设备新增', @ems_asset, 1, '', 1, 0, 'F', '0', '0', 'equipment:asset:add', '#', 'admin', NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:asset:add');
INSERT INTO sys_menu (menu_name, parent_id, order_num, path, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
SELECT '设备查询', @ems_asset, 2, '', 1, 0, 'F', '0', '0', 'equipment:asset:query', '#', 'admin', NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:asset:query');
-- 工单权限需在若依角色管理中按职责授权。
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT x.name,@ems_asset,x.sort,'',1,0,'F','0','0',x.perms,'#','admin',NOW()
FROM (SELECT '工单列表' name,10 sort,'equipment:order:list' perms UNION ALL
 SELECT '提交报修',11,'equipment:order:report' UNION ALL
 SELECT '维修接单',12,'equipment:order:accept' UNION ALL
 SELECT '维修完工',13,'equipment:order:complete' UNION ALL
 SELECT '确认关闭',14,'equipment:order:close') x
WHERE NOT EXISTS (SELECT 1 FROM sys_menu m WHERE m.perms=x.perms);
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '维修工单',@ems_parent,2,'orders','equipment/orders/index',1,0,'C','0','0','equipment:order:list','list','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=@ems_parent AND path='orders');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT x.name,@ems_asset,x.sort,'',1,0,'F','0','0',x.perms,'#','admin',NOW()
FROM (SELECT '巡检列表' name,20 sort,'equipment:inspection:list' perms UNION ALL SELECT '提交巡检',21,'equipment:inspection:add') x
WHERE NOT EXISTS (SELECT 1 FROM sys_menu m WHERE m.perms=x.perms);
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '设备巡检',@ems_parent,3,'inspections','equipment/inspections/index',1,0,'C','0','0','equipment:inspection:list','list','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=@ems_parent AND path='inspections');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '设备履历',@ems_asset,3,'',1,0,'F','0','0','equipment:asset:history','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:asset:history');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '设备编辑',@ems_asset,4,'',1,0,'F','0','0','equipment:asset:edit','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:asset:edit');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '查看全部工单',@ems_asset,15,'',1,0,'F','0','0','equipment:order:viewAll','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:order:viewAll');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '查看全部巡检',@ems_asset,22,'',1,0,'F','0','0','equipment:inspection:viewAll','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:inspection:viewAll');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '保养计划',@ems_parent,4,'maintenance','equipment/maintenance/index',1,0,'C','0','0','equipment:maintenance:list','list','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=@ems_parent AND path='maintenance');
SET @ems_maintenance = (SELECT menu_id FROM sys_menu WHERE parent_id=@ems_parent AND path='maintenance' LIMIT 1);
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT x.name,@ems_maintenance,x.sort,'',1,0,'F','0','0',x.perms,'#','admin',NOW()
FROM (SELECT '新建保养计划' name,1 sort,'equipment:maintenance:add' perms UNION ALL SELECT '完成保养',2,'equipment:maintenance:complete') x
WHERE NOT EXISTS (SELECT 1 FROM sys_menu m WHERE m.perms=x.perms);
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '编辑保养计划',@ems_maintenance,3,'',1,0,'F','0','0','equipment:maintenance:edit','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:maintenance:edit');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '取消工单',@ems_asset,16,'',1,0,'F','0','0','equipment:order:cancel','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:order:cancel');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '转派工单',@ems_asset,17,'',1,0,'F','0','0','equipment:order:assign','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:order:assign');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '维修到场',@ems_asset,18,'',1,0,'F','0','0','equipment:order:arrive','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:order:arrive');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '工单试运行',@ems_asset,19,'',1,0,'F','0','0','equipment:order:trial','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:order:trial');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time)
SELECT '上传工单照片',@ems_asset,20,'',1,0,'F','0','0','equipment:order:photo','#','admin',NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='equipment:order:photo');
