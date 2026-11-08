package com.ruoyi.web.controller.equipment;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import java.util.Set;

/** Runs ONLY against disposable scope_mysql_test database on isolated container network. */
public class DepartmentScopeDatabaseMysqlTest {
    static void check(boolean ok) { if (!ok) throw new AssertionError(); }
    public static void main(String[] args) {
        if(args.length!=1) throw new IllegalArgumentException("test password required");
        var ds=new DriverManagerDataSource("jdbc:mysql://scope-mysql-test:3306/scope_mysql_test?allowPublicKeyRetrieval=true&useSSL=false","root",args[0]);
        var j=new JdbcTemplate(ds);
        j.execute("CREATE TABLE ems_equipment (id BIGINT PRIMARY KEY)");
        j.execute("CREATE TABLE ems_equipment_department (equipment_id BIGINT PRIMARY KEY,dept_id BIGINT)");
        j.execute("CREATE TABLE sys_user (user_id BIGINT PRIMARY KEY,dept_id BIGINT,status CHAR(1),del_flag CHAR(1))");
        j.execute("CREATE TABLE sys_dept (dept_id BIGINT PRIMARY KEY,parent_id BIGINT,status CHAR(1),del_flag CHAR(1))");
        j.execute("CREATE TABLE sys_role (role_id BIGINT PRIMARY KEY,data_scope CHAR(1),status CHAR(1),del_flag CHAR(1))");
        j.execute("CREATE TABLE sys_user_role (user_id BIGINT,role_id BIGINT)");
        j.execute("CREATE TABLE sys_menu (menu_id BIGINT PRIMARY KEY,perms VARCHAR(100),status CHAR(1))");
        j.execute("CREATE TABLE sys_role_menu (role_id BIGINT,menu_id BIGINT)");
        j.execute("CREATE TABLE sys_role_dept (role_id BIGINT,dept_id BIGINT)");
        j.update("INSERT INTO sys_user VALUES (1,100,'0','0'),(7,100,'0','0'),(8,100,'1','0')");
        j.update("INSERT INTO sys_dept VALUES (100,0,'0','0'),(101,100,'0','0'),(102,101,'0','0'),(103,100,'1','0'),(104,103,'0','0'),(200,0,'0','0'),(201,0,'1','0')");
        j.update("INSERT INTO sys_role VALUES (2,'4','0','0'),(3,'2','0','0'),(4,'5','0','0'),(5,'1','1','0'),(6,'1','0','0'),(7,'1','0','2')");
        j.update("INSERT INTO sys_user_role VALUES (7,2),(7,3),(7,4),(7,5),(7,6),(7,7)");
        j.update("INSERT INTO sys_menu VALUES (1,'equipment:order:list','0'),(2,'equipment:order:edit','0'),(3,'equipment:order:list','1')");
        j.update("INSERT INTO sys_role_menu VALUES (2,1),(3,1),(4,1),(5,1),(6,2),(7,1),(6,3)");
        j.update("INSERT INTO sys_role_dept VALUES (3,200),(3,201)");
        var s=new DepartmentScopeDatabaseService(j);
        j.update("INSERT INTO ems_equipment VALUES (1),(2),(3),(4)");
        j.update("INSERT INTO ems_equipment_department VALUES (1,100),(2,200),(3,201)");
        var access=new DepartmentScopeAccess(j,s,true);
        try { access.rejectIncompleteRollout(); throw new AssertionError("incomplete rollout accepted"); } catch (IllegalStateException expected) {}
        var scope=new DepartmentScopeAccess.Scope(7,false,false,false,Set.of(100L),true);
        check(access.canEquipment(scope,1)); check(!access.canEquipment(scope,2)); check(!access.canEquipment(scope,3)); check(!access.canEquipment(scope,4));
        check(!access.canEquipment(new DepartmentScopeAccess.Scope(7,false,true,false,Set.of(),false),1));
        check(access.canEquipment(new DepartmentScopeAccess.Scope(1,true,true,true,Set.of(),true),4));
        var list=s.resolveUser(7,"equipment:order:list");
        check(list.actionGranted());
        check(list.departments().equals(Set.of(100L,101L,102L,200L)) && list.selfOnlyGranted() && !list.allDepartments());
        check(s.resolveUser(7,"equipment:order:edit").allDepartments());
        check(!s.resolveUser(7,"equipment:ORDER:edit").allDepartments());
        check(!s.resolveUser(8,"equipment:order:edit").allDepartments());
        check(s.resolveUser(1,"equipment:order:edit").allDepartments());
        j.update("UPDATE sys_user SET status='1' WHERE user_id=1"); check(!s.resolveUser(1,"equipment:order:edit").allDepartments());
        j.update("UPDATE sys_role SET status='1' WHERE role_id=2");
        check(s.resolveUser(7,"equipment:order:list").departments().equals(Set.of(200L)));
        j.update("UPDATE sys_menu SET status='1' WHERE menu_id=1"); check(!s.resolveUser(7,"equipment:order:list").actionGranted());
        System.out.println("disposable MySQL department scope integration passed; endpoints unchanged");
    }
}
