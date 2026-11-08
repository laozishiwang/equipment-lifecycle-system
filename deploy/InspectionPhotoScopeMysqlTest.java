package com.ruoyi.web.controller.equipment;
import java.util.*; import java.util.concurrent.*;
import org.springframework.jdbc.core.JdbcTemplate; import org.springframework.jdbc.datasource.DriverManagerDataSource;
public class InspectionPhotoScopeMysqlTest {
 static void check(boolean v){if(!v)throw new AssertionError();}
 public static void main(String[] a) throws Exception {
  var ds=new DriverManagerDataSource("jdbc:mysql://photo-read-mysql:3306/photo_test?allowPublicKeyRetrieval=true&useSSL=false","root","isolated-test-only"); var j=new JdbcTemplate(ds);
  j.execute("CREATE TABLE sys_dept(dept_id BIGINT PRIMARY KEY,status CHAR(1),del_flag CHAR(1))"); j.execute("CREATE TABLE ems_equipment(id BIGINT PRIMARY KEY)"); j.execute("CREATE TABLE ems_equipment_department(equipment_id BIGINT PRIMARY KEY,dept_id BIGINT)"); j.execute("CREATE TABLE ems_inspection(id BIGINT PRIMARY KEY,equipment_id BIGINT,inspector_id BIGINT)"); j.execute("CREATE TABLE ems_inspection_photo(id BIGINT PRIMARY KEY,inspection_id BIGINT)");
  j.update("INSERT INTO sys_dept VALUES(1,'0','0'),(2,'0','0')"); j.update("INSERT INTO ems_equipment VALUES(10)"); j.update("INSERT INTO ems_equipment_department VALUES(10,1)"); j.update("INSERT INTO ems_inspection VALUES(20,10,99)"); j.update("INSERT INTO ems_inspection_photo VALUES(30,20)");
  var scope=new DepartmentScopeAccess.Scope(7,false,false,false,Set.of(1L),true); var f=InspectionScopeSql.read(scope,"ins"); var args=new ArrayList<Object>(); args.add(30L);args.addAll(f.args()); String sql="SELECT COUNT(*) FROM ems_inspection_photo p WHERE p.id=? AND EXISTS (SELECT 1 FROM ems_inspection ins WHERE ins.id=p.inspection_id AND ("+f.sql()+"))";
  check(j.queryForObject(sql,Long.class,args.toArray())==1);
  try(var c=ds.getConnection()){c.setAutoCommit(false);try(var st=c.prepareStatement("SELECT id FROM ems_equipment WHERE id=10 FOR UPDATE")){st.executeQuery();} try(var st=c.prepareStatement("UPDATE ems_equipment_department SET dept_id=2 WHERE equipment_id=10")){st.executeUpdate();}
   var pool=Executors.newSingleThreadExecutor();try { var future=pool.submit(()->{try(var c2=ds.getConnection()){c2.setAutoCommit(false);try(var st=c2.prepareStatement("SELECT id FROM ems_equipment WHERE id=10 FOR UPDATE")){st.executeQuery();} try(var st=c2.prepareStatement("SELECT id FROM ems_inspection WHERE id=20 FOR UPDATE")){st.executeQuery();} var j2=new JdbcTemplate(new org.springframework.jdbc.datasource.SingleConnectionDataSource(c2,true)); long n=j2.queryForObject(sql,Long.class,args.toArray());c2.commit();return n;}}); Thread.sleep(250);check(!future.isDone()); c.commit();check(future.get(10,TimeUnit.SECONDS)==0); } finally {pool.shutdownNow();}}
  System.out.println("same-department photo SQL and department transfer lock passed; controller HTTP not tested");
 }
}
