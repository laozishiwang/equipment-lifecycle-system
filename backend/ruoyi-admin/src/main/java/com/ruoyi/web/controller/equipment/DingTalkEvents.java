package com.ruoyi.web.controller.equipment;

import org.springframework.jdbc.core.JdbcTemplate;

final class DingTalkEvents {
    private DingTalkEvents() {}
    static void record(JdbcTemplate jdbc, long orderId, String eventType) {
        jdbc.update("INSERT IGNORE INTO ems_dingtalk_outbox(order_id,event_type) SELECT ?,? WHERE EXISTS (SELECT 1 FROM ems_dingtalk_config WHERE id=1 AND enabled=1)", orderId, eventType);
        jdbc.update("INSERT IGNORE INTO ems_mail_outbox(order_id,event_type) SELECT ?,? WHERE EXISTS (SELECT 1 FROM ems_mail_config WHERE id=1 AND enabled=1)", orderId, eventType);
    }
}
