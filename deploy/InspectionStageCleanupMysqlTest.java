package com.ruoyi.web.controller.equipment;
import java.nio.file.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
public class InspectionStageCleanupMysqlTest {
 static void check(boolean b){if(!b)throw new AssertionError();}
 public static void main(String[] args) throws Exception {
  var ds=new DriverManagerDataSource("jdbc:mysql://stage-photo-mysql:3306/photo_test?allowPublicKeyRetrieval=true&useSSL=false","root","isolated-test-only");
  var j=new JdbcTemplate(ds); var tm=new DataSourceTransactionManager(ds); var tx=new TransactionTemplate(tm);
  j.execute("CREATE TABLE ems_inspection_photo_stage(id BIGINT PRIMARY KEY,stored_name VARCHAR(100),inspection_id BIGINT,expires_at DATETIME)");
  j.execute("CREATE TABLE ems_inspection_photo(stored_name VARCHAR(100))"); j.execute("CREATE TABLE ems_work_order_photo(stored_name VARCHAR(100))");
  Path dir=Files.createTempDirectory("expired-photo-"); String name="00000000-0000-4000-8000-000000000001.png"; Path file=dir.resolve(name); Files.write(file,new byte[]{1});
  try {
   j.update("INSERT INTO ems_inspection_photo_stage VALUES(1,?,NULL,DATE_SUB(NOW(),INTERVAL 3 HOUR))",name);
   var cleaner=new InspectionStageCleanup(j,tm,dir.toString()); var method=InspectionStageCleanup.class.getDeclaredMethod("cleanOne",long.class); method.setAccessible(true);
   try {tx.executeWithoutResult(status->{try{method.invoke(cleaner,1L);}catch(Exception e){throw new RuntimeException(e);} throw new IllegalStateException("rollback");}); throw new AssertionError();} catch(IllegalStateException ok){check("rollback".equals(ok.getMessage()));}
   check(Files.exists(file)); check(j.queryForObject("SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id=1",Long.class)==1);
   j.update("INSERT INTO ems_inspection_photo VALUES(?)",name); cleaner.cleanExpired(); check(Files.exists(file)); check(j.queryForObject("SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id=1",Long.class)==1);
   j.update("DELETE FROM ems_inspection_photo"); cleaner.cleanExpired(); check(!Files.exists(file)); check(j.queryForObject("SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id=1",Long.class)==0);
   System.out.println("expired-stage real mysql rollback, referenced preservation and commit passed");
  } finally {Files.deleteIfExists(file);Files.deleteIfExists(dir);}
 }
}
