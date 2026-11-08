package com.ruoyi.web.controller.equipment;
import java.nio.file.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
public class StagePhotoCommitMysqlTest {
 static void check(boolean ok) {if(!ok) throw new AssertionError();}
 public static void main(String[] args) throws Exception {
  var ds=new DriverManagerDataSource("jdbc:mysql://stage-photo-mysql:3306/photo_test?allowPublicKeyRetrieval=true&useSSL=false","root","isolated-test-only");
  var jdbc=new JdbcTemplate(ds); var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));
  jdbc.execute("CREATE TABLE staged (id BIGINT PRIMARY KEY, stored_name VARCHAR(100) NOT NULL)");
  Path file=Files.createTempFile("stage-real-db-", ".png");
  try {
   jdbc.update("INSERT INTO staged VALUES (1,?)",file.getFileName().toString());
   try { tx.executeWithoutResult(status -> {
    jdbc.queryForList("SELECT id FROM staged WHERE id=1 FOR UPDATE");
    jdbc.update("DELETE FROM staged WHERE id=1");
    StagePhotoCommitCleanup.register(file,()->jdbc.queryForObject("SELECT COUNT(*) FROM staged WHERE stored_name=?",Long.class,file.getFileName().toString())==0);
    throw new IllegalStateException("intentional rollback");
   }); throw new AssertionError("no rollback"); } catch(IllegalStateException expected) {check(expected.getMessage().equals("intentional rollback"));}
   check(jdbc.queryForObject("SELECT COUNT(*) FROM staged WHERE id=1",Long.class)==1); check(Files.exists(file));
   tx.executeWithoutResult(status -> {
    jdbc.queryForList("SELECT id FROM staged WHERE id=1 FOR UPDATE"); jdbc.update("DELETE FROM staged WHERE id=1");
    StagePhotoCommitCleanup.register(file,()->jdbc.queryForObject("SELECT COUNT(*) FROM staged WHERE stored_name=?",Long.class,file.getFileName().toString())==0);
   });
   check(jdbc.queryForObject("SELECT COUNT(*) FROM staged WHERE id=1",Long.class)==0); check(!Files.exists(file));
   System.out.println("real MySQL rollback preserves record and file; commit removes both");
  } finally {Files.deleteIfExists(file);}
 }
}
