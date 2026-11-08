package com.ruoyi.web.controller.equipment;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Pure proposal; not connected to authentication, queries or controller enforcement. */
public final class DepartmentScopeResolver {
    private DepartmentScopeResolver() {}

    /** eligible must reflect both enabled role state and the permission for the operation. */
    public record Role(String dataScope, boolean eligible, Set<Long> customDepartments) {
        public Role { customDepartments=Set.copyOf(customDepartments); }
    }
    /** descendants must be resolved from trusted enabled department data, not client input. */
    public record Input(boolean administrator, Long userDepartment, Set<Long> enabledDepartments,
                        Map<Long,Set<Long>> descendants, List<Role> roles) { }
    public record Result(boolean allDepartments, boolean selfOnlyGranted, Set<Long> departments, boolean actionGranted) { }

    public static Result resolve(Input input) {
        if (input==null || input.enabledDepartments()==null || input.descendants()==null || input.roles()==null)
            throw new IllegalArgumentException("Missing trusted scope data");
        if (input.administrator()) return new Result(true,true,Set.of(),true);
        Set<Long> allowed=new HashSet<>(); boolean all=false,self=false,granted=false;
        for (Role role:input.roles()) {
            if (!role.eligible()) continue;
            granted=true;
            switch (role.dataScope()) {
                case "1" -> all=true;
                case "2" -> allowed.addAll(role.customDepartments());
                case "3" -> { if(input.userDepartment()!=null) allowed.add(input.userDepartment()); }
                case "4" -> {
                    if(input.userDepartment()!=null) {
                        allowed.add(input.userDepartment());
                        allowed.addAll(input.descendants().getOrDefault(input.userDepartment(),Set.of()));
                    }
                }
                case "5" -> self=true;
                default -> throw new IllegalArgumentException("Unknown data scope");
            }
        }
        allowed.retainAll(input.enabledDepartments());
        return new Result(all,self,Set.copyOf(allowed),granted);
    }
}
