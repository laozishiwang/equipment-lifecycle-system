package com.ruoyi.web.controller.equipment;

/** Centralizes the live-role requirement for the cross-department pending queue. */
final class PendingOrderPermission {
    private PendingOrderPermission() {}
    static boolean allowed(boolean cachedPermission, boolean scopeEnabled, boolean livePermission) {
        return cachedPermission && (!scopeEnabled || livePermission);
    }
    static boolean current(DepartmentScopeAccess access) {
        boolean cached=com.ruoyi.common.utils.SecurityUtils.hasPermi("equipment:order:accept");
        if (!cached || !access.enabled()) return cached;
        return allowed(true,true,access.current("equipment:order:accept").actionGranted());
    }
}
