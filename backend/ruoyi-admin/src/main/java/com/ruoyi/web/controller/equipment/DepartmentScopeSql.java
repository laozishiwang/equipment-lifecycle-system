package com.ruoyi.web.controller.equipment;

import java.util.ArrayList;
import java.util.List;

/** Parameterized SQL for equipment-owned records. Not connected to endpoints. */
public final class DepartmentScopeSql {
    private DepartmentScopeSql() { }
    public record SqlFilter(String sql, List<Object> args) {
        public SqlFilter { args = List.copyOf(args); }
    }
    public static SqlFilter equipmentPredicate(DepartmentScopeAccess.Scope scope, String equipmentIdExpression) {
        if (scope == null || equipmentIdExpression == null || !equipmentIdExpression.matches("[A-Za-z_][A-Za-z0-9_]*\\.[A-Za-z_][A-Za-z0-9_]*"))
            throw new IllegalArgumentException("Invalid trusted equipment identifier");
        if (!scope.actionGranted()) return new SqlFilter("1=0", List.of());
        if (scope.administrator()) return new SqlFilter("1=1", List.of());
        String prefix = "EXISTS (SELECT 1 FROM ems_equipment_department ds_owner JOIN sys_dept ds_dept ON ds_dept.dept_id=ds_owner.dept_id AND ds_dept.status='0' AND ds_dept.del_flag='0' WHERE ds_owner.equipment_id=" + equipmentIdExpression;
        if (scope.allDepartments()) return new SqlFilter(prefix + ")", List.of());
        if (scope.departmentIds().isEmpty()) return new SqlFilter("1=0", List.of());
        var sorted = scope.departmentIds().stream().sorted().toList();
        String placeholders = String.join(",", java.util.Collections.nCopies(sorted.size(), "?"));
        List<Object> args = new ArrayList<>(sorted);
        return new SqlFilter(prefix + " AND ds_owner.dept_id IN (" + placeholders + "))", args);
    }
}
