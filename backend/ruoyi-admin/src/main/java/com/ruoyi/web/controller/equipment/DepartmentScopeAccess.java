package com.ruoyi.web.controller.equipment;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import com.ruoyi.common.utils.SecurityUtils;

/** Shared, opt-in scope adapter. Partial integrations must never be enabled. */
@Service
public class DepartmentScopeAccess {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeDatabaseService database;
    private final boolean enabled;
    @Value("${equipment.department-scope.experimental:false}")
    private boolean experimental;
    public DepartmentScopeAccess(JdbcTemplate jdbc, DepartmentScopeDatabaseService database,
            @Value("${equipment.department-scope.enabled:false}") boolean enabled) {
        this.jdbc=jdbc; this.database=database; this.enabled=enabled;
    }
    public record Scope(long userId, boolean administrator, boolean allDepartments,
                        boolean selfOnlyGranted, Set<Long> departmentIds, boolean actionGranted) {
        public Scope {
            if (userId <= 0 || departmentIds == null || departmentIds.stream().anyMatch(id -> id == null || id <= 0))
                throw new IllegalArgumentException("Invalid scope");
            departmentIds=Set.copyOf(departmentIds);
        }
    }
    @jakarta.annotation.PostConstruct
    void rejectIncompleteRollout() {
        if (enabled && !experimental) throw new IllegalStateException("Department scope is incomplete; do not enable outside isolated tests");
    }
    public boolean enabled() { return enabled; }
    public Scope current(String action) {
        long userId=SecurityUtils.getUserId();
        var resolved=database.currentScope(action);
        return new Scope(userId, userId==1 && resolved.allDepartments(), resolved.allDepartments(),
                resolved.selfOnlyGranted(), resolved.departments(), resolved.actionGranted());
    }
    public boolean canEquipment(Scope scope, long equipmentId) {
        if (!enabled) return true;
        if (equipmentId <= 0) return false;
        var filter=DepartmentScopeSql.equipmentPredicate(scope,"e.id");
        List<Object> args=new ArrayList<>(); args.add(equipmentId); args.addAll(filter.args());
        Long count=jdbc.queryForObject("SELECT COUNT(*) FROM ems_equipment e WHERE e.id=? AND ("+filter.sql()+")", Long.class, args.toArray());
        return count != null && count > 0;
    }
}
