package com.ruoyi.web.controller.equipment;

import java.time.LocalDate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/equipment/maintenance")
public class MaintenanceController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess access;
    public MaintenanceController(JdbcTemplate jdbc, DepartmentScopeAccess access) { this.jdbc = jdbc; this.access=access; }
    private boolean allowed(long equipmentId, String action) { return !access.enabled() || access.canEquipment(access.current(action), equipmentId); }
    private boolean lockPlanEquipment(long id, String action) {
        if (!access.enabled()) return true;
        var rows=jdbc.queryForList("SELECT equipment_id FROM ems_maintenance_plan WHERE id=?",id);
        if (rows.isEmpty()) return false;
        long equipmentId=((Number)rows.get(0).get("equipment_id")).longValue();
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",equipmentId).isEmpty()) return false;
        return allowed(equipmentId,action);
    }
    public record Plan(Long equipmentId, String title, Integer intervalDays, LocalDate nextDue) {}
    public record Completion(LocalDate completedDate, String notes) {}

    @PreAuthorize("@ss.hasPermi('equipment:maintenance:list')")
    @GetMapping
    public AjaxResult list(@RequestParam(required=false) Integer afterActive, @RequestParam(required=false) LocalDate afterDue, @RequestParam(required=false) Long afterId, @RequestParam(required=false) String dueStatus, @RequestParam(required=false) String keyword) {
        boolean noCursor = afterActive == null && afterDue == null && afterId == null;
        if (!noCursor && (afterActive == null || (afterActive != 0 && afterActive != 1) || afterDue == null || afterId == null || afterId <= 0)) return error("分页参数无效");
        if (dueStatus!=null && !dueStatus.isEmpty() && !java.util.List.of("OVERDUE","DUE","UPCOMING","INACTIVE").contains(dueStatus)) return error("到期状态无效");
        if (keyword!=null && keyword.length()>100) return error("搜索内容不能超过 100 字");
        LocalDate today = LocalDate.now(java.time.ZoneId.of("Asia/Shanghai"));
        String columns = "SELECT p.id,p.equipment_id,e.code,e.name,p.title,p.interval_days,DATE_FORMAT(p.next_due,'%Y-%m-%d') AS next_due,p.active,CASE WHEN p.active=0 THEN 'INACTIVE' WHEN p.next_due < ? THEN 'OVERDUE' WHEN p.next_due = ? THEN 'DUE' ELSE 'UPCOMING' END AS due_status FROM ems_maintenance_plan p JOIN ems_equipment e ON e.id=p.equipment_id";
        StringBuilder sql=new StringBuilder(columns).append(" WHERE 1=1");
        var args=new java.util.ArrayList<Object>();args.add(today);args.add(today);
        if(access.enabled()) { var filter=DepartmentScopeSql.equipmentPredicate(access.current("equipment:maintenance:list"),"e.id"); sql.append(" AND (").append(filter.sql()).append(")"); args.addAll(filter.args()); }
        if (dueStatus!=null && !dueStatus.isEmpty()) {
            if ("INACTIVE".equals(dueStatus)) sql.append(" AND p.active=0");
            else {
                sql.append(" AND p.active=1 AND p.next_due ");
                sql.append("OVERDUE".equals(dueStatus)?"< ?":"DUE".equals(dueStatus)?"= ?":"> ?");args.add(today);
            }
        }
        if (keyword!=null && !keyword.isBlank()) {
            String pattern="%"+keyword.trim().replace("!","!!").replace("%","!%").replace("_","!_")+"%";
            sql.append(" AND (e.code LIKE ? ESCAPE '!' OR e.name LIKE ? ESCAPE '!' OR p.title LIKE ? ESCAPE '!')");
            args.add(pattern);args.add(pattern);args.add(pattern);
        }
        if (!noCursor) {
            sql.append(" AND (p.active<? OR (p.active=? AND (p.next_due>? OR (p.next_due=? AND p.id<?))))");
            args.add(afterActive);args.add(afterActive);args.add(afterDue);args.add(afterDue);args.add(afterId);
        }
        sql.append(" ORDER BY p.active DESC,p.next_due,p.id DESC LIMIT 200");
        return success(jdbc.queryForList(sql.toString(),args.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:maintenance:list')")
    @GetMapping("/due-summary")
    public AjaxResult dueSummary() {
        LocalDate today = LocalDate.now(java.time.ZoneId.of("Asia/Shanghai"));
        String sql="SELECT COALESCE(SUM(CASE WHEN p.next_due < ? THEN 1 ELSE 0 END),0) AS overdue, COALESCE(SUM(CASE WHEN p.next_due = ? THEN 1 ELSE 0 END),0) AS due_today FROM ems_maintenance_plan p JOIN ems_equipment e ON e.id=p.equipment_id WHERE p.active=1";
        var args=new java.util.ArrayList<Object>(); args.add(today); args.add(today);
        if(access.enabled()) { var filter=DepartmentScopeSql.equipmentPredicate(access.current("equipment:maintenance:list"),"e.id"); sql+=" AND ("+filter.sql()+")"; args.addAll(filter.args()); }
        return success(jdbc.queryForMap(sql,args.toArray()));
    }
    @PreAuthorize("@ss.hasPermi('equipment:maintenance:add')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping
    public AjaxResult create(@RequestBody Plan plan) {
        if (plan.equipmentId()==null || plan.title()==null || plan.title().isBlank() || plan.title().length()>128 || plan.intervalDays()==null || plan.intervalDays()<1 || plan.intervalDays()>3650 || plan.nextDue()==null) return error("请检查设备、计划名称、周期和日期");
        var equipment=jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE",plan.equipmentId());
        if (equipment.isEmpty() || !allowed(plan.equipmentId(),"equipment:maintenance:add")) return error("设备不存在或无权限");
        jdbc.update("INSERT INTO ems_maintenance_plan(equipment_id,title,interval_days,next_due,created_by) VALUES (?,?,?,?,?)",plan.equipmentId(),plan.title().trim(),plan.intervalDays(),plan.nextDue(),SecurityUtils.getUserId());
        return success();
    }

    public record PlanEdit(String title, Integer intervalDays, LocalDate nextDue) {}

    @PreAuthorize("@ss.hasPermi('equipment:maintenance:edit')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PutMapping("/{id}")
    public AjaxResult edit(@PathVariable long id, @RequestBody PlanEdit plan) {
        if (plan.title()==null || plan.title().isBlank() || plan.title().length()>128 || plan.intervalDays()==null || plan.intervalDays()<1 || plan.intervalDays()>3650 || plan.nextDue()==null) return error("请检查计划名称、周期和日期");
        if (!lockPlanEquipment(id,"equipment:maintenance:edit")) return error("计划不存在或无权限");
        int changed=jdbc.update("UPDATE ems_maintenance_plan SET title=?,interval_days=?,next_due=? WHERE id=? AND active=1",plan.title().trim(),plan.intervalDays(),plan.nextDue(),id);
        return changed==1 ? success() : error("计划不存在、未变更或已停用");
    }

    @PreAuthorize("@ss.hasPermi('equipment:maintenance:edit')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/deactivate")
    public AjaxResult deactivate(@PathVariable long id) {
        if (!lockPlanEquipment(id,"equipment:maintenance:edit")) return error("计划不存在或无权限");
        int changed=jdbc.update("UPDATE ems_maintenance_plan SET active=0 WHERE id=? AND active=1",id);
        return changed==1 ? success() : error("计划不存在或已停用");
    }
    @PreAuthorize("@ss.hasPermi('equipment:maintenance:complete')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/complete")
    public AjaxResult complete(@PathVariable long id,@RequestBody Completion input) {
        if (input.completedDate()==null || input.completedDate().isAfter(LocalDate.now(java.time.ZoneId.of("Asia/Shanghai"))) || input.notes()==null || input.notes().isBlank() || input.notes().length()>2000) return error("请填写有效的完成日期和保养内容");
        if (!lockPlanEquipment(id,"equipment:maintenance:complete")) return error("计划不存在或无权限");
        var plans=jdbc.queryForList("SELECT id,interval_days,next_due FROM ems_maintenance_plan WHERE id=? AND active=1 FOR UPDATE",id);
        if (plans.isEmpty()) return error("计划不存在或已停用");
        LocalDate due=((java.sql.Date)plans.get(0).get("next_due")).toLocalDate();
        if (input.completedDate().isBefore(due)) return error("完成日期不能早于计划到期日");
        int days=((Number)plans.get(0).get("interval_days")).intValue();
        jdbc.update("INSERT INTO ems_maintenance_record(plan_id,completed_by,completed_date,notes) VALUES (?,?,?,?)",id,SecurityUtils.getUserId(),input.completedDate(),input.notes().trim());
        jdbc.update("UPDATE ems_maintenance_plan SET next_due=? WHERE id=?",input.completedDate().plusDays(days),id);
        return success();
    }

    @PreAuthorize("@ss.hasPermi('equipment:maintenance:list')")
    @GetMapping("/{id}/records")
    public AjaxResult records(@PathVariable long id, @RequestParam(required=false) Long beforeId) {
        if (beforeId != null && beforeId <= 0) return error("分页参数无效");
        String sql="SELECT r.id,r.completed_by,DATE_FORMAT(r.completed_date,'%Y-%m-%d') AS completed_date,r.notes,r.created_at FROM ems_maintenance_record r JOIN ems_maintenance_plan p ON p.id=r.plan_id JOIN ems_equipment e ON e.id=p.equipment_id WHERE r.plan_id=? AND r.id<?";
        var args=new java.util.ArrayList<Object>(); args.add(id); args.add(beforeId==null?Long.MAX_VALUE:beforeId);
        if(access.enabled()) { var filter=DepartmentScopeSql.equipmentPredicate(access.current("equipment:maintenance:list"),"e.id"); sql+=" AND ("+filter.sql()+")"; args.addAll(filter.args()); }
        return success(jdbc.queryForList(sql+" ORDER BY r.id DESC LIMIT 200",args.toArray()));
    }
}






