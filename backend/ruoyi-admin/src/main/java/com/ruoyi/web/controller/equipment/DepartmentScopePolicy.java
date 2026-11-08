package com.ruoyi.web.controller.equipment;

import java.util.Set;

/** Proposed data-scope decisions only. Not wired to controllers or an authorization switch. */
public final class DepartmentScopePolicy {
    private DepartmentScopePolicy() {}

    /** departmentIds is the already resolved union of enabled role scopes and permitted descendants. */
    public record Scope(long userId, boolean administrator, boolean allDepartments, Set<Long> departmentIds, boolean mayAcceptPending) {
        public Scope(long userId, boolean administrator, Set<Long> departmentIds, boolean mayAcceptPending) {
            this(userId, administrator, false, departmentIds, mayAcceptPending);
        }
        public Scope {
            if (userId <= 0 || departmentIds == null || departmentIds.stream().anyMatch(id -> id == null || id <= 0))
                throw new IllegalArgumentException("Invalid department scope");
            departmentIds = Set.copyOf(departmentIds);
        }
    }

    /** Callers must separately enforce menu/action permissions and validate department status. */
    public static boolean canAccessEquipment(Scope scope, Long equipmentDepartmentId) {
        return scope.administrator() || (equipmentDepartmentId != null && (scope.allDepartments() || scope.departmentIds().contains(equipmentDepartmentId)));
    }

    /** Work order participation survives device reassignment; pending is the cross-department queue. */
    public static boolean canReadOrder(Scope scope, Long equipmentDepartmentId, long reporterId, Long technicianId, String status) {
        return canAccessEquipment(scope, equipmentDepartmentId)
            || reporterId == scope.userId()
            || (technicianId != null && technicianId == scope.userId())
            || (scope.mayAcceptPending() && "REPORTED".equals(status));
    }

    public static boolean canReadInspection(Scope scope, Long equipmentDepartmentId, long inspectorId) {
        return canAccessEquipment(scope, equipmentDepartmentId) || inspectorId == scope.userId();
    }
}
