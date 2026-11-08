-- Disable only matching built-in framework menu routes; retain rows and child permissions for rollback.
-- Existing installations: back up sys_menu and review exact matches before applying.
UPDATE sys_menu SET visible='1',status='1' WHERE parent_id=0 AND ((menu_id=2 AND BINARY path='monitor') OR (menu_id=3 AND BINARY path='tool') OR (menu_id=4 AND BINARY path='http://ruoyi.vip'));
UPDATE sys_menu SET visible='1',status='1' WHERE parent_id=1 AND ((menu_id=104 AND BINARY path='post') OR (menu_id=105 AND BINARY path='dict') OR (menu_id=106 AND BINARY path='config') OR (menu_id=107 AND BINARY path='notice'));
-- Rename only the untouched built-in administrator nickname, leaving custom names intact.
UPDATE sys_user SET nick_name=CONVERT(0xE7B3BBE7BB9FE7AEA1E79086E59198 USING utf8mb4)
WHERE user_id=1 AND BINARY user_name='admin' AND BINARY nick_name=0xE88BA5E4BE9D;
