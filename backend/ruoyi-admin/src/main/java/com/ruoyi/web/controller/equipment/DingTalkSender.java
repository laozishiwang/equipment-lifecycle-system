package com.ruoyi.web.controller.equipment;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Service
public class DingTalkSender {
    private final JdbcTemplate jdbc;
    private final ObjectMapper json = new ObjectMapper();
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    public DingTalkSender(JdbcTemplate jdbc) { this.jdbc=jdbc; }
    public String send(String content) throws Exception {
        var rows=jdbc.queryForList("SELECT webhook,secret,keyword FROM ems_dingtalk_config WHERE id=1");
        if(rows.isEmpty() || rows.get(0).get("webhook").toString().isBlank()) return "请先配置 Webhook";
        var row=rows.get(0);String url=row.get("webhook").toString(),secret=row.get("secret").toString(),keyword=row.get("keyword").toString();
        URI uri=URI.create(url);
        if(!"https".equalsIgnoreCase(uri.getScheme()) || !"oapi.dingtalk.com".equalsIgnoreCase(uri.getHost()) || !"/robot/send".equals(uri.getPath()) || uri.getUserInfo()!=null || uri.getPort()!=-1 || uri.getFragment()!=null) return "Webhook 地址无效";
        if(!secret.isBlank()) { long now=System.currentTimeMillis(); Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8),"HmacSHA256"));String sign=Base64.getEncoder().encodeToString(mac.doFinal((now+"\n"+secret).getBytes(StandardCharsets.UTF_8)));url+=(url.contains("?")?"&":"?")+"timestamp="+now+"&sign="+URLEncoder.encode(sign,StandardCharsets.UTF_8); }
        String body=json.writeValueAsString(Map.of("msgtype","text","text",Map.of("content",(keyword.isBlank()?"":keyword+"\n")+content)));
        return post(URI.create(url),body);
    }
    String post(URI url,String body) throws Exception {
        var req=HttpRequest.newBuilder(url).timeout(Duration.ofSeconds(10)).header("Content-Type","application/json; charset=utf-8").POST(HttpRequest.BodyPublishers.ofString(body)).build();
        var response=http.send(req,HttpResponse.BodyHandlers.ofString());
        return parseResponse(response.statusCode(),response.body());
    }
    String parseResponse(int status,String body) throws Exception {
        if(status!=200) return "钉钉 HTTP 状态："+status;
        var data=json.readTree(body); return data.path("errcode").asInt(-1)==0 ? "" : "钉钉错误码："+data.path("errcode").asText()+"，"+data.path("errmsg").asText("");
    }
    @Scheduled(fixedDelay=10000)
    public void dispatch() {
        String owner=UUID.randomUUID().toString();
        int n=jdbc.update("UPDATE ems_dingtalk_outbox SET lease_owner=?,lease_until=DATE_ADD(NOW(),INTERVAL 1 MINUTE),attempts=attempts+1 WHERE status='PENDING' AND available_at<=NOW() AND (lease_until IS NULL OR lease_until<NOW()) AND EXISTS (SELECT 1 FROM ems_dingtalk_config WHERE id=1 AND enabled=1) ORDER BY id LIMIT 1",owner);
        if(n==0)return;
        var jobs=jdbc.queryForList("SELECT o.id,o.order_id,o.event_type,w.description,e.name,e.code FROM ems_dingtalk_outbox o JOIN ems_work_order w ON w.id=o.order_id JOIN ems_equipment e ON e.id=w.equipment_id WHERE o.lease_owner=?",owner);
        if(jobs.isEmpty())return;
        var j=jobs.get(0);String error;
        try { String content=("CLOSED".equals(j.get("event_type"))?"维修已完成":"设备报修提醒")+"\n工单："+j.get("order_id")+"\n设备："+j.get("code")+" "+j.get("name"); var config=jdbc.queryForList("SELECT template FROM ems_dingtalk_config WHERE id=1"); if(!config.isEmpty() && "detailed".equals(config.get(0).get("template"))) content+="\n故障："+j.get("description"); error=send(content); }
        catch(Exception ex) { error="发送失败，请检查网络及机器人配置"; }
        if(error.isEmpty())jdbc.update("UPDATE ems_dingtalk_outbox SET status='SENT',sent_at=NOW(),lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?",j.get("id"),owner);
        else jdbc.update("UPDATE ems_dingtalk_outbox SET status=IF(attempts>=5,'FAILED','PENDING'),last_error=?,available_at=DATE_ADD(NOW(),INTERVAL 1 MINUTE),lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?",error,j.get("id"),owner);
    }
}
