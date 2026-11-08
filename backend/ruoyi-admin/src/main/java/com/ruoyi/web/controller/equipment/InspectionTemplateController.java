package com.ruoyi.web.controller.equipment;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/equipment/assets/{equipmentId}/inspection-template")
public class InspectionTemplateController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess departmentScope;
    public InspectionTemplateController(JdbcTemplate jdbc, DepartmentScopeAccess departmentScope) { this.jdbc = jdbc; this.departmentScope=departmentScope; }
    public record Item(String name, String standard, java.math.BigDecimal lowerBound, java.math.BigDecimal upperBound, String unit) {}
    static boolean validNumber(java.math.BigDecimal value) {
        return value == null || (value.scale() <= 4 && value.abs().compareTo(new java.math.BigDecimal("999999999.9999")) <= 0);
    }
    public record Template(String name, List<Item> items, Boolean requireAbnormalPhoto, Integer ruleSchemaVersion) {}

    @PreAuthorize("@ss.hasPermi('equipment:asset:query')")
    @GetMapping
    @Transactional
    public AjaxResult get(@PathVariable long equipmentId) {
        if (departmentScope.enabled()) {
            if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",equipmentId).isEmpty() || !departmentScope.canEquipment(departmentScope.current("equipment:asset:query"),equipmentId)) return error("设备不存在或无权限");
        }
        var rows = jdbc.queryForList("SELECT t.id,t.name,COALESCE(r.require_abnormal_photo,0) AS photo_required FROM ems_equipment_inspection_template b JOIN ems_inspection_template t ON t.id=b.template_id LEFT JOIN ems_inspection_photo_rule r ON r.template_id=t.id WHERE b.equipment_id=? AND t.status='ACTIVE'", equipmentId);
        if (rows.isEmpty()) return success(Map.of("items", List.of(),"requireAbnormalPhoto",false));
        var template = rows.get(0);
        template.put("requireAbnormalPhoto", ((Number)template.remove("photo_required")).intValue()==1);
        template.put("items", jdbc.queryForList("SELECT i.item_name,i.standard_text,i.sort_order,r.lower_bound,r.upper_bound,r.unit FROM ems_inspection_template_item i LEFT JOIN ems_inspection_numeric_rule r ON r.template_item_id=i.id WHERE i.template_id=? ORDER BY i.sort_order,i.id", template.get("id")));
        return success(template);
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional
    @PutMapping
    public AjaxResult put(@PathVariable long equipmentId, @RequestBody Template input) {
        if (input.name()==null || input.name().isBlank() || input.name().length()>120 || input.items()==null || input.items().isEmpty() || input.items().size()>20) return error("请填写模板名称和 1 至 20 个项目");
        for (Item item:input.items()) {
            if (item==null || item.name()==null || item.name().isBlank() || item.name().length()>120 || (item.standard()!=null && item.standard().length()>500)) return error("模板项目不正确");
            if (!validNumber(item.lowerBound()) || !validNumber(item.upperBound()) || (item.unit()!=null && item.unit().length()>32) || (item.lowerBound()!=null && item.upperBound()!=null && item.lowerBound().compareTo(item.upperBound())>0) || (item.lowerBound()==null && item.upperBound()==null && item.unit()!=null && !item.unit().isBlank())) return error("数值范围或单位不正确");
        }
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE", equipmentId).isEmpty()) return error("设备不存在或已停用");
        if (departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:asset:edit"),equipmentId)) return error("设备不存在或无权限");
        if (input.ruleSchemaVersion()!=null && input.ruleSchemaVersion()!=1) return error("不支持的模板规则版本，请刷新页面");
        if (input.ruleSchemaVersion()==null) {
            Long numericRules=jdbc.queryForObject("SELECT COUNT(*) FROM ems_equipment_inspection_template b JOIN ems_inspection_template_item i ON i.template_id=b.template_id JOIN ems_inspection_numeric_rule n ON n.template_item_id=i.id WHERE b.equipment_id=?",Long.class,equipmentId);
            if (numericRules!=null && numericRules>0) return error("模板包含数值规则，请刷新至新版页面后编辑");
        }
        boolean requirePhoto=Boolean.TRUE.equals(input.requireAbnormalPhoto());
        if (input.requireAbnormalPhoto()==null) {
            Long previous=jdbc.queryForObject("SELECT COUNT(*) FROM ems_equipment_inspection_template b JOIN ems_inspection_photo_rule r ON r.template_id=b.template_id AND r.require_abnormal_photo=1 WHERE b.equipment_id=?",Long.class,equipmentId);
            requirePhoto=previous!=null && previous>0;
        }
        var key = new GeneratedKeyHolder();
        int inserted = jdbc.update(c -> {
            PreparedStatement p = c.prepareStatement("INSERT INTO ems_inspection_template(name,created_by) VALUES (?,?)", Statement.RETURN_GENERATED_KEYS);
            p.setString(1,input.name().trim()); p.setLong(2,SecurityUtils.getUserId()); return p;
        }, key);
        if (inserted!=1 || key.getKey()==null) throw new IllegalStateException("创建巡检模板失败");
        long templateId=key.getKey().longValue();
        if (requirePhoto) jdbc.update("INSERT INTO ems_inspection_photo_rule(template_id,require_abnormal_photo) VALUES (?,1)",templateId);
        var batch = new java.util.ArrayList<Object[]>();
        for (int i=0;i<input.items().size();i++) {
            Item item=input.items().get(i);
            batch.add(new Object[]{templateId,item.name().trim(),item.standard()==null?"":item.standard().trim(),i});
        }
        jdbc.batchUpdate("INSERT INTO ems_inspection_template_item(template_id,item_name,standard_text,sort_order) VALUES (?,?,?,?)",batch);
        var createdItems=jdbc.queryForList("SELECT id FROM ems_inspection_template_item WHERE template_id=? ORDER BY sort_order,id",templateId);
        if (createdItems.size()!=input.items().size()) throw new IllegalStateException("模板项目保存失败");
        var rules = new java.util.ArrayList<Object[]>();
        for (int i=0;i<input.items().size();i++) {
            Item item=input.items().get(i);
            if (item.lowerBound()!=null || item.upperBound()!=null) rules.add(new Object[]{createdItems.get(i).get("id"),item.lowerBound(),item.upperBound(),item.unit()==null?"":item.unit().trim()});
        }
        if (!rules.isEmpty()) jdbc.batchUpdate("INSERT INTO ems_inspection_numeric_rule(template_item_id,lower_bound,upper_bound,unit) VALUES (?,?,?,?)",rules);
        int updated=jdbc.update("UPDATE ems_equipment_inspection_template SET template_id=? WHERE equipment_id=?",templateId,equipmentId);
        if (updated==0) jdbc.update("INSERT INTO ems_equipment_inspection_template(equipment_id,template_id) VALUES (?,?)",equipmentId,templateId);
        return success(Map.of("id",templateId));
    }
}
