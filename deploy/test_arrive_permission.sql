INSERT IGNORE INTO sys_role_menu(role_id,menu_id) SELECT 9002,menu_id FROM sys_menu WHERE perms='equipment:order:arrive';
