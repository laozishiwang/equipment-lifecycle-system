-- Restore only the original system-monitor root menu; existing children and role assignments remain unchanged.
UPDATE sys_menu SET visible='0', status='0'
WHERE menu_id=2 AND parent_id=0 AND BINARY path='monitor' AND menu_type='M';
