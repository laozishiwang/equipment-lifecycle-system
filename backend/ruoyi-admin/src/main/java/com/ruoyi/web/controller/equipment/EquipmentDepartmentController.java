package com.ruoyi.web.controller.equipment;

import java.util.Map;
import java.util.Objects;
import java.util.List;
import java.util.ArrayList;
import java.util.TreeSet;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

/** Department ownership metadata; this does not implement data scope. */
@RestController
@RequestMapping("/equipment/assets")
public class EquipmentDepartmentController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess access;
    public EquipmentDepartmentController(JdbcTemplate jdbc, DepartmentScopeAccess access) { this.jdbc=jdbc; this.access=access; }
    private boolean targetAllowed(DepartmentScopeAccess.Scope scope, Long deptId) {
        if (scope.administrator()) return true;
        return scope.actionGranted() && deptId!=null && (scope.allDepartments() || scope.departmentIds().contains(deptId));
    }
    public record DepartmentChange(Long deptId, Boolean clear) {}
    public record BatchDepartmentChange(Long deptId, List<Long> equipmentIds) {}

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @GetMapping("/departments")
    public AjaxResult departments() {
        String sql="SELECT dept_id,dept_name,parent_id FROM sys_dept WHERE status='0' AND del_flag='0'";
        var args=new ArrayList<Object>();
        if (access.enabled()) {
            var scope=access.current("equipment:asset:edit");
            if (!scope.actionGranted()) return success(List.of());
            if (!scope.administrator() && !scope.allDepartments()) {
                var ids=scope.departmentIds().stream().sorted().toList();
                if (ids.isEmpty()) return success(List.of());
                sql+=" AND dept_id IN ("+String.join(",",java.util.Collections.nCopies(ids.size(),"?"))+")";
                args.addAll(ids);
            }
        }
        return success(jdbc.queryForList(sql+" ORDER BY order_num,dept_id",args.toArray()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/departments/batch")
    public AjaxResult assignUnassigned(@RequestBody BatchDepartmentChange input) {
        if (input==null || input.deptId()==null || input.deptId()<=0 || input.equipmentIds()==null || input.equipmentIds().isEmpty() || input.equipmentIds().size()>100 || input.equipmentIds().stream().anyMatch(id->id==null || id<=0)) return error("请选择部门及 1 至 100 台未分配设备");
        if (access.enabled()) {
            var scope=access.current("equipment:asset:edit");
            if (!scope.administrator() || !targetAllowed(scope,input.deptId())) return error("无权限分配未归属设备");
        }
        var ids=new TreeSet<>(input.equipmentIds());
        if (ids.size()!=input.equipmentIds().size()) return error("设备列表包含重复项");
        String placeholders=String.join(",",java.util.Collections.nCopies(ids.size(),"?"));
        Object[] parameters=ids.toArray();
        var locked=jdbc.queryForList("SELECT id FROM ems_equipment WHERE id IN ("+placeholders+") ORDER BY id FOR UPDATE",parameters);
        if (locked.size()!=ids.size()) return error("设备不存在，请刷新后重试");
        if (!jdbc.queryForList("SELECT equipment_id FROM ems_equipment_department WHERE equipment_id IN ("+placeholders+") ORDER BY equipment_id FOR UPDATE",parameters).isEmpty()) return error("部分设备已设置部门，请刷新后重试");
        var department=jdbc.queryForList("SELECT dept_name FROM sys_dept WHERE dept_id=? AND status='0' AND del_flag='0' FOR UPDATE",input.deptId());
        if (department.isEmpty()) return error("部门不存在或已停用");
        String name=String.valueOf(department.get(0).get("dept_name"));
        long actor=SecurityUtils.getUserId();
        List<Object[]> associations=new ArrayList<>(), histories=new ArrayList<>();
        for (long id:ids) { associations.add(new Object[]{id,input.deptId()}); histories.add(new Object[]{id,input.deptId(),name,actor}); }
        jdbc.batchUpdate("INSERT INTO ems_equipment_department(equipment_id,dept_id) VALUES (?,?)",associations);
        jdbc.batchUpdate("INSERT INTO ems_equipment_department_history(equipment_id,old_dept_id,old_dept_name,new_dept_id,new_dept_name,changed_by) VALUES (?,NULL,NULL,?,?,?)",histories);
        return success(Map.of("assigned",ids.size()));
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/{id}/department")
    public AjaxResult get(@PathVariable long id) {
        var asset=jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=?"+(access.enabled()?" FOR UPDATE":""),id);
        if (asset.isEmpty()) return error("设备不存在");
        if(access.enabled() && !access.canEquipment(access.current("equipment:asset:edit"),id)) return error("设备不存在或无权限");
        var current=jdbc.queryForList("SELECT d.dept_id,d.dept_name,d.status,d.del_flag FROM ems_equipment_department ed JOIN sys_dept d ON d.dept_id=ed.dept_id WHERE ed.equipment_id=?",id);
        var history=jdbc.queryForList("SELECT old_dept_id,old_dept_name,new_dept_id,new_dept_name,changed_by,changed_at FROM ems_equipment_department_history WHERE equipment_id=? ORDER BY id DESC LIMIT 200",id);
        return success(Map.of("current",current,"history",history));
    }

    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PutMapping("/{id}/department")
    public AjaxResult set(@PathVariable long id, @RequestBody DepartmentChange input) {
        if (input==null || (input.deptId()==null && !Boolean.TRUE.equals(input.clear())) || (input.deptId()!=null && Boolean.TRUE.equals(input.clear()))) return error("请选择部门或明确清除归属");
        if (input.deptId()!=null && input.deptId()<=0) return error("部门无效");
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",id).isEmpty()) return error("设备不存在");
        var old=jdbc.queryForList("SELECT d.dept_id,d.dept_name FROM ems_equipment_department ed JOIN sys_dept d ON d.dept_id=ed.dept_id WHERE ed.equipment_id=?",id);
        Long oldId=old.isEmpty()?null:((Number)old.get(0).get("dept_id")).longValue();
        String oldName=old.isEmpty()?null:String.valueOf(old.get(0).get("dept_name"));
        Long next=input.deptId();
        if(access.enabled()) {
            var scope=access.current("equipment:asset:edit");
            if ((oldId==null && !scope.administrator()) || (oldId!=null && !access.canEquipment(scope,id)) || !targetAllowed(scope,next)) return error("设备不存在或无权限");
        }
        if (Objects.equals(oldId,next)) return success();
        String nextName=null;
        if (next!=null) {
            var departments=jdbc.queryForList("SELECT dept_name FROM sys_dept WHERE dept_id=? AND status='0' AND del_flag='0' FOR UPDATE",next);
            if (departments.isEmpty()) return error("部门不存在或已停用");
            nextName=String.valueOf(departments.get(0).get("dept_name"));
        }
        if (next==null) jdbc.update("DELETE FROM ems_equipment_department WHERE equipment_id=?",id);
        else jdbc.update("INSERT INTO ems_equipment_department(equipment_id,dept_id) VALUES (?,?) ON DUPLICATE KEY UPDATE dept_id=VALUES(dept_id)",id,next);
        jdbc.update("INSERT INTO ems_equipment_department_history(equipment_id,old_dept_id,old_dept_name,new_dept_id,new_dept_name,changed_by) VALUES (?,?,?,?,?,?)",id,oldId,oldName,next,nextName,SecurityUtils.getUserId());
        return success();
    }
}
