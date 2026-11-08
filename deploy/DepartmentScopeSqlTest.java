import com.ruoyi.web.controller.equipment.DepartmentScopeAccess.Scope;
import com.ruoyi.web.controller.equipment.DepartmentScopeSql;
import java.util.Set;
import java.util.List;
public class DepartmentScopeSqlTest {
 public static void main(String[] args) {
  var revoked=DepartmentScopeSql.equipmentPredicate(new Scope(9,false,true,false,Set.of(),false),"e.id");
  if(!revoked.sql().equals("1=0")) throw new AssertionError();
  var admin=DepartmentScopeSql.equipmentPredicate(new Scope(1,true,true,true,Set.of(),true),"e.id");
  if(!admin.sql().equals("1=1")) throw new AssertionError();
  var all=DepartmentScopeSql.equipmentPredicate(new Scope(2,false,true,false,Set.of(),true),"e.id");
  if(!all.sql().contains("ds_dept.status='0'") || !all.args().isEmpty()) throw new AssertionError();
  var empty=DepartmentScopeSql.equipmentPredicate(new Scope(3,false,false,false,Set.of(),true),"e.id");
  if(!empty.sql().equals("1=0")) throw new AssertionError();
  var scoped=DepartmentScopeSql.equipmentPredicate(new Scope(4,false,false,false,Set.of(2L,1L),true),"e.id");
  if(!scoped.sql().contains("IN (?,?)") || !scoped.args().equals(List.of(1L,2L))) throw new AssertionError();
  try { DepartmentScopeSql.equipmentPredicate(new Scope(1,true,true,true,Set.of(),true),"e.id OR 1=1"); throw new AssertionError(); } catch (IllegalArgumentException ok) { }
  System.out.println("department SQL filter tests passed; not connected to controllers");
 }
}
