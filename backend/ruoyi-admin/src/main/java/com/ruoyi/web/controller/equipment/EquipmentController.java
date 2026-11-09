package com.ruoyi.web.controller.equipment;

import java.util.List;
import java.util.Map;
import java.time.LocalDate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

/** 设备台账。所有写操作都由服务端检查权限。 */
@RestController
@RequestMapping("/equipment/assets")
public class EquipmentController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess departmentScope;
    @org.springframework.beans.factory.annotation.Value("${ems.public-base-url:}")
    private String publicBaseUrl;
    @org.springframework.beans.factory.annotation.Value("${ems.private-upload-dir:./private-uploads}")
    private String privateUploadDir;
    public EquipmentController(JdbcTemplate jdbc, DepartmentScopeAccess departmentScope) { this.jdbc = jdbc; this.departmentScope = departmentScope; }

    public record Asset(String code, String name, String model, String location, String manufacturer, String serialNumber, LocalDate purchaseDate, LocalDate warrantyUntil, Long deptId) {}

    @PreAuthorize("@ss.hasPermi('equipment:asset:list')")
    @GetMapping
    public AjaxResult list(@RequestParam(defaultValue = "") String keyword, @RequestParam(required=false) Long beforeId, @RequestParam(defaultValue="ALL") String ownership) {
        if (keyword.length() > 128) return error("查询条件过长");
        if (beforeId != null && beforeId <= 0) return error("分页参数无效");
        if (!List.of("ALL","ASSIGNED","UNASSIGNED").contains(ownership)) return error("部门归属筛选无效");
        long cursor = beforeId == null ? Long.MAX_VALUE : beforeId;
        String value = "%" + keyword.trim().replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%";
        String filter = switch (ownership) { case "ASSIGNED" -> " AND ed.equipment_id IS NOT NULL"; case "UNASSIGNED" -> " AND ed.equipment_id IS NULL"; default -> ""; };
        var args = new java.util.ArrayList<Object>(List.of(cursor, value, value));
        if (departmentScope.enabled()) {
            var scoped = DepartmentScopeSql.equipmentPredicate(departmentScope.current("equipment:asset:list"), "e.id");
            filter += " AND (" + scoped.sql() + ")";
            args.addAll(scoped.args());
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
            "SELECT e.id,e.code,e.name,e.model,e.location,e.status,e.created_at,ed.dept_id,d.dept_name FROM ems_equipment e LEFT JOIN ems_equipment_department ed ON ed.equipment_id=e.id LEFT JOIN sys_dept d ON d.dept_id=ed.dept_id WHERE e.id<? AND (e.code LIKE ? ESCAPE '!' OR e.name LIKE ? ESCAPE '!')" + filter + " ORDER BY e.id DESC LIMIT 200", args.toArray());
        return success(rows);
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:list')")
    @GetMapping("/qr-base")
    public AjaxResult qrBase() {
        String value=publicBaseUrl==null?"":publicBaseUrl.trim();
        if (value.isEmpty()) return success(Map.of("baseUrl",""));
        try {
            var uri=new java.net.URI(value);
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost()==null || uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null || !(uri.getPath()==null || uri.getPath().isEmpty() || "/".equals(uri.getPath())) || uri.getPort()>65535) return error("公网二维码地址配置无效");
            return success(Map.of("baseUrl",uri.getScheme()+"://"+uri.getRawAuthority()));
        } catch (java.net.URISyntaxException ex) { return error("公网二维码地址配置无效"); }
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:query')")
    @GetMapping("/{id}")
    public AjaxResult get(@PathVariable long id) {
        String scopeFilter = "";
        var args = new java.util.ArrayList<Object>(); args.add(id);
        if (departmentScope.enabled()) {
            var scoped = DepartmentScopeSql.equipmentPredicate(departmentScope.current("equipment:asset:query"), "e.id");
            scopeFilter = " AND (" + scoped.sql() + ")"; args.addAll(scoped.args());
        }
        var rows = jdbc.queryForList("SELECT e.id,e.code,e.name,e.model,e.location,e.status,e.created_at,p.manufacturer,p.serial_number,DATE_FORMAT(p.purchase_date,'%Y-%m-%d') AS purchase_date,DATE_FORMAT(p.warranty_until,'%Y-%m-%d') AS warranty_until FROM ems_equipment e LEFT JOIN ems_equipment_profile p ON p.equipment_id=e.id WHERE e.id = ?" + scopeFilter, args.toArray());
        return rows.isEmpty() ? error("设备不存在") : success(rows.get(0));
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:history')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/{id}/history")
    public AjaxResult history(@PathVariable long id) {
        if (departmentScope.enabled()) return scopedHistory(id);
        var equipment = jdbc.queryForList("SELECT e.id,e.code,e.name,e.model,e.location,e.status,p.manufacturer,p.serial_number,DATE_FORMAT(p.purchase_date,'%Y-%m-%d') AS purchase_date,DATE_FORMAT(p.warranty_until,'%Y-%m-%d') AS warranty_until FROM ems_equipment e LEFT JOIN ems_equipment_profile p ON p.equipment_id=e.id WHERE e.id=?", id);
        if (equipment.isEmpty()) return error("设备不存在");
        var inspections = jdbc.queryForList("SELECT id,inspector_id,inspected_at,result,remark FROM ems_inspection WHERE equipment_id=? ORDER BY id DESC LIMIT 200", id);
        var orders = jdbc.queryForList("SELECT w.id,w.description,w.status,w.reporter_id,w.technician_id,w.repair_description,DATE_FORMAT(w.repair_date,'%Y-%m-%d') AS repair_date,w.created_at,COALESCE((SELECT SUM(c.amount) FROM ems_repair_cost c WHERE c.work_order_id=w.id),0) AS total_cost FROM ems_work_order w WHERE w.equipment_id=? ORDER BY w.id DESC LIMIT 200", id);
        var locations = jdbc.queryForList("SELECT location,changed_by,changed_at FROM ems_equipment_location_history WHERE equipment_id=? ORDER BY id DESC LIMIT 200", id);
        var maintenance = jdbc.queryForList("SELECT p.title,r.completed_by,DATE_FORMAT(r.completed_date,'%Y-%m-%d') AS completed_date,r.notes FROM ems_maintenance_record r JOIN ems_maintenance_plan p ON p.id=r.plan_id WHERE p.equipment_id=? ORDER BY r.id DESC LIMIT 200", id);
        return success(Map.of("equipment",equipment.get(0),"inspections",inspections,"orders",orders,"locations",locations,"maintenance",maintenance));
    }
    private AjaxResult scopedHistory(long id) {
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",id).isEmpty() ||
            !departmentScope.canEquipment(departmentScope.current("equipment:asset:history"),id)) return error("设备不存在或无权查看");
        var equipment=jdbc.queryForList("SELECT e.id,e.code,e.name,e.model,e.location,e.status,p.manufacturer,p.serial_number,DATE_FORMAT(p.purchase_date,'%Y-%m-%d') AS purchase_date,DATE_FORMAT(p.warranty_until,'%Y-%m-%d') AS warranty_until FROM ems_equipment e LEFT JOIN ems_equipment_profile p ON p.equipment_id=e.id WHERE e.id=?",id);
        List<Map<String,Object>> inspections=List.of(),orders=List.of(),maintenance=List.of();
        if (SecurityUtils.hasPermi("equipment:inspection:list")) {
            var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"i");
            var args=new java.util.ArrayList<Object>(); args.add(id); args.addAll(f.args());
            inspections=jdbc.queryForList("SELECT i.id,i.inspector_id,i.inspected_at,i.result,i.remark FROM ems_inspection i WHERE i.equipment_id=? AND ("+f.sql()+") ORDER BY i.id DESC LIMIT 200",args.toArray());
        }
        if (SecurityUtils.hasPermi("equipment:order:list")) {
            var f=OrderScopeSql.read(departmentScope.current("equipment:order:list"),PendingOrderPermission.current(departmentScope));
            var args=new java.util.ArrayList<Object>(); args.add(id); args.addAll(f.args());
            orders=jdbc.queryForList("SELECT w.id,w.description,w.status,w.reporter_id,w.technician_id,w.repair_description,DATE_FORMAT(w.repair_date,'%Y-%m-%d') AS repair_date,w.created_at,COALESCE((SELECT SUM(c.amount) FROM ems_repair_cost c WHERE c.work_order_id=w.id),0) AS total_cost FROM ems_work_order w WHERE w.equipment_id=? AND ("+f.sql()+") ORDER BY w.id DESC LIMIT 200",args.toArray());
        }
        if (SecurityUtils.hasPermi("equipment:maintenance:list")) {
            var scope=departmentScope.current("equipment:maintenance:list");
            if (departmentScope.canEquipment(scope,id)) maintenance=jdbc.queryForList("SELECT p.title,r.completed_by,DATE_FORMAT(r.completed_date,'%Y-%m-%d') AS completed_date,r.notes FROM ems_maintenance_record r JOIN ems_maintenance_plan p ON p.id=r.plan_id WHERE p.equipment_id=? ORDER BY r.id DESC LIMIT 200",id);
        }
        var locations=jdbc.queryForList("SELECT location,changed_by,changed_at FROM ems_equipment_location_history WHERE equipment_id=? ORDER BY id DESC LIMIT 200",id);
        return success(Map.of("equipment",equipment.get(0),"inspections",inspections,"orders",orders,"locations",locations,"maintenance",maintenance));
    }
    public record AssetUpdate(String name, String model, String location, String status, String manufacturer, String serialNumber, LocalDate purchaseDate, LocalDate warrantyUntil) {}

    /** 汇总删除前需要向操作者说明的业务记录。 */
    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @GetMapping("/{id}/deletion-summary")
    public AjaxResult deletionSummary(@PathVariable long id) {
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=?", id).isEmpty() ||
            (departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:asset:edit"), id))) return error("设备不存在或无权限");
        return success(jdbc.queryForMap("SELECT " +
            "(SELECT COUNT(*) FROM ems_work_order WHERE equipment_id=?) AS orders, " +
            "(SELECT COUNT(*) FROM ems_inspection WHERE equipment_id=?) AS inspections, " +
            "(SELECT COUNT(*) FROM ems_maintenance_plan WHERE equipment_id=?) AS maintenance, " +
            "(SELECT COUNT(*) FROM ems_work_order_photo p JOIN ems_work_order w ON w.id=p.work_order_id WHERE w.equipment_id=?) + " +
            "(SELECT COUNT(*) FROM ems_inspection_photo p JOIN ems_inspection i ON i.id=p.inspection_id WHERE i.equipment_id=?) AS photos, " +
            "(SELECT COUNT(*) FROM ems_repair_cost c JOIN ems_work_order w ON w.id=c.work_order_id WHERE w.equipment_id=?) AS costs, " +
            "(SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE equipment_id=?) AS stagedPhotos", id,id,id,id,id,id,id));
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional
    @DeleteMapping("/{id}")
    public AjaxResult deleteUnused(@PathVariable long id) {
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE", id).isEmpty() ||
            (departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:asset:edit"), id))) return error("设备不存在或无权限");
        Long records=jdbc.queryForObject("SELECT (SELECT COUNT(*) FROM ems_work_order WHERE equipment_id=?) + (SELECT COUNT(*) FROM ems_inspection WHERE equipment_id=?) + (SELECT COUNT(*) FROM ems_maintenance_plan WHERE equipment_id=?) + (SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE equipment_id=?)", Long.class,id,id,id,id);
        if (records != null && records > 0) return error("该设备存在维修、巡检、保养或待处理照片，不能普通删除。请在编辑中将设备设为报废，以保留历史记录。");
        jdbc.update("DELETE FROM ems_equipment_inspection_template WHERE equipment_id=?", id);
        jdbc.update("DELETE FROM ems_equipment_department_history WHERE equipment_id=?", id);
        jdbc.update("DELETE FROM ems_equipment_department WHERE equipment_id=?", id);
        jdbc.update("DELETE FROM ems_equipment_location_history WHERE equipment_id=?", id);
        jdbc.update("DELETE FROM ems_equipment_profile WHERE equipment_id=?", id);
        jdbc.update("DELETE FROM ems_equipment WHERE id=?", id);
        return success();
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional
    @DeleteMapping("/{id}/with-history")
    public AjaxResult deleteWithHistory(@PathVariable long id, @RequestParam String confirmCode) {
        var assets=jdbc.queryForList("SELECT code FROM ems_equipment WHERE id=? FOR UPDATE",id);
        if (assets.isEmpty() || (departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:asset:edit"),id))) return error("设备不存在或无权限");
        if (!String.valueOf(assets.get(0).get("code")).equals(confirmCode)) return error("设备编号不匹配，未删除");
        String orders="SELECT id FROM ems_work_order WHERE equipment_id=?";
        String inspections="SELECT id FROM ems_inspection WHERE equipment_id=?";
        var photos=jdbc.queryForList("SELECT stored_name FROM ems_work_order_photo WHERE work_order_id IN ("+orders+") UNION SELECT stored_name FROM ems_inspection_photo WHERE inspection_id IN ("+inspections+") UNION SELECT stored_name FROM ems_inspection_photo_stage WHERE equipment_id=?",String.class,id,id,id);
        String repairs="SELECT id FROM ems_work_order_repair WHERE work_order_id IN ("+orders+")";
        for (String table : List.of("ems_work_order_repair_diagnosis","ems_repair_fault_category","ems_repair_fault_code","ems_repair_cost_link")) jdbc.update("DELETE FROM "+table+" WHERE repair_id IN ("+repairs+")",id);
        jdbc.update("DELETE FROM ems_repair_cost_link WHERE cost_id IN (SELECT id FROM ems_repair_cost WHERE work_order_id IN ("+orders+"))",id);
        for (String table : List.of("ems_work_order_photo","ems_repair_cost","ems_work_order_trial","ems_work_order_repair","ems_work_order_log","ems_work_order_assignment","ems_work_order_cancellation","ems_work_order_rating")) jdbc.update("DELETE FROM "+table+" WHERE work_order_id IN ("+orders+")",id);
        for (String table : List.of("ems_dingtalk_outbox","ems_mail_outbox")) jdbc.update("DELETE FROM "+table+" WHERE order_id IN ("+orders+")",id);
        jdbc.update("DELETE FROM ems_work_order WHERE equipment_id=?",id);
        jdbc.update("DELETE FROM ems_inspection_numeric_observation WHERE inspection_item_id IN (SELECT id FROM ems_inspection_item WHERE inspection_id IN ("+inspections+"))",id);
        for (String table : List.of("ems_inspection_photo","ems_inspection_item","ems_inspection_template_snapshot")) jdbc.update("DELETE FROM "+table+" WHERE inspection_id IN ("+inspections+")",id);
        jdbc.update("DELETE FROM ems_inspection_photo_stage WHERE equipment_id=?",id);
        jdbc.update("DELETE FROM ems_inspection WHERE equipment_id=?",id);
        jdbc.update("DELETE FROM ems_maintenance_record WHERE plan_id IN (SELECT id FROM ems_maintenance_plan WHERE equipment_id=?)",id);
        jdbc.update("DELETE FROM ems_maintenance_plan WHERE equipment_id=?",id);
        for (String table : List.of("ems_equipment_inspection_template","ems_equipment_department_history","ems_equipment_department","ems_equipment_location_history","ems_equipment_profile")) jdbc.update("DELETE FROM "+table+" WHERE equipment_id=?",id);
        jdbc.update("DELETE FROM ems_equipment WHERE id=?",id);
        var directory=java.nio.file.Path.of(privateUploadDir).toAbsolutePath().normalize();
        for (String name : photos) {
            var target=directory.resolve(name).normalize();
            if (!target.getParent().equals(directory)) throw new IllegalStateException("照片路径无效");
            StagePhotoCommitCleanup.register(target, () -> jdbc.queryForObject("SELECT (SELECT COUNT(*) FROM ems_work_order_photo WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_inspection_photo WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE stored_name=?)",Long.class,name,name,name)==0);
        }
        return success();
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional
    @PutMapping("/{id}")
    public AjaxResult update(@PathVariable long id, @RequestBody AssetUpdate asset) {
        if (asset.name() == null || asset.name().isBlank() || asset.name().length() > 128 ||
            (asset.model() != null && asset.model().length() > 128) ||
            (asset.location() != null && asset.location().length() > 255) ||
            (asset.manufacturer() != null && asset.manufacturer().length() > 128) ||
            (asset.serialNumber() != null && asset.serialNumber().length() > 128) ||
            (asset.purchaseDate() != null && asset.warrantyUntil() != null && asset.warrantyUntil().isBefore(asset.purchaseDate())) ||
            asset.status() == null || !List.of("ACTIVE", "RETIRED").contains(asset.status())) return error("请检查设备信息和状态");
        var locked = jdbc.queryForList("SELECT id,location FROM ems_equipment WHERE id=? FOR UPDATE", id);
        if (locked.isEmpty()) return error("设备不存在");
        if (departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:asset:edit"), id)) return error("设备不存在或无权限");
        int updated = jdbc.update("UPDATE ems_equipment SET name=?,model=?,location=?,status=? WHERE id=? AND (? <> 'RETIRED' OR (NOT EXISTS (SELECT 1 FROM ems_work_order WHERE equipment_id=? AND status NOT IN ('CLOSED','CANCELLED')) AND NOT EXISTS (SELECT 1 FROM ems_maintenance_plan WHERE equipment_id=? AND active=1)))", asset.name().trim(),asset.model(),asset.location(),asset.status(),id,asset.status(),id,id);
        if (updated == 1) saveProfile(id,asset.manufacturer(),asset.serialNumber(),asset.purchaseDate(),asset.warrantyUntil());
        if (updated == 1 && !java.util.Objects.equals(locked.get(0).get("location"), asset.location())) jdbc.update("INSERT INTO ems_equipment_location_history(equipment_id,location,changed_by) VALUES (?,?,?)", id,asset.location(),SecurityUtils.getUserId());
        return updated == 1 ? success() : error("设备不存在、没有变化，或仍有未关闭工单 / 启用的保养计划");
    }
    private void saveProfile(long id, String manufacturer, String serialNumber, LocalDate purchaseDate, LocalDate warrantyUntil) {
        jdbc.update("INSERT INTO ems_equipment_profile(equipment_id,manufacturer,serial_number,purchase_date,warranty_until) VALUES (?,?,?,?,?) ON DUPLICATE KEY UPDATE manufacturer=VALUES(manufacturer),serial_number=VALUES(serial_number),purchase_date=VALUES(purchase_date),warranty_until=VALUES(warranty_until)", id,manufacturer,serialNumber,purchaseDate,warrantyUntil);
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:add')")
    @GetMapping("/create-departments")
    public AjaxResult createDepartments() {
        if (!departmentScope.enabled()) return success(Map.of("required",false,"departments",List.of()));
        var scope=departmentScope.current("equipment:asset:add");
        if (!scope.actionGranted()) return error("无权新增设备");
        String sql="SELECT dept_id,dept_name FROM sys_dept WHERE status='0' AND del_flag='0'";
        var args=new java.util.ArrayList<Object>();
        if (!scope.administrator() && !scope.allDepartments()) {
            var ids=scope.departmentIds().stream().sorted().toList();
            if (ids.isEmpty()) return success(Map.of("required",true,"departments",List.of()));
            sql+=" AND dept_id IN ("+String.join(",",java.util.Collections.nCopies(ids.size(),"?"))+")";
            args.addAll(ids);
        }
        return success(Map.of("required",!scope.administrator(),"departments",jdbc.queryForList(sql+" ORDER BY order_num,dept_id",args.toArray())));
    }
    @PreAuthorize("@ss.hasPermi('equipment:asset:add')")
    @Transactional
    @PostMapping
    public AjaxResult create(@RequestBody Asset asset) {
        if (asset == null) return error("请填写设备资料");
        String departmentName=null;
        if (departmentScope.enabled()) {
            var scope=departmentScope.current("equipment:asset:add");
            if (!scope.actionGranted()) return error("无权新增设备");
            if (asset.deptId()==null && !scope.administrator()) return error("请选择归属部门");
            if (asset.deptId()!=null) {
                if (asset.deptId()<=0 || (!scope.administrator() && !scope.allDepartments() && !scope.departmentIds().contains(asset.deptId()))) return error("部门不存在或无权分配");
                var departments=jdbc.queryForList("SELECT dept_name FROM sys_dept WHERE dept_id=? AND status='0' AND del_flag='0' FOR UPDATE",asset.deptId());
                if (departments.isEmpty()) return error("部门不存在或无权分配");
                departmentName=String.valueOf(departments.get(0).get("dept_name"));
            }
        }
        if (asset.code() == null || asset.code().isBlank() || asset.code().length() > 64 ||
            asset.name() == null || asset.name().isBlank() || asset.name().length() > 128 ||
            (asset.model() != null && asset.model().length() > 128) ||
            (asset.location() != null && asset.location().length() > 255) ||
            (asset.manufacturer() != null && asset.manufacturer().length() > 128) ||
            (asset.serialNumber() != null && asset.serialNumber().length() > 128) ||
            (asset.purchaseDate() != null && asset.warrantyUntil() != null && asset.warrantyUntil().isBefore(asset.purchaseDate()))) return error("请检查设备资料及日期");
        jdbc.update("INSERT INTO ems_equipment(code,name,model,location) VALUES (?,?,?,?)",
            asset.code().trim(), asset.name().trim(), asset.model(), asset.location());
        Long id = jdbc.queryForObject("SELECT id FROM ems_equipment WHERE code=?", Long.class, asset.code().trim());
        saveProfile(id,asset.manufacturer(),asset.serialNumber(),asset.purchaseDate(),asset.warrantyUntil());
        if (departmentName!=null) {
            jdbc.update("INSERT INTO ems_equipment_department(equipment_id,dept_id) VALUES (?,?)",id,asset.deptId());
            jdbc.update("INSERT INTO ems_equipment_department_history(equipment_id,old_dept_id,old_dept_name,new_dept_id,new_dept_name,changed_by) VALUES (?,NULL,NULL,?,?,?)",id,asset.deptId(),departmentName,SecurityUtils.getUserId());
        }
        if (asset.location() != null && !asset.location().isBlank()) jdbc.update("INSERT INTO ems_equipment_location_history(equipment_id,location,changed_by) SELECT id,location,? FROM ems_equipment WHERE code=?", SecurityUtils.getUserId(), asset.code().trim());
        return success();
    }
}
















