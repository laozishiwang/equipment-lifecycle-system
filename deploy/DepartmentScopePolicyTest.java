import com.ruoyi.web.controller.equipment.DepartmentScopePolicy;
import com.ruoyi.web.controller.equipment.DepartmentScopePolicy.Scope;
import java.util.Set;

/** Standalone contract checks; this does not claim any endpoint enforces the policy. */
public class DepartmentScopePolicyTest {
    private static void check(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        Scope a=new Scope(10,false,Set.of(100L,101L),false);
        Scope b=new Scope(20,false,Set.of(200L),false);
        Scope tech=new Scope(30,false,Set.of(200L),true);
        Scope multi=new Scope(40,false,Set.of(100L,101L,200L),false);
        Scope admin=new Scope(1,true,Set.of(),false);
        check(DepartmentScopePolicy.canAccessEquipment(a,100L));
        check(DepartmentScopePolicy.canAccessEquipment(a,101L));
        check(!DepartmentScopePolicy.canAccessEquipment(a,200L));
        check(!DepartmentScopePolicy.canAccessEquipment(a,null));
        check(DepartmentScopePolicy.canAccessEquipment(multi,200L));
        check(DepartmentScopePolicy.canAccessEquipment(admin,null));
        Scope all = new Scope(50,false,true,Set.of(),false);
        check(DepartmentScopePolicy.canAccessEquipment(all,200L));
        check(!DepartmentScopePolicy.canAccessEquipment(all,null));
        Scope self = new Scope(60,false,false,Set.of(),false);
        check(!DepartmentScopePolicy.canAccessEquipment(self,100L));
        check(DepartmentScopePolicy.canReadOrder(self,100L,60,null,"CLOSED"));
        check(DepartmentScopePolicy.canReadOrder(tech,100L,10,null,"REPORTED"));
        check(!DepartmentScopePolicy.canReadOrder(b,100L,10,null,"REPORTED"));
        check(DepartmentScopePolicy.canReadOrder(tech,null,10,30L,"CLOSED"));
        check(DepartmentScopePolicy.canReadOrder(a,200L,10,null,"CLOSED"));
        check(!DepartmentScopePolicy.canReadOrder(tech,100L,10,40L,"CLOSED"));
        check(DepartmentScopePolicy.canReadInspection(a,200L,10));
        check(!DepartmentScopePolicy.canReadInspection(b,null,10));
        try { new Scope(1,false,Set.of(-1L),false); throw new AssertionError(); } catch (IllegalArgumentException expected) { }
        System.out.println("department policy contract passed; endpoints remain unchanged");
    }
}
