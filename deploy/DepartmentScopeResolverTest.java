import com.ruoyi.web.controller.equipment.DepartmentScopeResolver;
import com.ruoyi.web.controller.equipment.DepartmentScopeResolver.Input;
import com.ruoyi.web.controller.equipment.DepartmentScopeResolver.Role;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class DepartmentScopeResolverTest {
    static void check(boolean value) { if(!value) throw new AssertionError(); }
    static Role role(String scope, boolean eligible, Long... departments) { return new Role(scope,eligible,Set.of(departments)); }
    static Input input(boolean admin,Long dept,List<Role> roles) { return new Input(admin,dept,Set.of(10L,11L,20L),Map.of(10L,Set.of(11L,99L)),roles); }
    public static void main(String[] args) {
        check(DepartmentScopeResolver.resolve(input(false,10L,List.of(role("3",true)))).departments().equals(Set.of(10L)));
        check(DepartmentScopeResolver.resolve(input(false,10L,List.of(role("4",true)))).departments().equals(Set.of(10L,11L)));
        check(DepartmentScopeResolver.resolve(input(false,10L,List.of(role("3",true),role("2",true,20L,99L)))).departments().equals(Set.of(10L,20L)));
        check(DepartmentScopeResolver.resolve(input(false,10L,List.of(role("1",false),role("5",true)))).selfOnlyGranted());
        check(!DepartmentScopeResolver.resolve(input(false,10L,List.of(role("1",false)))).allDepartments());
        check(DepartmentScopeResolver.resolve(input(false,10L,List.of(role("1",true)))).allDepartments());
        check(DepartmentScopeResolver.resolve(input(true,null,List.of())).allDepartments());
        check(DepartmentScopeResolver.resolve(input(false,null,List.of(role("3",true)))).departments().isEmpty());
        try { DepartmentScopeResolver.resolve(input(false,10L,List.of(role("invalid",true)))); throw new AssertionError(); } catch(IllegalArgumentException expected) { }
        System.out.println("department resolver contract passed; no endpoint enforcement");
    }
}
