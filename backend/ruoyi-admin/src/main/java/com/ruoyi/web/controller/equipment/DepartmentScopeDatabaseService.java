package com.ruoyi.web.controller.equipment;

import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.ruoyi.common.utils.SecurityUtils;

/** Trusted scope source for future endpoint integration. Not an authorization interceptor. */
@Service
public class DepartmentScopeDatabaseService {
    private final JdbcTemplate jdbc;
    public DepartmentScopeDatabaseService(JdbcTemplate jdbc) { this.jdbc=jdbc; }

    /** action is a server-defined permission constant, never a request parameter. */
    @Transactional(readOnly=true)
    public DepartmentScopeResolver.Result currentScope(String action) {
        return resolveUser(SecurityUtils.getUserId(), action);
    }

    // Package-private for isolated contract tests; application callers must use currentScope.
    DepartmentScopeResolver.Result resolveUser(long userId, String action) {
        if (userId <= 0 || action == null || !action.matches("[a-zA-Z0-9:_-]{1,100}"))
            throw new IllegalArgumentException("Invalid user or permission");
        var users=jdbc.queryForList("SELECT dept_id FROM sys_user WHERE user_id=? AND status='0' AND del_flag='0'", userId);
        if (users.size()!=1) return new DepartmentScopeResolver.Result(false,false,Set.of(),false);
        if (userId==1) return new DepartmentScopeResolver.Result(true,true,Set.of(),true);
        Object department=users.get(0).get("dept_id");
        Long userDept=department == null ? null : ((Number)department).longValue();
        var departmentRows=jdbc.queryForList("SELECT dept_id,parent_id FROM sys_dept WHERE status='0' AND del_flag='0'");
        Set<Long> enabled=new HashSet<>(); Map<Long,Set<Long>> children=new HashMap<>();
        for (var row:departmentRows) {
            long id=((Number)row.get("dept_id")).longValue();
            Object parent=row.get("parent_id"); enabled.add(id);
            if (parent!=null) children.computeIfAbsent(((Number)parent).longValue(),k->new HashSet<>()).add(id);
        }
        Set<Long> descendants=new HashSet<>();
        if (userDept!=null && enabled.contains(userDept)) {
            Deque<Long> queue=new ArrayDeque<>(); queue.add(userDept);
            while (!queue.isEmpty()) for (Long id:children.getOrDefault(queue.remove(),Set.of()))
                if (!id.equals(userDept) && descendants.add(id)) queue.add(id);
        }
        var roleRows=jdbc.queryForList("SELECT DISTINCT r.role_id,r.data_scope FROM sys_user_role ur JOIN sys_role r ON r.role_id=ur.role_id JOIN sys_role_menu rm ON rm.role_id=r.role_id JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE ur.user_id=? AND r.status='0' AND r.del_flag='0' AND m.status='0' AND BINARY m.perms=BINARY ?",userId,action);
        List<DepartmentScopeResolver.Role> roles=new ArrayList<>();
        for (var role:roleRows) {
            String scope=(String)role.get("data_scope"); Set<Long> custom=new HashSet<>();
            if ("2".equals(scope)) for (var row:jdbc.queryForList("SELECT dept_id FROM sys_role_dept WHERE role_id=?",((Number)role.get("role_id")).longValue()))
                custom.add(((Number)row.get("dept_id")).longValue());
            roles.add(new DepartmentScopeResolver.Role(scope,true,custom));
        }
        Map<Long,Set<Long>> tree=userDept==null ? Map.of() : Map.of(userDept,descendants);
        return DepartmentScopeResolver.resolve(new DepartmentScopeResolver.Input(false,userDept,enabled,tree,roles));
    }
}
