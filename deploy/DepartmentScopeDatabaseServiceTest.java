package com.ruoyi.web.controller.equipment;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;

/** Standalone contract test; no controllers use the database service yet. */
public class DepartmentScopeDatabaseServiceTest {
    static class Fake extends JdbcTemplate {
        boolean active=true; List<Map<String,Object>> roles=List.of(); String seenAction; int roleQueries;
        @Override public List<Map<String,Object>> queryForList(String sql) { return queryForList(sql, new Object[0]); }
        @Override public List<Map<String,Object>> queryForList(String sql,Object... args) {
            if(sql.startsWith("SELECT dept_id FROM sys_user")) return active?List.of(Map.of("dept_id",100L)):List.of();
            if(sql.startsWith("SELECT dept_id,parent_id")) return List.of(Map.of("dept_id",100L,"parent_id",0L),Map.of("dept_id",101L,"parent_id",100L),Map.of("dept_id",102L,"parent_id",101L),Map.of("dept_id",200L,"parent_id",0L));
            if(sql.startsWith("SELECT DISTINCT")) { seenAction=(String)args[1]; roleQueries++; if(!sql.contains("BINARY m.perms=BINARY ?")) throw new AssertionError("action not parameterized"); return roles; }
            if(sql.startsWith("SELECT dept_id FROM sys_role_dept")) return List.of(Map.of("dept_id",200L),Map.of("dept_id",999L));
            throw new AssertionError(sql);
        }
    }
    static void check(boolean b) {if(!b) throw new AssertionError();}
    public static void main(String[] a) {
        Fake f=new Fake(); var service=new DepartmentScopeDatabaseService(f);
        f.roles=List.of(Map.of("role_id",2L,"data_scope","4"),Map.of("role_id",3L,"data_scope","2"),Map.of("role_id",4L,"data_scope","5"));
        var r=service.resolveUser(7,"equipment:order:list");
        check(r.departments().equals(Set.of(100L,101L,102L,200L)) && r.selfOnlyGranted() && !r.allDepartments());
        check(f.seenAction.equals("equipment:order:list"));
        f.roles=List.of(Map.of("role_id",2L,"data_scope","1")); check(service.resolveUser(7,"equipment:order:list").allDepartments());
        f.roles=List.of(); check(service.resolveUser(7,"equipment:order:list").departments().isEmpty());
        int count=f.roleQueries; check(service.resolveUser(1,"equipment:order:list").allDepartments()); check(f.roleQueries==count);
        f.active=false; check(!service.resolveUser(1,"equipment:order:list").allDepartments());
        try {service.resolveUser(7,"x' OR 1=1");throw new AssertionError();} catch(IllegalArgumentException expected) {}
        System.out.println("department database resolver contract passed; no endpoint enforcement");
    }
}
