package com.ruoyi.web.controller.equipment;

import java.sql.Statement;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;

@RestController
@RequestMapping("/public/field")
public class PublicFieldController extends BaseController {
    private final JdbcTemplate jdbc;
    private final InspectionController inspections;
    private final InspectionPhotoController photos;
    public PublicFieldController(JdbcTemplate jdbc, InspectionController inspections, InspectionPhotoController photos) { this.jdbc=jdbc; this.inspections=inspections; this.photos=photos; }
    public record Report(String name,String description,java.util.List<String> photoTokens) {}
    public record Inspection(String name,String result,String remark,Boolean createOrder,Long templateId,java.util.List<InspectionController.InspectionItem> items,java.util.List<String> photoTokens) {}
    private long actor() { return jdbc.queryForObject("SELECT user_id FROM sys_user WHERE user_name='ems_field_guest' AND status='1' AND del_flag='0'",Long.class); }
    private boolean validName(String name) { return name!=null && !name.isBlank() && name.trim().length()<=50; }
    @GetMapping("/{id}")
    public AjaxResult equipment(@PathVariable long id) {
        var rows=jdbc.queryForList("SELECT id,code,name,model,location,status FROM ems_equipment WHERE id=? AND status='ACTIVE'",id);
        if (rows.isEmpty()) return error("设备不存在或已停用");
        var asset=rows.get(0);
        var templates=jdbc.queryForList("SELECT t.id,t.name,COALESCE(r.require_abnormal_photo,0) AS photo_required FROM ems_equipment_inspection_template b JOIN ems_inspection_template t ON t.id=b.template_id LEFT JOIN ems_inspection_photo_rule r ON r.template_id=t.id WHERE b.equipment_id=? AND t.status='ACTIVE'",id);
        for (var t:templates) t.put("items",jdbc.queryForList("SELECT i.item_name,i.standard_text,i.sort_order,r.lower_bound,r.upper_bound,r.unit FROM ems_inspection_template_item i LEFT JOIN ems_inspection_numeric_rule r ON r.template_item_id=i.id WHERE i.template_id=? ORDER BY i.sort_order,i.id",t.get("id")));
        asset.put("templates",templates);return success(asset);
    }
    @PostMapping("/{id}/reports") @Transactional
    public AjaxResult report(@PathVariable long id,@RequestBody Report input) {
        if (!validName(input.name()) || input.description()==null || input.description().isBlank() || input.description().length()>2000) return error("请填写姓名和故障描述");
        if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE",id).isEmpty()) return error("设备不存在或不可报修");
        long user=actor();var key=new GeneratedKeyHolder();
        jdbc.update(c->{var p=c.prepareStatement("INSERT INTO ems_work_order(equipment_id,reporter_id,reporter_name,description) VALUES (?,?,?,?)",Statement.RETURN_GENERATED_KEYS);p.setLong(1,id);p.setLong(2,user);p.setString(3,input.name().trim());p.setString(4,input.description().trim());return p;},key);
        long order=key.getKey().longValue();jdbc.update("INSERT INTO ems_work_order_log(work_order_id,from_status,to_status,operator_id) VALUES (?,?,?,?)",order,"NEW","REPORTED",user);
        if (input.photoTokens()!=null) {
            if (input.photoTokens().size()>6 || new java.util.HashSet<>(input.photoTokens()).size()!=input.photoTokens().size()) throw new IllegalArgumentException("照片数量或参数不正确");
            for (String token:input.photoTokens()) {
                var rows=jdbc.queryForList("SELECT id,stored_name,media_type,file_size FROM ems_inspection_photo_stage WHERE public_token=? AND equipment_id=? AND uploaded_by=? AND inspection_id IS NULL AND expires_at>NOW() FOR UPDATE",token,id,user);
                if (rows.isEmpty()) throw new IllegalArgumentException("照片不存在或已过期，请重新上传");
                var photo=rows.get(0);
                jdbc.update("INSERT INTO ems_work_order_photo(work_order_id,stored_name,media_type,file_size,uploaded_by) VALUES (?,?,?,?,?)",order,photo.get("stored_name"),photo.get("media_type"),photo.get("file_size"),user);
                jdbc.update("DELETE FROM ems_inspection_photo_stage WHERE id=?",photo.get("id"));
            }
        }
        DingTalkEvents.record(jdbc,order,"REPORTED");
        return success(Map.of("orderId",order));
    }
    @PostMapping("/{id}/photos")
    public AjaxResult photo(@PathVariable long id,@RequestParam("file") org.springframework.web.multipart.MultipartFile file,jakarta.servlet.http.HttpServletResponse response) throws java.io.IOException { return photos.stagePublic(id,file,response,actor()); }
    @PostMapping("/{id}/inspections") @Transactional
    public AjaxResult inspection(@PathVariable long id,@RequestBody Inspection input) {
        if (!validName(input.name())) return error("请填写姓名");
        var ids=new java.util.ArrayList<Long>();
        if (input.photoTokens()!=null) for (String token:input.photoTokens()) {
            var rows=jdbc.queryForList("SELECT id FROM ems_inspection_photo_stage WHERE public_token=? AND equipment_id=? AND inspection_id IS NULL AND expires_at>NOW() FOR UPDATE",token,id);
            if (rows.isEmpty()) return error("照片不存在或已过期，请重新上传");
            ids.add(((Number)rows.get(0).get("id")).longValue());
        }
        return inspections.createPublic(new InspectionController.Inspection(id,input.result(),input.remark(),input.createOrder(),input.items(),input.templateId(),ids),actor(),input.name().trim());
    }
}
