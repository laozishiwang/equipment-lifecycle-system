package com.ruoyi.web.controller.equipment;

import java.sql.Statement;
import java.util.Map;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/equipment/fault-codes")
public class FaultCodeController extends BaseController {
    private final JdbcTemplate jdbc;
    public FaultCodeController(JdbcTemplate jdbc) { this.jdbc=jdbc; }
    public record FaultCode(String code,String category,String part,String symptom) {}
    public record Status(String status) {}
    private boolean valid(FaultCode x) {
        return x!=null && x.code()!=null && x.code().matches("[A-Za-z0-9_-]{1,64}") && validText(x.category()) && validText(x.part()) && validText(x.symptom());
    }
    private boolean validText(String x) { return x!=null && !x.isBlank() && x.length()<=80; }
    @PreAuthorize("@ss.hasAnyPermi('equipment:order:complete,equipment:asset:edit')")
    @GetMapping
    public AjaxResult list(@RequestParam(defaultValue="false") boolean all, @RequestParam(required=false) Long afterId) {
        if (all && !SecurityUtils.hasPermi("equipment:asset:edit")) return error("无权查看停用的故障代码");
        if (afterId!=null && afterId<=0) return error("分页参数无效");
        return success(jdbc.queryForList("SELECT id,code,category,part,symptom,status FROM ems_fault_code WHERE id>?"+(all?"":" AND status='ACTIVE'")+" ORDER BY id LIMIT 200",afterId==null?0:afterId));
    }
    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @PostMapping
    public AjaxResult create(@RequestBody FaultCode input) {
        if (!valid(input)) return error("请填写有效的代码、类别、部位和现象");
        try {
            var key=new GeneratedKeyHolder();
            int count=jdbc.update(c -> { var p=c.prepareStatement("INSERT INTO ems_fault_code(code,category,part,symptom,created_by) VALUES (?,?,?,?,?)",Statement.RETURN_GENERATED_KEYS);p.setString(1,input.code());p.setString(2,input.category().trim());p.setString(3,input.part().trim());p.setString(4,input.symptom().trim());p.setLong(5,SecurityUtils.getUserId());return p; },key);
            if (count!=1 || key.getKey()==null) throw new IllegalStateException("故障代码保存失败");
            return success(Map.of("id",key.getKey().longValue()));
        } catch (DuplicateKeyException e) { return error("代码或类别、部位、现象组合已存在"); }
    }
    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @PutMapping("/{id}")
    public AjaxResult update(@PathVariable long id,@RequestBody FaultCode input) {
        if (id<=0 || !valid(input)) return error("请填写有效的代码、类别、部位和现象");
        try {
            int n=jdbc.update("UPDATE ems_fault_code SET code=?,category=?,part=?,symptom=?,updated_by=?,updated_at=NOW() WHERE id=?",input.code(),input.category().trim(),input.part().trim(),input.symptom().trim(),SecurityUtils.getUserId(),id);
            return n==1?success():error("故障代码不存在或内容未改变");
        } catch (DuplicateKeyException e) { return error("代码或类别、部位、现象组合已存在"); }
    }
    @PreAuthorize("@ss.hasPermi('equipment:asset:edit')")
    @PutMapping("/{id}/status")
    public AjaxResult status(@PathVariable long id,@RequestBody Status input) {
        if (id<=0 || input==null || input.status()==null || !java.util.List.of("ACTIVE","INACTIVE").contains(input.status())) return error("状态无效");
        int n=jdbc.update("UPDATE ems_fault_code SET status=?,updated_by=?,updated_at=NOW() WHERE id=?",input.status(),SecurityUtils.getUserId(),id);
        return n==1?success():error("故障代码不存在或状态未改变");
    }
}

