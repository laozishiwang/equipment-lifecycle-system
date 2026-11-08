package com.ruoyi.web.controller.equipment;

/** SQL condition for an authorized inspection reader; caller supplies only a trusted alias. */
public final class InspectionScopeSql {
    private InspectionScopeSql() {}
    public static DepartmentScopeSql.SqlFilter read(DepartmentScopeAccess.Scope scope, String alias) {
        if (scope == null || alias == null || !alias.matches("[A-Za-z_][A-Za-z0-9_]*")) throw new IllegalArgumentException("Invalid inspection alias");
        if (!scope.actionGranted()) return new DepartmentScopeSql.SqlFilter("1=0", java.util.List.of());
        var device=DepartmentScopeSql.equipmentPredicate(scope, alias+".equipment_id");
        var args=new java.util.ArrayList<Object>(device.args()); args.add(scope.userId());
        return new DepartmentScopeSql.SqlFilter("(("+device.sql()+") OR "+alias+".inspector_id=?)",args);
    }
}
