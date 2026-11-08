package com.ruoyi.web.controller.equipment;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.UUID;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.SecurityUtils;

@RestController
@RequestMapping("/equipment/inspections")
public class InspectionPhotoController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess departmentScope;
    private final Path storage;
    private final PrivatePhotoStorage photoStorage;
    private final org.springframework.transaction.support.TransactionTemplate transactions;
    public InspectionPhotoController(JdbcTemplate jdbc, DepartmentScopeAccess departmentScope, org.springframework.transaction.PlatformTransactionManager manager, PrivatePhotoStorage photoStorage, @Value("${ems.private-upload-dir:./private-uploads}") String directory) {
        this.jdbc=jdbc; this.departmentScope=departmentScope; this.photoStorage=photoStorage; this.storage=Path.of(directory).toAbsolutePath().normalize();
        this.transactions=new org.springframework.transaction.support.TransactionTemplate(manager);
        this.transactions.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);
    }
    private boolean canView(long id) {
        Long count=SecurityUtils.hasPermi("equipment:inspection:viewAll")
            ? jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=?",Long.class,id)
            : jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection WHERE id=? AND inspector_id=?",Long.class,id,SecurityUtils.getUserId());
        return count!=null && count>0;
    }
    @PreAuthorize("@ss.hasPermi('equipment:inspection:add')")
    @PostMapping("/staged-photos")
    public AjaxResult stage(@RequestParam long equipmentId, @RequestParam("file") MultipartFile file, HttpServletResponse response) throws IOException {
        return stageInternal(equipmentId,file,response,SecurityUtils.getUserId(),false);
    }
    public AjaxResult stagePublic(long equipmentId, MultipartFile file, HttpServletResponse response, long actorId) throws IOException {
        return stageInternal(equipmentId,file,response,actorId,true);
    }
    private AjaxResult stageInternal(long equipmentId, MultipartFile file, HttpServletResponse response, long actorId, boolean publicEntry) throws IOException {
        if (file.isEmpty() || file.getSize()>WorkOrderPhotoController.MAX_BYTES) return error("照片大小必须在 5 MB 以内");
        Long count=jdbc.queryForObject("SELECT COUNT(*) FROM ems_equipment WHERE id=? AND status='ACTIVE'",Long.class,equipmentId);
        if (count==null || count==0) return error("设备不存在或不可巡检");
        if (!WorkOrderPhotoController.IMAGE_DECODER.tryAcquire()) {
            long rejected=WorkOrderPhotoController.IMAGE_REJECTIONS.incrementAndGet();
            if ((rejected & (rejected-1))==0) WorkOrderPhotoController.LOG.warn("Image decode capacity reached; rejected={}",rejected);
            response.setStatus(503); response.setHeader("Retry-After","2");
            return AjaxResult.error(503,"照片处理中，请稍后重试");
        }
        byte[] bytes; String type;
        try {
            bytes=file.getBytes();
            try { type=WorkOrderPhotoController.imageType(bytes); } catch (IOException | RuntimeException invalid) { return error("照片内容无效"); }
        } finally { WorkOrderPhotoController.IMAGE_DECODER.release(); }
        if (type==null) return error("仅支持完整且尺寸合理的 JPEG 或 PNG 照片");
        String name=UUID.randomUUID()+(type.equals("image/jpeg")?".jpg":".png");
        Path target=photoStorage.store(name,bytes);
        if (target==null) return error("照片存储空间不足，请联系管理员处理");
        var registered=new java.util.concurrent.atomic.AtomicBoolean(false);
        try {
            Long userId=actorId;
            Long stagedId=transactions.execute(status -> {
                PhotoRollbackCleanup.register(target); registered.set(true);
                if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? AND status='ACTIVE' FOR UPDATE",equipmentId).isEmpty()) return null;
                if (!publicEntry && departmentScope.enabled() && !departmentScope.canEquipment(departmentScope.current("equipment:inspection:add"),equipmentId)) return null;
                if (jdbc.queryForList("SELECT user_id FROM sys_user WHERE user_id=? FOR UPDATE",userId).isEmpty()) throw new IllegalStateException("上传用户不存在");
                if (!publicEntry) {
                    Long pending=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE uploaded_by=? AND inspection_id IS NULL",Long.class,userId);
                    if (pending!=null && pending>=24) return null;
                }
                var key=new org.springframework.jdbc.support.GeneratedKeyHolder();
                int inserted=jdbc.update(c -> {
                    var statement=c.prepareStatement("INSERT INTO ems_inspection_photo_stage(equipment_id,uploaded_by,stored_name,media_type,file_size,expires_at) VALUES (?,?,?,?,?,DATE_ADD(NOW(),INTERVAL 2 HOUR))",java.sql.Statement.RETURN_GENERATED_KEYS);
                    statement.setLong(1,equipmentId);statement.setLong(2,userId);statement.setString(3,name);statement.setString(4,type);statement.setInt(5,bytes.length);return statement;
                },key);
                if (inserted!=1 || key.getKey()==null) throw new IllegalStateException("临时照片保存失败");
                return key.getKey().longValue();
            });
            if (stagedId==null) {
                Files.deleteIfExists(target);
                return error("待提交照片已达上限，请先提交或稍后重试");
            }
            if (publicEntry) { String token=UUID.randomUUID().toString(); jdbc.update("UPDATE ems_inspection_photo_stage SET public_token=? WHERE id=?",token,stagedId); return success(Map.of("token",token)); }
            return success(Map.of("id",stagedId));
        } catch (IOException | RuntimeException ex) {
            if (!registered.get()) try { Files.deleteIfExists(target); } catch (IOException cleanup) { ex.addSuppressed(cleanup); }
            throw ex;
        }
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:add')")
    @org.springframework.transaction.annotation.Transactional
    @DeleteMapping("/staged-photos/{stageId}")
    public AjaxResult removeStage(@PathVariable long stageId) throws IOException {
        if (stageId<=0) return error("照片编号无效");
        var rows=jdbc.queryForList("SELECT stored_name,inspection_id FROM ems_inspection_photo_stage WHERE id=? AND uploaded_by=? FOR UPDATE",stageId,SecurityUtils.getUserId());
        // An absent or another user's row looks identical, so retries do not reveal ownership.
        if (rows.isEmpty()) return success();
        var row=rows.get(0);
        if (row.get("inspection_id")!=null) return error("照片已提交，无法移除");
        String name=String.valueOf(row.get("stored_name"));
        if (!name.matches("[0-9a-f-]{36}\\.(jpg|png)")) throw new IllegalStateException("临时照片名称无效");
        Long references=jdbc.queryForObject("SELECT (SELECT COUNT(*) FROM ems_inspection_photo WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_work_order_photo WHERE stored_name=?)",Long.class,name,name);
        if (references==null || references!=0) throw new IllegalStateException("照片已被引用，无法移除");
        Path target=storage.resolve(name).normalize();
        if (!target.getParent().equals(storage)) throw new IllegalStateException("临时照片路径无效");
        if (jdbc.update("DELETE FROM ems_inspection_photo_stage WHERE id=? AND uploaded_by=? AND inspection_id IS NULL",stageId,SecurityUtils.getUserId())!=1) throw new IllegalStateException("移除临时照片失败");
        StagePhotoCommitCleanup.register(target, () -> {
            Long remaining=jdbc.queryForObject("SELECT (SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_inspection_photo WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_work_order_photo WHERE stored_name=?)",Long.class,name,name,name);
            return remaining != null && remaining == 0;
        });
        return success();
    }

    @PreAuthorize("@ss.hasPermi('equipment:inspection:add')")
    @PostMapping("/{id}/photos")
    public AjaxResult upload(@PathVariable long id, @RequestParam("file") MultipartFile file, HttpServletResponse response) throws IOException {
        if (file.isEmpty() || file.getSize()>WorkOrderPhotoController.MAX_BYTES) return error("照片大小必须在 5 MB 以内");
        if (!departmentScope.enabled() && !canView(id)) return error("巡检不存在或无权上传");
        if (!WorkOrderPhotoController.IMAGE_DECODER.tryAcquire()) {
            long rejected=WorkOrderPhotoController.IMAGE_REJECTIONS.incrementAndGet();
            if ((rejected & (rejected-1))==0) WorkOrderPhotoController.LOG.warn("Image decode capacity reached; rejected={}",rejected);
            response.setStatus(503); response.setHeader("Retry-After","2");
            return AjaxResult.error(503,"照片处理中，请稍后重试");
        }
        byte[] bytes; String type;
        try {
            bytes=file.getBytes();
            try { type=WorkOrderPhotoController.imageType(bytes); } catch (IOException | RuntimeException invalid) { return error("照片内容无效"); }
        } finally { WorkOrderPhotoController.IMAGE_DECODER.release(); }
        if (type==null) return error("仅支持完整且尺寸合理的 JPEG 或 PNG 照片");
        String name=UUID.randomUUID()+(type.equals("image/jpeg")?".jpg":".png");
        Path target=photoStorage.store(name,bytes);
        if (target==null) return error("照片存储空间不足，请联系管理员处理");
        var registered=new java.util.concurrent.atomic.AtomicBoolean(false);
        try {
            Boolean inserted=transactions.execute(status -> {
                PhotoRollbackCleanup.register(target); registered.set(true);
                var initial=jdbc.queryForList("SELECT equipment_id FROM ems_inspection WHERE id=?",id);
                if (initial.isEmpty()) return false;
                long equipment=((Number)initial.get(0).get("equipment_id")).longValue();
                if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",equipment).isEmpty()) return false;
                if (jdbc.queryForList("SELECT id FROM ems_inspection WHERE id=? AND equipment_id=? FOR UPDATE",id,equipment).isEmpty() || (!departmentScope.enabled() && !canView(id))) return false;
                if (departmentScope.enabled()) {
                    for (String action:java.util.List.of("equipment:inspection:list","equipment:inspection:add")) {
                        var filter=InspectionScopeSql.read(departmentScope.current(action),"i");
                        var args=new java.util.ArrayList<Object>(); args.add(id); args.addAll(filter.args());
                        Long allowed=jdbc.queryForObject("SELECT COUNT(*) FROM ems_inspection i WHERE i.id=? AND ("+filter.sql()+")",Long.class,args.toArray());
                        if (allowed==null || allowed==0) return false;
                    }
                }
                if (jdbc.update("INSERT INTO ems_inspection_photo(inspection_id,stored_name,media_type,file_size,uploaded_by) VALUES (?,?,?,?,?)",id,name,type,bytes.length,SecurityUtils.getUserId())!=1) throw new IllegalStateException("巡检照片保存失败");
                return true;
            });
            if (!Boolean.TRUE.equals(inserted)) { Files.deleteIfExists(target); return error("巡检不存在或无权上传"); }
        } catch (IOException | RuntimeException ex) {
            if (!registered.get()) try { Files.deleteIfExists(target); } catch (IOException cleanup) { ex.addSuppressed(cleanup); }
            throw ex;
        }
        return success();
    }
    @PreAuthorize("@ss.hasPermi('equipment:inspection:list')")
    @GetMapping("/{id}/photos")
    public AjaxResult list(@PathVariable long id, @RequestParam(required=false) Long afterId) {
        if (!departmentScope.enabled() && !canView(id)) return error("巡检不存在或无权查看");
        if (afterId!=null && afterId<=0) return error("照片分页参数无效");
        String sql="SELECT p.id,p.media_type,p.file_size,p.uploaded_by,p.uploaded_at FROM ems_inspection_photo p WHERE p.inspection_id=?";
        var args=new java.util.ArrayList<Object>(); args.add(id);
        if (afterId!=null) { sql+=" AND p.id>?"; args.add(afterId); }
        if (departmentScope.enabled()) { var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins"); sql+=" AND EXISTS (SELECT 1 FROM ems_inspection ins WHERE ins.id=p.inspection_id AND ("+f.sql()+"))"; args.addAll(f.args()); }
        return success(jdbc.queryForList(sql+" ORDER BY p.id LIMIT 20",args.toArray()));
    }
    @PreAuthorize("@ss.hasPermi('equipment:inspection:list')")
    @org.springframework.transaction.annotation.Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/photos/{photoId}")
    public ResponseEntity<byte[]> photo(@PathVariable long photoId) throws IOException {
        if (departmentScope.enabled()) {
            var initial=jdbc.queryForList("SELECT i.id,i.equipment_id FROM ems_inspection_photo p JOIN ems_inspection i ON i.id=p.inspection_id WHERE p.id=?",photoId);
            if (initial.isEmpty()) return ResponseEntity.notFound().build();
            long inspection=((Number)initial.get(0).get("id")).longValue();
            long equipment=((Number)initial.get(0).get("equipment_id")).longValue();
            if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",equipment).isEmpty() ||
                jdbc.queryForList("SELECT id FROM ems_inspection WHERE id=? AND equipment_id=? FOR UPDATE",inspection,equipment).isEmpty()) return ResponseEntity.notFound().build();
        }
        String sql="SELECT p.inspection_id,p.stored_name,p.media_type FROM ems_inspection_photo p WHERE p.id=?";
        var args=new java.util.ArrayList<Object>(); args.add(photoId);
        if (departmentScope.enabled()) { var f=InspectionScopeSql.read(departmentScope.current("equipment:inspection:list"),"ins"); sql+=" AND EXISTS (SELECT 1 FROM ems_inspection ins WHERE ins.id=p.inspection_id AND ("+f.sql()+"))"; args.addAll(f.args()); }
        var rows=jdbc.queryForList(sql,args.toArray());
        if (rows.isEmpty()) return ResponseEntity.notFound().build();
        Map<String,Object> row=rows.get(0);
        if (!departmentScope.enabled() && !canView(((Number)row.get("inspection_id")).longValue())) return ResponseEntity.notFound().build();
        String name=String.valueOf(row.get("stored_name")), type=String.valueOf(row.get("media_type"));
        if (!name.matches("[0-9a-f-]{36}\\.(jpg|png)") || !(type.equals("image/jpeg") || type.equals("image/png"))) return ResponseEntity.notFound().build();
        Path target=storage.resolve(name).normalize();
        if (!target.getParent().equals(storage) || !Files.isRegularFile(target) || Files.size(target)>WorkOrderPhotoController.MAX_BYTES) return ResponseEntity.notFound().build();
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(type)).cacheControl(CacheControl.noStore()).header("X-Content-Type-Options","nosniff").body(Files.readAllBytes(target));
    }
}
