package com.ruoyi.web.controller.equipment;

import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/monitor/mail")
public class MailConfigController extends BaseController {
    private final JdbcTemplate jdbc; private final MailSender sender;
    public MailConfigController(JdbcTemplate jdbc,MailSender sender){this.jdbc=jdbc;this.sender=sender;}
    public record Config(Boolean enabled,String host,Integer port,String security,String username,String password,String from,String recipients){}
    @PreAuthorize("@ss.hasPermi('monitor:email:config')") @GetMapping("/config")
    public AjaxResult get(){
        if(!SecurityUtils.isAdmin(SecurityUtils.getUserId())) return error("仅管理员可管理邮箱通知");
        var rows=jdbc.queryForList("SELECT enabled,host,port,security,username,password,sender,recipients FROM ems_mail_config WHERE id=1");
        if(rows.isEmpty())return success(Map.of("enabled",false,"host","","port",465,"security","SSL","username","","from","","recipients","","hasPassword",false));
        var r=rows.get(0);return success(Map.of("enabled",((Number)r.get("enabled")).intValue()!=0,"host",r.get("host"),"port",r.get("port"),"security",r.get("security"),"username",r.get("username"),"from",r.get("sender"),"recipients",r.get("recipients"),"hasPassword",!r.get("password").toString().isBlank()));
    }
    @PreAuthorize("@ss.hasPermi('monitor:email:config')") @PutMapping("/config")
    public AjaxResult save(@RequestBody Config c){
        if(!SecurityUtils.isAdmin(SecurityUtils.getUserId()))return error("仅管理员可管理邮箱通知");
        if(c.host()==null||c.host().isBlank()||c.host().length()>255||c.port()==null||c.port()<1||c.port()>65535||!java.util.List.of("SSL","STARTTLS","NONE").contains(c.security())||c.username()==null||c.username().isBlank()||c.from()==null||c.from().isBlank()||c.recipients()==null||c.recipients().isBlank())return error("请填写完整邮箱配置");
        jdbc.update("INSERT INTO ems_mail_config(id,recipients) VALUES(1,'') ON DUPLICATE KEY UPDATE id=id");
        jdbc.update("UPDATE ems_mail_config SET enabled=?,host=?,port=?,security=?,username=?,password=COALESCE(NULLIF(?,''),password),sender=?,recipients=? WHERE id=1",Boolean.TRUE.equals(c.enabled()),c.host().trim(),c.port(),c.security(),c.username().trim(),c.password(),c.from().trim(),c.recipients().trim());return success();
    }
    @PreAuthorize("@ss.hasPermi('monitor:email:config')") @PostMapping("/test")
    public AjaxResult test(){if(!SecurityUtils.isAdmin(SecurityUtils.getUserId()))return error("仅管理员可测试邮箱通知");try{sender.send("设备管理系统通知测试","这是一封测试邮件。");return success("测试邮件已发送");}catch(Exception e){return error("发送失败，请检查邮箱配置和网络");}}
}
