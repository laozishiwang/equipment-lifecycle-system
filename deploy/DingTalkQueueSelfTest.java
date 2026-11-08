package com.ruoyi.web.controller.equipment;
import java.net.URI;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;

public class DingTalkQueueSelfTest {
 static class Db extends JdbcTemplate {
  boolean enabled=true; String result=""; int claims, sent, failed;
  @Override public int update(String sql,Object... args) {
   if(sql.startsWith("UPDATE ems_dingtalk_outbox SET lease_owner")) { if(!enabled)return 0; claims++;return 1; }
   if(sql.contains("status='SENT'")) {sent++;return 1;}
   if(sql.contains("status=IF")) {failed++;return 1;}
   throw new AssertionError(sql);
  }
  @Override public List<Map<String,Object>> queryForList(String sql,Object... args) {
   if(sql.contains("o.lease_owner"))return List.of(Map.of("id",1L,"order_id",2L,"event_type","REPORTED","description","故障","name","设备","code","A"));
   throw new AssertionError(sql);
  }
  @Override public List<Map<String,Object>> queryForList(String sql) {
   if(sql.contains("SELECT template"))return List.of(Map.of("template","basic"));
   if(sql.contains("SELECT webhook"))return List.of(Map.of("webhook","https://oapi.dingtalk.com/robot/send?access_token=test","secret","","keyword",""));
   throw new AssertionError(sql);
  }
 }
 static class Fake extends DingTalkSender { Db db; Fake(Db db){super(db);this.db=db;} @Override String post(URI u,String body){return db.result;} }
 public static void main(String[] args) { Db db=new Db();Fake f=new Fake(db); db.enabled=false;f.dispatch();if(db.claims!=0)throw new AssertionError("disabled");db.enabled=true;f.dispatch();if(db.sent!=1)throw new AssertionError("sent");db.result="模拟发送失败";f.dispatch();if(db.failed!=1)throw new AssertionError("failure");System.out.println("queue disabled, success and failure paths passed (mock JDBC and transport)"); }
}
