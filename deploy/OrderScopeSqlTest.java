import com.ruoyi.web.controller.equipment.OrderScopeSql;
import com.ruoyi.web.controller.equipment.DepartmentScopePolicy.Scope;
import java.util.*;
public class OrderScopeSqlTest {
 public static void main(String[] args) {
  var p=OrderScopeSql.read(new Scope(7,false,Set.of(20L,10L),true));
  if (!p.args().equals(List.of(10L,20L,7L,7L)) || !p.sql().contains("od.dept_id IN (?,?)") || !p.sql().contains("w.status='REPORTED'")) throw new AssertionError(p);
  var empty=OrderScopeSql.read(new Scope(7,false,Set.of(),false));
  if (empty.sql().contains(" IN ") || empty.sql().contains("REPORTED") || !empty.args().equals(List.of(7L,7L))) throw new AssertionError(empty);
  var admin=OrderScopeSql.read(new Scope(1,true,Set.of(),false));
  if (!admin.sql().equals("1=1") || !admin.args().isEmpty()) throw new AssertionError(admin);
  var all=OrderScopeSql.read(new Scope(8,false,true,Set.of(),false));
  if (!all.sql().contains("sd.status='0'") || all.sql().contains(" IN ")) throw new AssertionError(all);
  var revoked=OrderScopeSql.read(new com.ruoyi.web.controller.equipment.DepartmentScopeAccess.Scope(7,false,false,false,Set.of(10L),false),true);
  if (!revoked.sql().equals("1=0") || !revoked.args().isEmpty()) throw new AssertionError(revoked);
  var active=OrderScopeSql.read(new com.ruoyi.web.controller.equipment.DepartmentScopeAccess.Scope(7,false,false,false,Set.of(10L),true),true);
  if (!active.args().equals(List.of(10L,7L,7L)) || !active.sql().contains("w.status='REPORTED'")) throw new AssertionError(active);
  System.out.println("order scope SQL contract passed; rollout remains disabled");
 }
}
