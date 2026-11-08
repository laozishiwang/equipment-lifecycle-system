package com.ruoyi.web.controller.equipment;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;
import java.sql.PreparedStatement;
import java.sql.Statement;
import org.springframework.jdbc.support.GeneratedKeyHolder;

@RestController
@RequestMapping("/equipment/inspections")
public class InspectionController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess departmentScope;
    private final java.nio.file.Path privateStorage;
    public InspectionController(JdbcTemplate jdbc, DepartmentScopeAccess departmentScope, @org.springframework.beans.factory.annotation.Value("${ems.private-upload-dir:./private-uploads}") String directory) {
        this.jdbc = jdbc; this.departmentScope = departmentScope; this.privateStorage=java.nio.file.Path.of(directory).toAbsolutePath().normalize();
    }
    public record InspectionItem(String name, String result, String remark, java.math.BigDecimal measuredValue) {}
    public record Inspection(Long equipmentId, String result, String remark, Boolean createOrder, java.util.List<InspectionItem> items, Long templateId, java.util.List<Long> photoStageIds) {}
    public record OrderRequest(String description) {}

    @PreAuthorize("@ss.hasPermi('equipment:inspection:list') and @ss.hasPermi('equipment:order:report')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/work-order")
    public AjaxResult createWorkOrder(@PathVariable long id, @RequestBody OrderRequest input) {
        if (input == null || input.description() == null || input.description().isBlank() || input.description().length() > 2000) return error("请填写故障描述，最多 2000 字");
        var candidates = (departmentScope.enabled() || SecurityUtils.hasPermi("equipment:inspection:viewAll"))
            ? jdbc.queryForList("SELECT equipment_id FROM ems_inspection WHERE id=?", id)
            : jdbc.queryForList("SELECT equipment_id FROM ems_inspection WHERE id=? AND inspector_id=?", id, SecurityUtils.getUserId());
        if (candidates.isEmpty()) return error("巡检不存在或无权操作");
        long equipmentId = ((Number)candidates.get(0).get("equipment_id")).longValue();
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE", equipmentId).isEmpty()) return error("设备不存在或不可报修");
        var inspections = jdbc.queryForList("SELECT result,inspector_id FROM ems_inspection WHERE id=? AND equipment_id=? FOR UPDATE", id, equipmentId);
        if (inspections.isEmpty() || (!departmentScope.enabled() && !SecurityUtils.hasPermi("equipment:inspection:viewAll") && ((Number)inspections.get(0).get("inspector_id")).longValue()!=SecurityUtils.getUserId())) return error("巡检不存在或无权操作");
        if (departmentScope.enabled()) {
            var inspectionScope=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins");
            var args=new java.util.ArrayList<Object>(); args.add(id); args.addAll(inspectionScope.args());
            Long visible=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection ins WHERE ins.id=? AND ("+inspectionScope.sql()+")",Long.class,args.toArray());
            if (visible==null || visible==0 || !departmentScope.canEquipment(departmentScope.current("equipment:order:report"),equipmentId)) return error("巡检不存在或无权操作");
        }
        if (!"ABNORMAL".equals(inspections.get(0).get("result"))) return error("只有异常巡检可以转报修");
        if (!jdbc.queryForList("SELECT id FROM ems_work_order WHERE inspection_id=? AND status<>'CANCELLED' LIMIT 1 FOR UPDATE", id).isEmpty()) return error("该巡检已有未取消的报修工单");
        var key = new GeneratedKeyHolder();
        int created = jdbc.update(connection -> {
            PreparedStatement p = connection.prepareStatement("INSERT INTO ems_work_order(equipment_id,inspection_id,reporter_id,description) VALUES (?,?,?,?)", Statement.RETURN_GENERATED_KEYS);
            p.setLong(1,equipmentId); p.setLong(2,id); p.setLong(3,SecurityUtils.getUserId()); p.setString(4,input.description().trim()); return p;
        }, key);
        if (created != 1 || key.getKey() == null) throw new IllegalStateException("巡检转报修失败");
        long orderId=key.getKey().longValue();
        jdbc.update("INSERT INTO ems_work_order_log(work_order_id,from_status,to_status,operator_id) VALUES (?,?,?,?)",orderId,"NEW","REPORTED",SecurityUtils.getUserId());
        DingTalkEvents.record(jdbc,orderId,"REPORTED");
        return success(java.util.Map.of("orderId",orderId));
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:list')")
    @GetMapping
    public AjaxResult list(@RequestParam(required=false) Long beforeId, @RequestParam(required=false) String result) {
        if (beforeId != null && beforeId <= 0) return error("分页参数无效");
        if (result != null && !result.isEmpty() && !java.util.List.of("NORMAL","ABNORMAL").contains(result)) return error("巡检结果无效");
        long cursor = beforeId == null ? Long.MAX_VALUE : beforeId;
        var args = new java.util.ArrayList<Object>();
        String canReport="0";
        if (SecurityUtils.hasPermi("equipment:order:report")) {
            String permitted="1=1";
            if (departmentScope.enabled()) {
                var filter=DepartmentScopeSql.equipmentPredicate(departmentScope.current("equipment:order:report"),"e.id");
                permitted=filter.sql(); args.addAll(filter.args());
            }
            canReport="CASE WHEN i.result='ABNORMAL' AND e.status='ACTIVE' AND NOT EXISTS (SELECT 1 FROM ems_work_order pending WHERE pending.inspection_id=i.id AND pending.status<>'CANCELLED') AND ("+permitted+") THEN 1 ELSE 0 END";
        }
        StringBuilder sql = new StringBuilder("SELECT i.id,i.equipment_id,e.code,e.name,i.inspector_id,i.inspector_name,i.inspected_at,i.result,i.remark,w.id AS order_id,w.status AS order_status," + canReport + " AS can_report FROM ems_inspection i JOIN ems_equipment e ON e.id=i.equipment_id LEFT JOIN ems_work_order w ON w.id=(SELECT MAX(wo.id) FROM ems_work_order wo WHERE wo.inspection_id=i.id)");
        if (!SecurityUtils.hasPermi("equipment:order:list")) sql.append(" AND 1=0");
        else if (departmentScope.enabled()) {
            var filter=OrderScopeSql.read(departmentScope.current("equipment:order:list"),PendingOrderPermission.current(departmentScope));
            sql.append(" AND (").append(filter.sql()).append(")"); args.addAll(filter.args());
        } else if (!departmentScope.enabled() && !SecurityUtils.hasPermi("equipment:order:viewAll")) {
            sql.append(" AND (w.reporter_id=? OR w.technician_id=?");
            args.add(SecurityUtils.getUserId()); args.add(SecurityUtils.getUserId());
            if (SecurityUtils.hasPermi("equipment:order:accept")) sql.append(" OR w.status='REPORTED'");
            sql.append(")");
        }
        sql.append(" WHERE i.id<?"); args.add(cursor);
        if (result != null && !result.isEmpty()) { sql.append(" AND i.result=?"); args.add(result); }
        if (!departmentScope.enabled() && !SecurityUtils.hasPermi("equipment:inspection:viewAll")) { sql.append(" AND i.inspector_id=?"); args.add(SecurityUtils.getUserId()); }
        if (departmentScope.enabled()) {
            var scope=departmentScope.current("equipment:inspection:list");
            var filter=InspectionScopeSql.read(scope,"i");
            sql.append(" AND (").append(filter.sql()).append(")");
            args.addAll(filter.args());
        }
        sql.append(" ORDER BY i.id DESC LIMIT 200");
        return success(jdbc.queryForList(sql.toString(),args.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:list') and @ss.hasPermi('equipment:order:list')")
    @GetMapping("/{id}/work-orders")
    public AjaxResult workOrders(@PathVariable long id, @RequestParam(required=false) Long beforeId) {
        if (beforeId != null && beforeId <= 0) return error("分页参数无效");
        Long visible;
        if (departmentScope.enabled()) {
            var filter=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins");
            var params=new java.util.ArrayList<Object>(); params.add(id); params.addAll(filter.args());
            visible=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection ins WHERE ins.id=? AND ("+filter.sql()+")",Long.class,params.toArray());
        } else {
            visible=SecurityUtils.hasPermi("equipment:inspection:viewAll")
                ? jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=?",Long.class,id)
                : jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=? AND inspector_id=?",Long.class,id,SecurityUtils.getUserId());
        }
        if (visible == null || visible == 0) return error("巡检不存在或无权查看");
        StringBuilder sql=new StringBuilder("SELECT w.id,w.status,w.description,w.created_at FROM ems_work_order w WHERE w.inspection_id=? AND w.id<?");
        var args=new java.util.ArrayList<Object>(); args.add(id); args.add(beforeId==null?Long.MAX_VALUE:beforeId);
        if (!departmentScope.enabled() && !SecurityUtils.hasPermi("equipment:order:viewAll")) {
            sql.append(" AND (w.reporter_id=? OR w.technician_id=?"); args.add(SecurityUtils.getUserId()); args.add(SecurityUtils.getUserId());
            if (SecurityUtils.hasPermi("equipment:order:accept")) sql.append(" OR w.status='REPORTED'");
            sql.append(")");
        }
        if (departmentScope.enabled()) {
            var inspectionFilter=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins");
            sql.append(" AND EXISTS (SELECT 1 FROM ems_inspection ins WHERE ins.id=w.inspection_id AND (").append(inspectionFilter.sql()).append("))");
            args.addAll(inspectionFilter.args());
            var orderFilter=OrderScopeSql.read(departmentScope.current("equipment:order:list"),PendingOrderPermission.current(departmentScope));
            sql.append(" AND (").append(orderFilter.sql()).append(")"); args.addAll(orderFilter.args());
        }
        sql.append(" ORDER BY w.id DESC LIMIT 20");
        return success(jdbc.queryForList(sql.toString(),args.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:list')")
    @GetMapping("/{id}/items")
    public AjaxResult items(@PathVariable long id) {
        Long count;
        if (departmentScope.enabled()) {
            var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins");
            var params=new java.util.ArrayList<Object>(); params.add(id); params.addAll(f.args());
            count=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection ins WHERE ins.id=? AND ("+f.sql()+")",Long.class,params.toArray());
        } else count=SecurityUtils.hasPermi("equipment:inspection:viewAll")
            ? jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=?", Long.class, id)
            : jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=? AND inspector_id=?", Long.class, id, SecurityUtils.getUserId());
        if (count == null || count == 0) return error("巡检不存在或无权查看");
        String filter=""; var params=new java.util.ArrayList<Object>(); params.add(id);
        if (departmentScope.enabled()) { var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins"); filter=" AND EXISTS (SELECT 1 FROM ems_inspection ins WHERE ins.id=i.inspection_id AND ("+f.sql()+"))"; params.addAll(f.args()); }
        return success(jdbc.queryForList("SELECT i.id,i.item_name,i.result,i.remark,n.measured_value,n.lower_bound,n.upper_bound,n.unit FROM ems_inspection_item i LEFT JOIN ems_inspection_numeric_observation n ON n.inspection_item_id=i.id WHERE i.inspection_id=?"+filter+" ORDER BY i.id", params.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:list')")
    @GetMapping("/{id}/template-snapshot")
    public AjaxResult templateSnapshot(@PathVariable long id) {
        Long count;
        if (departmentScope.enabled()) {
            var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins");
            var params=new java.util.ArrayList<Object>(); params.add(id); params.addAll(f.args());
            count=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection ins WHERE ins.id=? AND ("+f.sql()+")",Long.class,params.toArray());
        } else count=SecurityUtils.hasPermi("equipment:inspection:viewAll")
            ? jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=?", Long.class, id)
            : jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=? AND inspector_id=?", Long.class, id, SecurityUtils.getUserId());
        if (count == null || count == 0) return error("巡检不存在或无权查看");
        String filter=""; var params=new java.util.ArrayList<Object>(); params.add(id);
        if (departmentScope.enabled()) { var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins"); filter=" AND EXISTS (SELECT 1 FROM ems_inspection ins WHERE ins.id=s.inspection_id AND ("+f.sql()+"))"; params.addAll(f.args()); }
        return success(jdbc.queryForList("SELECT s.template_id,s.template_name,s.item_order,s.item_name,s.standard_text FROM ems_inspection_template_snapshot s WHERE s.inspection_id=?"+filter+" ORDER BY s.item_order", params.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:add')")
    @Transactional
    @PostMapping
    public AjaxResult create(@RequestBody Inspection input) {
        return createInternal(input, SecurityUtils.getUserId(), null, false);
    }

    @Transactional
    public AjaxResult createPublic(Inspection input, long actorId, String actorName) {
        return createInternal(input, actorId, actorName, true);
    }

    private AjaxResult createInternal(Inspection input, long actorId, String actorName, boolean publicEntry) {
        if (input.equipmentId() == null || input.result() == null || !(input.result().equals("NORMAL") || input.result().equals("ABNORMAL")) || (input.remark() != null && input.remark().length() > 1000)) return error("巡检数据不正确");
        if (input.items() != null) {
            if (input.items().size() > 20) return error("巡检项目不能超过 20 项");
            for (InspectionItem item : input.items()) {
                if (item == null || item.name() == null || item.name().isBlank() || item.name().length() > 120 || item.result() == null || !java.util.List.of("NORMAL", "ABNORMAL").contains(item.result()) || (item.remark() != null && item.remark().length() > 500)) return error("巡检项目数据不正确");
                if ("ABNORMAL".equals(item.result()) && !"ABNORMAL".equals(input.result())) return error("存在异常项目时巡检结果必须为异常");
            }
        }
        java.util.List<Long> photoIds=input.photoStageIds()==null?java.util.List.of():input.photoStageIds();
        if (photoIds.size()>6 || photoIds.stream().anyMatch(id->id==null || id<=0) || new java.util.HashSet<>(photoIds).size()!=photoIds.size()) return error("临时照片参数不正确");
        if (Boolean.TRUE.equals(input.createOrder()) && (!input.result().equals("ABNORMAL") || input.remark() == null || input.remark().isBlank())) return error("异常转报修时请填写异常说明");
        if (Boolean.TRUE.equals(input.createOrder()) && !(publicEntry || com.ruoyi.common.utils.SecurityUtils.hasPermi("equipment:order:report"))) return error("没有提交报修的权限");
        var locked = jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE", input.equipmentId());
        if (locked.isEmpty()) return error("设备不存在或不可巡检");
        if (!publicEntry && departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:inspection:add"), input.equipmentId())) return error("设备不存在或无权巡检");
        if (!publicEntry && departmentScope.enabled() && Boolean.TRUE.equals(input.createOrder()) && !departmentScope.canEquipment(departmentScope.current("equipment:order:report"), input.equipmentId())) return error("设备不存在或无权报修");
        if (input.templateId() == null) {
            Long bound = jdbc.queryForObject("SELECT COUNT(*) FROM ems_equipment_inspection_template b JOIN ems_inspection_template t ON t.id=b.template_id AND t.status='ACTIVE' WHERE b.equipment_id=?", Long.class, input.equipmentId());
            if (bound != null && bound > 0) return error("该设备已配置巡检模板，请刷新后使用模板巡检");
        }
        java.util.List<java.util.Map<String,Object>> templateRows = java.util.List.of();
        if (input.templateId() != null) {
            templateRows = jdbc.queryForList("SELECT t.id,t.name,i.item_name,i.standard_text,r.lower_bound,r.upper_bound,r.unit FROM ems_equipment_inspection_template b JOIN ems_inspection_template t ON t.id=b.template_id AND t.status='ACTIVE' JOIN ems_inspection_template_item i ON i.template_id=t.id LEFT JOIN ems_inspection_numeric_rule r ON r.template_item_id=i.id WHERE b.equipment_id=? AND t.id=? ORDER BY i.sort_order,i.id", input.equipmentId(),input.templateId());
            if (templateRows.isEmpty() || input.items()==null || input.items().size()<templateRows.size()) return error("巡检模板已变更或项目不完整，请刷新后重试");
            for (int i=0;i<templateRows.size();i++) if (!input.items().get(i).name().trim().equals(templateRows.get(i).get("item_name"))) return error("模板项目不匹配，请刷新后重试");
        }
        if (input.items()!=null) for (int i=0;i<input.items().size();i++) {
            InspectionItem item=input.items().get(i);
            var rule=i<templateRows.size()?templateRows.get(i):null;
            java.math.BigDecimal low=rule==null?null:(java.math.BigDecimal)rule.get("lower_bound");
            java.math.BigDecimal high=rule==null?null:(java.math.BigDecimal)rule.get("upper_bound");
            boolean numeric=low!=null || high!=null;
            if (numeric) {
                var value=item.measuredValue();
                if (value==null || !InspectionTemplateController.validNumber(value)) return error("请填写有效的检查数值");
                boolean abnormal=(low!=null && value.compareTo(low)<0) || (high!=null && value.compareTo(high)>0);
                if (!item.result().equals(abnormal?"ABNORMAL":"NORMAL")) return error("数值与检查结果不一致");
            } else if (item.measuredValue()!=null) return error("非数值项目不能填写读数");
        }
        if ("ABNORMAL".equals(input.result()) && input.templateId()!=null) {
            Long required=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection_photo_rule WHERE template_id=? AND require_abnormal_photo=1",Long.class,input.templateId());
            if (required!=null && required>0 && photoIds.isEmpty()) return error("该模板要求异常巡检上传照片");
        }
        var stagedPhotos=new java.util.ArrayList<java.util.Map<String,Object>>();
        for (Long photoId:photoIds.stream().sorted().toList()) {
            var staged=jdbc.queryForList("SELECT id,stored_name,media_type,file_size FROM ems_inspection_photo_stage WHERE id=? AND equipment_id=? AND uploaded_by=? AND inspection_id IS NULL AND expires_at>NOW() FOR UPDATE",photoId,input.equipmentId(),actorId);
            if (staged.isEmpty()) return error("临时照片不存在、已过期或已使用，请重新上传");
            var photo=staged.get(0); String storedName=String.valueOf(photo.get("stored_name"));
            if (!storedName.matches("[0-9a-f-]{36}\\.(jpg|png)")) return error("临时照片无效，请重新上传");
            var path=privateStorage.resolve(storedName).normalize();
            try {
                if (!path.getParent().equals(privateStorage) || !java.nio.file.Files.isRegularFile(path) || java.nio.file.Files.size(path)!=((Number)photo.get("file_size")).longValue()) return error("临时照片不可用，请重新上传");
            } catch (java.io.IOException ex) { return error("临时照片不可用，请重新上传"); }
            stagedPhotos.add(photo);
        }
        var key = new GeneratedKeyHolder();
        int inserted = jdbc.update(connection -> {
            PreparedStatement p = connection.prepareStatement("INSERT INTO ems_inspection(equipment_id,inspector_id,inspected_at,result,remark) SELECT id,?,NOW(),?,? FROM ems_equipment WHERE id=? AND status='ACTIVE'", Statement.RETURN_GENERATED_KEYS);
            p.setLong(1, actorId); p.setString(2, input.result()); p.setString(3, input.remark()); p.setLong(4, input.equipmentId()); return p;
        }, key);
        if (inserted != 1 || key.getKey() == null) throw new IllegalStateException("创建巡检记录失败");
        if (input.items() != null) for (int i=0;i<input.items().size();i++) {
            InspectionItem item=input.items().get(i);
            var itemKey=new GeneratedKeyHolder();
            int count=jdbc.update(c -> {
                PreparedStatement p=c.prepareStatement("INSERT INTO ems_inspection_item(inspection_id,item_name,result,remark) VALUES (?,?,?,?)",Statement.RETURN_GENERATED_KEYS);
                p.setLong(1,key.getKey().longValue()); p.setString(2,item.name().trim()); p.setString(3,item.result()); p.setString(4,item.remark()==null?"":item.remark().trim()); return p;
            },itemKey);
            if(count!=1 || itemKey.getKey()==null) throw new IllegalStateException("巡检项目保存失败");
            if (item.measuredValue()!=null) {
                var rule=templateRows.get(i);
                jdbc.update("INSERT INTO ems_inspection_numeric_observation(inspection_item_id,measured_value,lower_bound,upper_bound,unit) VALUES (?,?,?,?,?)",itemKey.getKey().longValue(),item.measuredValue(),rule.get("lower_bound"),rule.get("upper_bound"),rule.get("unit"));
            }
        }
        if (!templateRows.isEmpty()) {
            var snapshot = new java.util.ArrayList<Object[]>();
            for (int i=0;i<templateRows.size();i++) {
                var row=templateRows.get(i);
                snapshot.add(new Object[]{key.getKey().longValue(),input.templateId(),row.get("name"),i,row.get("item_name"),row.get("standard_text")});
            }
            jdbc.batchUpdate("INSERT INTO ems_inspection_template_snapshot(inspection_id,template_id,template_name,item_order,item_name,standard_text) VALUES (?,?,?,?,?,?)",snapshot);
        }
        for (var photo:stagedPhotos) {
            int photoInserted=jdbc.update("INSERT INTO ems_inspection_photo(inspection_id,stored_name,media_type,file_size,uploaded_by) VALUES (?,?,?,?,?)",key.getKey().longValue(),photo.get("stored_name"),photo.get("media_type"),photo.get("file_size"),actorId);
            int bound=jdbc.update("UPDATE ems_inspection_photo_stage SET inspection_id=? WHERE id=? AND inspection_id IS NULL",key.getKey().longValue(),photo.get("id"));
            if (photoInserted!=1 || bound!=1) throw new IllegalStateException("巡检照片绑定失败");
        }
        Long createdOrderId = null;
        if (Boolean.TRUE.equals(input.createOrder())) {
            var orderKey = new GeneratedKeyHolder();
            int created = jdbc.update(connection -> {
                PreparedStatement p = connection.prepareStatement("INSERT INTO ems_work_order(equipment_id,inspection_id,reporter_id,description) VALUES (?,?,?,?)", Statement.RETURN_GENERATED_KEYS);
                p.setLong(1, input.equipmentId()); p.setLong(2, key.getKey().longValue()); p.setLong(3, actorId); p.setString(4, input.remark().trim()); return p;
            }, orderKey);
            if (created != 1 || orderKey.getKey() == null) throw new IllegalStateException("巡检转报修失败");
            createdOrderId = orderKey.getKey().longValue();
            jdbc.update("INSERT INTO ems_work_order_log(work_order_id,from_status,to_status,operator_id) VALUES (?,?,?,?)", createdOrderId, "NEW", "REPORTED", actorId);
            DingTalkEvents.record(jdbc,createdOrderId,"REPORTED");
        }
        if (publicEntry) { jdbc.update("UPDATE ems_inspection SET inspector_name=? WHERE id=?", actorName, key.getKey().longValue()); if (createdOrderId != null) jdbc.update("UPDATE ems_work_order SET reporter_name=? WHERE id=?",actorName,createdOrderId); }
        return createdOrderId == null ? success(java.util.Map.of("inspectionId",key.getKey().longValue())) : success(java.util.Map.of("inspectionId",key.getKey().longValue(),"orderId",createdOrderId));
    }
}





