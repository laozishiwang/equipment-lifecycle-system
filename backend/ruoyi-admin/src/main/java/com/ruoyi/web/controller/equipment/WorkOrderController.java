package com.ruoyi.web.controller.equipment;

import java.math.BigDecimal;
import java.sql.PreparedStatement;
import java.sql.Statement;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/equipment/orders")
public class WorkOrderController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess departmentScope;
    public WorkOrderController(JdbcTemplate jdbc, DepartmentScopeAccess departmentScope) { this.jdbc = jdbc; this.departmentScope=departmentScope; }
    // Caller is transactional. Lock equipment before order to serialize ownership changes.
    private boolean mayChange(long id, String action, boolean participation, boolean pending) {
        if (!departmentScope.enabled()) return true;
        var initial=jdbc.queryForList("SELECT equipment_id FROM ems_work_order WHERE id=?", id);
        if (initial.isEmpty()) return false;
        long equipment=((Number)initial.get(0).get("equipment_id")).longValue();
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",equipment).isEmpty()) return false;
        var locked=jdbc.queryForList("SELECT equipment_id,reporter_id,technician_id,status FROM ems_work_order WHERE id=? FOR UPDATE",id);
        if (locked.isEmpty() || ((Number)locked.get(0).get("equipment_id")).longValue()!=equipment) return false;
        var scope=departmentScope.current(action);
        if (!scope.actionGranted()) return false;
        var row=locked.get(0); Object tech=row.get("technician_id");
        return departmentScope.canEquipment(scope,equipment)
            || (participation && (((Number)row.get("reporter_id")).longValue()==scope.userId() || (tech!=null && ((Number)tech).longValue()==scope.userId())))
            || (pending && "REPORTED".equals(row.get("status")));
    }
    public record Report(Long equipmentId, String description) {}
    public record Cost(String category, String description, BigDecimal amount) {}
    public record Completion(LocalDate repairDate, String description, List<Cost> costs, String diagnosis, String faultCategory, Long faultCodeId) {}
    public record Cancellation(String reason) {}
    public record Assignment(Long technicianId, String reason) {}
    public record Trial(String result, String notes) {}
    public record Rating(Integer stars, String remark) {}

    @PreAuthorize("@ss.hasPermi('equipment:order:list')")
    @GetMapping
    public AjaxResult list(@RequestParam(required=false) Long beforeId, @RequestParam(required=false) String status, @RequestParam(required=false) String keyword) {
        if (beforeId != null && beforeId <= 0) return error("分页参数无效");
        if (status != null && !status.isEmpty() && !List.of("REPORTED","ACCEPTED","ARRIVED","TESTING","COMPLETED","CLOSED","CANCELLED").contains(status)) return error("工单状态无效");
        if (keyword != null && keyword.length()>100) return error("搜索内容不能超过 100 字");
        long cursor = beforeId == null ? Long.MAX_VALUE : beforeId;
        StringBuilder sql = new StringBuilder("SELECT w.id,w.equipment_id,e.code,e.name,w.description,w.status,w.reporter_id,w.reporter_name,w.technician_id,DATE_FORMAT(w.repair_date,'%Y-%m-%d') AS repair_date,w.created_at FROM ems_work_order w JOIN ems_equipment e ON e.id=w.equipment_id WHERE w.id<?");
        List<Object> args = new java.util.ArrayList<>();
        args.add(cursor);
        if (status != null && !status.isEmpty()) { sql.append(" AND w.status=?"); args.add(status); }
        if (keyword != null && !keyword.isBlank()) {
            String term=keyword.trim(),pattern="%"+term.replace("!","!!").replace("%","!%").replace("_","!_")+"%";
            sql.append(" AND (e.code LIKE ? ESCAPE '!' OR e.name LIKE ? ESCAPE '!' OR w.description LIKE ? ESCAPE '!' OR CAST(w.id AS CHAR)=?)");
            args.add(pattern);args.add(pattern);args.add(pattern);args.add(term);
        }
        if (!departmentScope.enabled() && !SecurityUtils.hasPermi("equipment:order:viewAll")) {
            long userId = SecurityUtils.getUserId();
            String pending = PendingOrderPermission.current(departmentScope) ? " OR w.status='REPORTED'" : "";
            sql.append(" AND (w.reporter_id=? OR w.technician_id=?").append(pending).append(")");
            args.add(userId); args.add(userId);
        }
        if (departmentScope.enabled()) {
            var scope=departmentScope.current("equipment:order:list");
            var filter=OrderScopeSql.read(scope, PendingOrderPermission.current(departmentScope));
            sql.append(" AND ").append(filter.sql()); args.addAll(filter.args());
        }
        sql.append(" ORDER BY w.id DESC LIMIT 200");
        return success(jdbc.queryForList(sql.toString(), args.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:list')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/{id}")
    public AjaxResult detail(@PathVariable long id) {
        if (departmentScope.enabled() && !mayChange(id,"equipment:order:list",true,PendingOrderPermission.current(departmentScope))) return error("工单不存在或无权查看");
        String sql = "SELECT w.id,w.equipment_id,e.code,e.name,w.description,w.status,w.reporter_id,w.reporter_name,w.technician_id,w.repair_description,DATE_FORMAT(w.repair_date,'%Y-%m-%d') AS repair_date,w.created_at FROM ems_work_order w JOIN ems_equipment e ON e.id=w.equipment_id WHERE w.id=?";
        List<Map<String,Object>> rows;
        if (departmentScope.enabled() || SecurityUtils.hasPermi("equipment:order:viewAll")) rows = jdbc.queryForList(sql, id);
        else if (PendingOrderPermission.current(departmentScope)) rows = jdbc.queryForList(sql + " AND (w.reporter_id=? OR w.technician_id=? OR w.status='REPORTED')", id, SecurityUtils.getUserId(), SecurityUtils.getUserId());
        else rows = jdbc.queryForList(sql + " AND (w.reporter_id=? OR w.technician_id=?)", id, SecurityUtils.getUserId(), SecurityUtils.getUserId());
        if (rows.isEmpty()) return error("工单不存在或无权查看");
        if (departmentScope.enabled()) {
            var filter=OrderScopeSql.read(departmentScope.current("equipment:order:list"), PendingOrderPermission.current(departmentScope));
            var args=new java.util.ArrayList<Object>(); args.add(id); args.addAll(filter.args());
            Long permitted=jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order w WHERE w.id=? AND "+filter.sql(), Long.class, args.toArray());
            if (permitted==null || permitted==0) return error("工单不存在或无权查看");
        }
        Map<String,Object> detail = rows.get(0);
        var cancellation = jdbc.queryForList("SELECT cancellation_type,reason,cancelled_by,cancelled_at FROM ems_work_order_cancellation WHERE work_order_id=?", id);
        if (!cancellation.isEmpty()) detail.put("cancellation", cancellation.get(0));
        detail.put("repairs", jdbc.queryForList("SELECT r.technician_id,DATE_FORMAT(r.repair_date,'%Y-%m-%d') AS repair_date,r.description,r.created_at,d.diagnosis,f.category AS fault_category,fc.code AS fault_code,fc.category AS fault_code_category,fc.part AS fault_part,fc.symptom AS fault_symptom FROM ems_work_order_repair r LEFT JOIN ems_work_order_repair_diagnosis d ON d.repair_id=r.id LEFT JOIN ems_repair_fault_category f ON f.repair_id=r.id LEFT JOIN ems_repair_fault_code fc ON fc.repair_id=r.id WHERE r.work_order_id=? ORDER BY r.id", id));
        var rating = jdbc.queryForList("SELECT stars,remark,rated_at FROM ems_work_order_rating WHERE work_order_id=?", id);
        if (!rating.isEmpty()) detail.put("rating", rating.get(0));
        detail.put("trials", jdbc.queryForList("SELECT technician_id,result,notes,tested_at FROM ems_work_order_trial WHERE work_order_id=? ORDER BY id", id));
        detail.put("assignments", jdbc.queryForList("SELECT from_user_id,to_user_id,operator_id,reason,assigned_at FROM ems_work_order_assignment WHERE work_order_id=? ORDER BY id", id));
        detail.put("transitions", jdbc.queryForList("SELECT from_status,to_status,operator_id,operated_at FROM ems_work_order_log WHERE work_order_id=? ORDER BY id", id));
        return success(detail);
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:report')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/rating")
    public AjaxResult rate(@PathVariable long id, @RequestBody Rating input) {
        if (input.stars()==null || input.stars()<1 || input.stars()>5 || (input.remark()!=null && input.remark().length()>500)) return error("请选择 1 至 5 星，评价不超过 500 字");
        if (departmentScope.enabled() && !departmentScope.current("equipment:order:report").actionGranted()) return error("无权评价");
        int inserted=jdbc.update("INSERT IGNORE INTO ems_work_order_rating(work_order_id,reporter_id,stars,remark) SELECT id,reporter_id,?,? FROM ems_work_order WHERE id=? AND reporter_id=? AND status='CLOSED'",input.stars(),input.remark()==null?"":input.remark().trim(),id,SecurityUtils.getUserId());
        return inserted==1 ? success() : error("工单不可评价或已经评价");
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:report')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping
    public AjaxResult report(@RequestBody Report report) {
        if (report.equipmentId() == null || report.description() == null || report.description().isBlank() || report.description().length() > 2000) return error("请填写设备和故障描述");
        var locked = jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE", report.equipmentId());
        if (locked.isEmpty()) return error("设备不存在或不可报修");
        if (departmentScope.enabled()) { var scope=departmentScope.current("equipment:order:report"); if (!scope.actionGranted() || !departmentScope.canEquipment(scope,report.equipmentId())) return error("设备不存在或无权报修"); }
        var key = new GeneratedKeyHolder();
        int updated = jdbc.update(connection -> {
            PreparedStatement p = connection.prepareStatement("INSERT INTO ems_work_order(equipment_id,reporter_id,description) VALUES (?,?,?)", Statement.RETURN_GENERATED_KEYS);
            p.setLong(1, report.equipmentId()); p.setLong(2, SecurityUtils.getUserId()); p.setString(3, report.description().trim()); return p;
        }, key);
        if (updated != 1 || key.getKey() == null) throw new IllegalStateException("创建报修单失败");
        logTransition(key.getKey().longValue(), "NEW", "REPORTED");
        DingTalkEvents.record(jdbc,key.getKey().longValue(),"REPORTED");
        return success(Map.of("id",key.getKey().longValue()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:report')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/withdraw")
    public AjaxResult withdraw(@PathVariable long id, @RequestBody Cancellation input) {
        if (!mayChange(id,"equipment:order:report",true,false)) return error("工单不存在或无权操作");
        if (input.reason()==null || input.reason().isBlank() || input.reason().length()>1000) return error("请填写撤回原因");
        int changed=jdbc.update("UPDATE ems_work_order SET status='CANCELLED' WHERE id=? AND reporter_id=? AND status='REPORTED'", id, SecurityUtils.getUserId());
        if (changed != 1) return error("只能撤回本人尚未接单的工单");
        jdbc.update("INSERT INTO ems_work_order_cancellation(work_order_id,cancelled_by,cancellation_type,reason) VALUES (?,?,?,?)", id, SecurityUtils.getUserId(), "WITHDRAW", input.reason().trim());
        logTransition(id,"REPORTED","CANCELLED");
        return success();
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:cancel')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/cancel")
    public AjaxResult cancel(@PathVariable long id, @RequestBody Cancellation input) {
        if (!mayChange(id,"equipment:order:cancel",false,false)) return error("工单不存在或无权操作");
        if (input.reason()==null || input.reason().isBlank() || input.reason().length()>1000) return error("请填写取消原因");
        var rows=jdbc.queryForList("SELECT status FROM ems_work_order WHERE id=? FOR UPDATE", id);
        if (rows.isEmpty()) return error("工单不存在");
        String before=String.valueOf(rows.get(0).get("status"));
        if (!List.of("REPORTED","ACCEPTED","ARRIVED","TESTING","COMPLETED").contains(before)) return error("工单已结束");
        jdbc.update("UPDATE ems_work_order SET status='CANCELLED' WHERE id=?",id);
        jdbc.update("INSERT INTO ems_work_order_cancellation(work_order_id,cancelled_by,cancellation_type,reason) VALUES (?,?,?,?)", id, SecurityUtils.getUserId(), "ADMIN", input.reason().trim());
        logTransition(id,before,"CANCELLED");
        return success();
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:assign')")
    @GetMapping("/technicians")
    public AjaxResult technicians() {
        if (departmentScope.enabled() && !departmentScope.current("equipment:order:assign").actionGranted()) return error("无权查看维修人员");
        return success(jdbc.queryForList("SELECT DISTINCT u.user_id,u.user_name,u.nick_name FROM sys_user u JOIN sys_user_role ur ON ur.user_id=u.user_id JOIN sys_role r ON r.role_id=ur.role_id JOIN sys_role_menu rm ON rm.role_id=r.role_id JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE u.status='0' AND u.del_flag='0' AND r.status='0' AND r.del_flag='0' AND m.status='0' AND m.perms='equipment:order:complete' ORDER BY u.user_id LIMIT 500"));
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:assign')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/assign")
    public AjaxResult assign(@PathVariable long id, @RequestBody Assignment input) {
        if (!mayChange(id,"equipment:order:assign",false,false)) return error("工单不存在或无权操作");
        if (input.technicianId()==null || input.technicianId()<=0 || input.reason()==null || input.reason().isBlank() || input.reason().length()>1000) return error("请选择维修人员并填写转派原因");
        var rows=jdbc.queryForList("SELECT status,technician_id FROM ems_work_order WHERE id=? FOR UPDATE",id);
        if (rows.isEmpty() || !List.of("ACCEPTED","ARRIVED","TESTING").contains(rows.get(0).get("status")) || rows.get(0).get("technician_id")==null) return error("只有待到场、维修中或待试运行的工单可以转派");
        long previous=((Number)rows.get(0).get("technician_id")).longValue();
        if (previous==input.technicianId()) return error("目标维修人员与当前人员相同");
        Long eligible=jdbc.queryForObject("SELECT COUNT(DISTINCT u.user_id) FROM sys_user u JOIN sys_user_role ur ON ur.user_id=u.user_id JOIN sys_role r ON r.role_id=ur.role_id JOIN sys_role_menu rm ON rm.role_id=r.role_id JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE u.user_id=? AND u.status='0' AND u.del_flag='0' AND r.status='0' AND r.del_flag='0' AND m.status='0' AND m.perms='equipment:order:complete'", Long.class, input.technicianId());
        if (eligible==null || eligible==0) return error("目标人员不存在、已停用或没有维修权限");
        jdbc.update("UPDATE ems_work_order SET technician_id=? WHERE id=?",input.technicianId(),id);
        jdbc.update("INSERT INTO ems_work_order_assignment(work_order_id,from_user_id,to_user_id,operator_id,reason) VALUES (?,?,?,?,?)",id,previous,input.technicianId(),SecurityUtils.getUserId(),input.reason().trim());
        return success();
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:accept')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/accept")
    public AjaxResult accept(@PathVariable long id) {
        if (!mayChange(id,"equipment:order:accept",false,true)) return error("工单不存在或无权操作");
        int updated = jdbc.update("UPDATE ems_work_order SET status='ACCEPTED', technician_id=? WHERE id=? AND status='REPORTED'", SecurityUtils.getUserId(), id);
        if (updated == 1) logTransition(id, "REPORTED", "ACCEPTED");
        return updated == 1 ? success() : error("工单不存在或已被接单");
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:arrive')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/arrive")
    public AjaxResult arrive(@PathVariable long id) {
        if (!mayChange(id,"equipment:order:arrive",true,false)) return error("工单不存在或无权操作");
        int changed=jdbc.update("UPDATE ems_work_order SET status='ARRIVED' WHERE id=? AND status='ACCEPTED' AND technician_id=?",id,SecurityUtils.getUserId());
        if (changed != 1) return error("工单状态不正确或不是您的工单");
        logTransition(id,"ACCEPTED","ARRIVED");
        return success();
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:complete')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/complete")
    public AjaxResult complete(@PathVariable long id, @RequestBody Completion completion) {
        if (!mayChange(id,"equipment:order:complete",true,false)) return error("工单不存在或无权操作");
        if (completion.repairDate() == null || completion.repairDate().isAfter(LocalDate.now(java.time.ZoneId.of("Asia/Shanghai"))) || completion.description() == null || completion.description().isBlank() || completion.description().length() > 2000 || completion.costs() == null || completion.costs().size() > 100) return error("请填写维修日期、内容和费用明细");
        if (completion.faultCategory()!=null && !List.of("MECHANICAL","ELECTRICAL","HYDRAULIC","CONTROL","OTHER").contains(completion.faultCategory())) return error("故障类别无效");
        if (completion.diagnosis()!=null && completion.diagnosis().length()>2000) return error("诊断原因不能超过 2000 字");
        for (Cost cost : completion.costs()) {
            if (cost == null || cost.category() == null || !List.of("LABOR", "PARTS", "OTHER").contains(cost.category()) || cost.description() == null || cost.description().isBlank() || cost.description().length() > 255 || cost.amount() == null || cost.amount().signum() < 0 || cost.amount().scale() > 2 || cost.amount().compareTo(new BigDecimal("9999999999.99")) > 0) return error("费用明细有误");
        }
        java.util.Map<String,Object> faultCode=null;
        if (completion.faultCodeId()!=null) {
            var candidates=jdbc.queryForList("SELECT id,code,category,part,symptom FROM ems_fault_code WHERE id=? AND status='ACTIVE' FOR UPDATE",completion.faultCodeId());
            if (candidates.isEmpty()) return error("故障代码不存在或已停用");
            faultCode=candidates.get(0);
        }
        int updated = jdbc.update("UPDATE ems_work_order SET status='TESTING',repair_date=?,repair_description=? WHERE id=? AND status='ARRIVED' AND technician_id=?", completion.repairDate(), completion.description().trim(), id, SecurityUtils.getUserId());
        if (updated != 1) return error("工单状态不正确或不是您的工单");
        var repairKey=new GeneratedKeyHolder();
        int repairInserted=jdbc.update(connection -> {
            PreparedStatement p=connection.prepareStatement("INSERT INTO ems_work_order_repair(work_order_id,technician_id,repair_date,description) VALUES (?,?,?,?)",Statement.RETURN_GENERATED_KEYS);
            p.setLong(1,id); p.setLong(2,SecurityUtils.getUserId()); p.setObject(3,completion.repairDate()); p.setString(4,completion.description().trim()); return p;
        },repairKey);
        if (repairInserted!=1 || repairKey.getKey()==null) throw new IllegalStateException("维修记录保存失败");
        for (Cost cost:completion.costs()) {
            var costKey=new GeneratedKeyHolder();
            int costInserted=jdbc.update(c -> { var p=c.prepareStatement("INSERT INTO ems_repair_cost(work_order_id,category,description,amount) VALUES (?,?,?,?)",Statement.RETURN_GENERATED_KEYS);p.setLong(1,id);p.setString(2,cost.category());p.setString(3,cost.description().trim());p.setBigDecimal(4,cost.amount());return p; },costKey);
            if (costInserted!=1 || costKey.getKey()==null) throw new IllegalStateException("维修费用保存失败");
            jdbc.update("INSERT INTO ems_repair_cost_link(cost_id,repair_id) VALUES (?,?)",costKey.getKey().longValue(),repairKey.getKey().longValue());
        }
        if (completion.diagnosis()!=null && !completion.diagnosis().isBlank()) jdbc.update("INSERT INTO ems_work_order_repair_diagnosis(repair_id,diagnosis) VALUES (?,?)",repairKey.getKey().longValue(),completion.diagnosis().trim());
        if (completion.faultCategory()!=null) jdbc.update("INSERT INTO ems_repair_fault_category(repair_id,category) VALUES (?,?)",repairKey.getKey().longValue(),completion.faultCategory());
        if (faultCode!=null) jdbc.update("INSERT INTO ems_repair_fault_code(repair_id,fault_code_id,code,category,part,symptom) VALUES (?,?,?,?,?,?)",repairKey.getKey().longValue(),faultCode.get("id"),faultCode.get("code"),faultCode.get("category"),faultCode.get("part"),faultCode.get("symptom"));
        logTransition(id, "ARRIVED", "TESTING");
        return success();
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:trial')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/trial")
    public AjaxResult trial(@PathVariable long id, @RequestBody Trial input) {
        if (!mayChange(id,"equipment:order:trial",true,false)) return error("工单不存在或无权操作");
        if (input.result()==null || !List.of("PASS","FAIL").contains(input.result()) || (input.notes()!=null && input.notes().length()>1000) || ("FAIL".equals(input.result()) && (input.notes()==null || input.notes().isBlank()))) return error("请选择试运行结果，未通过时请填写说明");
        String next="PASS".equals(input.result()) ? "COMPLETED" : "ARRIVED";
        int changed=jdbc.update("UPDATE ems_work_order SET status=? WHERE id=? AND status='TESTING' AND technician_id=?",next,id,SecurityUtils.getUserId());
        if (changed!=1) return error("工单状态不正确或不是您的工单");
        jdbc.update("INSERT INTO ems_work_order_trial(work_order_id,technician_id,result,notes) VALUES (?,?,?,?)",id,SecurityUtils.getUserId(),input.result(),input.notes());
        logTransition(id,"TESTING",next);
        return success();
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:close')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/close")
    public AjaxResult close(@PathVariable long id) {
        if (!mayChange(id,"equipment:order:close",false,false)) return error("工单不存在或无权操作");
        var rows=jdbc.queryForList("SELECT status FROM ems_work_order WHERE id=? FOR UPDATE",id);
        if (rows.isEmpty() || !"COMPLETED".equals(rows.get(0).get("status"))) return error("工单不存在或尚未完成维修");
        var trials=jdbc.queryForList("SELECT result FROM ems_work_order_trial WHERE work_order_id=? ORDER BY id DESC LIMIT 1",id);
        if (!trials.isEmpty()) {
            Long repairs=jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order_repair WHERE work_order_id=?",Long.class,id);
            if (!"PASS".equals(trials.get(0).get("result")) || repairs==null || repairs==0) return error("最新试运行未通过或缺少维修记录，不能关闭");
        }
        int updated=jdbc.update("UPDATE ems_work_order SET status='CLOSED' WHERE id=? AND status='COMPLETED'",id);
        if (updated!=1) throw new IllegalStateException("关闭工单失败");
        logTransition(id,"COMPLETED","CLOSED");
        DingTalkEvents.record(jdbc,id,"CLOSED");
        return success();
    }

    private void logTransition(long id, String before, String after) {
        jdbc.update("INSERT INTO ems_work_order_log(work_order_id,from_status,to_status,operator_id) VALUES (?,?,?,?)", id, before, after, SecurityUtils.getUserId());
    }

    @PreAuthorize("@ss.hasPermi('equipment:order:list')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/{id}/costs")
    public AjaxResult costs(@PathVariable long id) {
        if (departmentScope.enabled() && !mayChange(id,"equipment:order:list",true,false)) return error("无权查看该工单费用");
        if (departmentScope.enabled()) {
            var filter=OrderScopeSql.read(departmentScope.current("equipment:order:list"),false);
            var args=new java.util.ArrayList<Object>(); args.add(id); args.addAll(filter.args());
            Long permitted=jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order w WHERE w.id=? AND "+filter.sql(), Long.class, args.toArray());
            if (permitted==null || permitted==0) return error("无权查看该工单费用");
        }
        if (!departmentScope.enabled() && !SecurityUtils.hasPermi("equipment:order:viewAll")) {
            Long count = jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order WHERE id=? AND (reporter_id=? OR technician_id=?)", Long.class, id, SecurityUtils.getUserId(), SecurityUtils.getUserId());
            if (count == null || count == 0) return error("无权查看该工单费用");
        }
        List<Map<String,Object>> costs = jdbc.queryForList("SELECT c.id,c.category,c.description,c.amount,DATE_FORMAT(r.repair_date,'%Y-%m-%d') AS repair_date,r.id AS repair_id FROM ems_repair_cost c LEFT JOIN ems_repair_cost_link l ON l.cost_id=c.id LEFT JOIN ems_work_order_repair r ON r.id=l.repair_id WHERE c.work_order_id=? ORDER BY c.id", id);
        return success(costs);
    }
}















