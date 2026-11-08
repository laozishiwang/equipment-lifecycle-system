package com.ruoyi.web.controller.equipment;

import java.net.URI;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/monitor/dingtalk")
public class DingTalkConfigController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DingTalkSender sender;
    public DingTalkConfigController(JdbcTemplate jdbc, DingTalkSender sender) { this.jdbc = jdbc; this.sender=sender; }
    public record Config(Boolean enabled, String webhook, String secret, String keyword, String template, Boolean clearSecret) {}
    @org.springframework.security.access.prepost.PreAuthorize("@ss.hasPermi('monitor:dingtalk:config')")
    @GetMapping("/config")
    public AjaxResult get() {
        if (!SecurityUtils.isAdmin(SecurityUtils.getUserId())) return error("仅管理员可管理通知配置");
        var rows = jdbc.queryForList("SELECT enabled, webhook, secret, keyword, template FROM ems_dingtalk_config WHERE id=1");
        if (rows.isEmpty()) return success(Map.of("enabled",false,"hasWebhook",false,"hasSecret",false,"keyword","","template","basic"));
        var r=rows.get(0);
        return success(Map.of("enabled",((Number)r.get("enabled")).intValue()!=0,"hasWebhook",!r.get("webhook").toString().isBlank(),"hasSecret",!r.get("secret").toString().isBlank(),"keyword",r.get("keyword"),"template",r.get("template")));
    }
    @org.springframework.security.access.prepost.PreAuthorize("@ss.hasPermi('monitor:dingtalk:config')")
    @PutMapping("/config")
    public AjaxResult save(@RequestBody Config c) {
        if (!SecurityUtils.isAdmin(SecurityUtils.getUserId())) return error("仅管理员可管理通知配置");
        if (c.keyword()!=null && c.keyword().length()>100) return error("关键词不能超过100字");
        if (c.template()!=null && !java.util.List.of("basic","detailed").contains(c.template())) return error("模板无效");
        if (c.webhook()!=null && !c.webhook().isBlank()) {
            try { var u=URI.create(c.webhook()); if (!"https".equalsIgnoreCase(u.getScheme()) || !"oapi.dingtalk.com".equalsIgnoreCase(u.getHost()) || !"/robot/send".equals(u.getPath()) || u.getUserInfo()!=null || u.getPort()!=-1 || u.getFragment()!=null) return error("请输入钉钉机器人 Webhook"); }
            catch (IllegalArgumentException e) { return error("Webhook 格式无效"); }
        }
        if (c.webhook()!=null && c.webhook().length()>1024 || c.secret()!=null && c.secret().length()>255) return error("配置内容过长");
        if (Boolean.TRUE.equals(c.enabled()) && (c.webhook()==null || c.webhook().isBlank())) {
            var rows=jdbc.queryForList("SELECT webhook FROM ems_dingtalk_config WHERE id=1");
            if (rows.isEmpty() || rows.get(0).get("webhook").toString().isBlank()) return error("启用前请填写 Webhook");
        }
        jdbc.update("INSERT IGNORE INTO ems_dingtalk_config(id) VALUES (1)");
        jdbc.update("UPDATE ems_dingtalk_config SET enabled=COALESCE(?,enabled), webhook=COALESCE(NULLIF(?,''),webhook), secret=CASE WHEN ? THEN '' ELSE COALESCE(NULLIF(?,''),secret) END, keyword=COALESCE(?,keyword), template=COALESCE(?,template) WHERE id=1", c.enabled(),c.webhook(),Boolean.TRUE.equals(c.clearSecret()),c.secret(),c.keyword(),c.template());
        return success();
    }
    @org.springframework.security.access.prepost.PreAuthorize("@ss.hasPermi('monitor:dingtalk:config')")
    @GetMapping("/recent")
    public AjaxResult recent() {
        if (!SecurityUtils.isAdmin(SecurityUtils.getUserId())) return error("仅管理员可查看通知记录");
        return success(jdbc.queryForList("SELECT order_id,event_type,status,attempts,last_error,created_at,sent_at FROM ems_dingtalk_outbox ORDER BY id DESC LIMIT 20"));
    }
    @org.springframework.security.access.prepost.PreAuthorize("@ss.hasPermi('monitor:dingtalk:config')")
    @PostMapping("/test")
    public AjaxResult test() {
        if (!SecurityUtils.isAdmin(SecurityUtils.getUserId())) return error("仅管理员可测试通知");
        try { String result=sender.send("设备管理系统：钉钉通知测试"); return result.isEmpty() ? success("测试消息已发送") : error(result); }
        catch (Exception ex) { return error("发送失败，请检查网络及机器人配置"); }
    }
}
