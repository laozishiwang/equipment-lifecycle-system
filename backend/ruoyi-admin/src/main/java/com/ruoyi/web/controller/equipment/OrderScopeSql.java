package com.ruoyi.web.controller.equipment;

import java.util.ArrayList;
import java.util.List;

/** Proposed query fragment for w=ems_work_order; not yet wired to endpoints. */
public final class OrderScopeSql {
    private OrderScopeSql() {}
    public record Predicate(String sql, List<Object> args) {
        public Predicate { args=List.copyOf(args); }
    }
    public static Predicate read(DepartmentScopeAccess.Scope scope, boolean mayAcceptPending) {
        if (!scope.actionGranted()) return new Predicate("1=0", List.of());
        if (scope.administrator()) return new Predicate("1=1", List.of());
        var department=DepartmentScopeSql.equipmentPredicate(scope, "w.equipment_id");
        var args=new ArrayList<Object>(department.args());
        args.add(scope.userId()); args.add(scope.userId());
        return new Predicate("("+department.sql()+" OR w.reporter_id=? OR w.technician_id=?"+
            (mayAcceptPending ? " OR w.status='REPORTED'" : "")+")", args);
    }
    public static Predicate read(DepartmentScopePolicy.Scope scope) {
        if (scope.administrator()) return new Predicate("1=1", List.of());
        var args=new ArrayList<Object>();
        String departments="";
        if (scope.allDepartments()) departments=" OR EXISTS (SELECT 1 FROM ems_equipment_department od JOIN sys_dept sd ON sd.dept_id=od.dept_id AND sd.status='0' AND sd.del_flag='0' WHERE od.equipment_id=w.equipment_id)";
        else if (!scope.departmentIds().isEmpty()) {
            var ids=scope.departmentIds().stream().sorted().toList();
            departments=" OR EXISTS (SELECT 1 FROM ems_equipment_department od JOIN sys_dept sd ON sd.dept_id=od.dept_id AND sd.status='0' AND sd.del_flag='0' WHERE od.equipment_id=w.equipment_id AND od.dept_id IN ("+String.join(",",java.util.Collections.nCopies(ids.size(),"?"))+"))";
            args.addAll(ids);
        }
        args.add(scope.userId()); args.add(scope.userId());
        String pending=scope.mayAcceptPending()?" OR w.status='REPORTED'":"";
        return new Predicate("(1=0"+departments+" OR w.reporter_id=? OR w.technician_id=?"+pending+")",args);
    }
}
