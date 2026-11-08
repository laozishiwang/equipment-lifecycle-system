package com.ruoyi.web.controller.equipment;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Service
public class MailSender {
    private final JdbcTemplate jdbc;
    public MailSender(JdbcTemplate jdbc) { this.jdbc=jdbc; }
    public void send(String title,String content) {
        var rows=jdbc.queryForList("SELECT * FROM ems_mail_config WHERE id=1");
        if(rows.isEmpty()) throw new IllegalStateException("请先保存邮箱配置");
        var c=rows.get(0); var mail=new JavaMailSenderImpl();
        mail.setHost(c.get("host").toString()); mail.setPort(((Number)c.get("port")).intValue());
        mail.setUsername(c.get("username").toString()); mail.setPassword(c.get("password").toString());
        var props=mail.getJavaMailProperties(); props.put("mail.smtp.auth","true");
        props.put("mail.smtp.connectiontimeout","10000"); props.put("mail.smtp.timeout","10000"); props.put("mail.smtp.writetimeout","10000");
        String security=c.get("security").toString();
        if("SSL".equals(security)) props.put("mail.smtp.ssl.enable","true");
        if("STARTTLS".equals(security)){props.put("mail.smtp.starttls.enable","true");props.put("mail.smtp.starttls.required","true");}
        var msg=new SimpleMailMessage();msg.setFrom(c.get("sender").toString());msg.setTo(c.get("recipients").toString().split("\\s*[,，;；]\\s*"));msg.setSubject(title);msg.setText(content);mail.send(msg);
    }
    @Scheduled(fixedDelay=10000)
    public void dispatch(){
        String owner=UUID.randomUUID().toString();
        int n=jdbc.update("UPDATE ems_mail_outbox SET lease_owner=?,lease_until=DATE_ADD(NOW(),INTERVAL 1 MINUTE),attempts=attempts+1 WHERE status='PENDING' AND available_at<=NOW() AND (lease_until IS NULL OR lease_until<NOW()) AND EXISTS (SELECT 1 FROM ems_mail_config WHERE id=1 AND enabled=1) ORDER BY id LIMIT 1",owner);
        if(n==0)return;
        var rows=jdbc.queryForList("SELECT o.id,o.order_id,o.event_type,w.description,e.name,e.code FROM ems_mail_outbox o JOIN ems_work_order w ON w.id=o.order_id JOIN ems_equipment e ON e.id=w.equipment_id WHERE o.lease_owner=?",owner);
        if(rows.isEmpty())return;var r=rows.get(0);String title="CLOSED".equals(r.get("event_type"))?"维修已完成":"设备报修提醒";
        try{send(title,"工单："+r.get("order_id")+"\n设备："+r.get("code")+" "+r.get("name")+"\n故障："+r.get("description"));jdbc.update("UPDATE ems_mail_outbox SET status='SENT',sent_at=NOW(),lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?",r.get("id"),owner);}
        catch(Exception e){jdbc.update("UPDATE ems_mail_outbox SET status=IF(attempts>=5,'FAILED','PENDING'),last_error='发送失败，请检查邮箱配置',available_at=DATE_ADD(NOW(),INTERVAL 1 MINUTE),lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?",r.get("id"),owner);}
    }
}
