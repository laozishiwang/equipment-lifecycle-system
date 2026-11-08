package com.ruoyi.web.controller.equipment;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
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
@RequestMapping("/equipment/orders")
public class WorkOrderPhotoController extends BaseController {
    static final int MAX_BYTES = 5 * 1024 * 1024;
    // Decoding one 40-megapixel image can use roughly 160 MB before overhead.
    // Keep one decoder in flight for the current 512 MB heap; tune after load testing.
    static final java.util.concurrent.Semaphore IMAGE_DECODER = new java.util.concurrent.Semaphore(1);
    static final java.util.concurrent.atomic.AtomicLong IMAGE_REJECTIONS = new java.util.concurrent.atomic.AtomicLong();
    static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(WorkOrderPhotoController.class);
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess departmentScope;
    private final Path storage;
    private final PrivatePhotoStorage photoStorage;
    public WorkOrderPhotoController(JdbcTemplate jdbc, PrivatePhotoStorage photoStorage, DepartmentScopeAccess departmentScope, @Value("${ems.private-upload-dir:./private-uploads}") String directory) {
        this.jdbc=jdbc; this.departmentScope=departmentScope; this.photoStorage=photoStorage; this.storage=Path.of(directory).toAbsolutePath().normalize();
    }
    private boolean inScope(long orderId, String action, boolean pending, boolean lock) {
        if (!departmentScope.enabled()) return true;
        if (lock) {
            var rows=jdbc.queryForList("SELECT equipment_id FROM ems_work_order WHERE id=?",orderId);
            if (rows.isEmpty()) return false;
            long equipment=((Number)rows.get(0).get("equipment_id")).longValue();
            if (jdbc.queryForList("SELECT id FROM ems_equipment WHERE id=? FOR UPDATE",equipment).isEmpty()) return false;
            var orders=jdbc.queryForList("SELECT equipment_id FROM ems_work_order WHERE id=? FOR UPDATE",orderId);
            if (orders.isEmpty() || ((Number)orders.get(0).get("equipment_id")).longValue()!=equipment) return false;
        }
        var filter=OrderScopeSql.read(departmentScope.current(action),pending);
        var args=new java.util.ArrayList<Object>(); args.add(orderId); args.addAll(filter.args());
        Long count=jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order w WHERE w.id=? AND "+filter.sql(),Long.class,args.toArray());
        return count!=null && count>0;
    }
    private boolean canView(long orderId) {
        if (!inScope(orderId,"equipment:order:list",PendingOrderPermission.current(departmentScope),false)) return false;
        if (departmentScope.enabled()) return true;
        if (SecurityUtils.hasPermi("equipment:order:viewAll")) return true;
        long user=SecurityUtils.getUserId();
        String pending=PendingOrderPermission.current(departmentScope) ? " OR status='REPORTED'" : "";
        Long count=jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order WHERE id=? AND (reporter_id=? OR technician_id=?"+pending+")",Long.class,orderId,user,user);
        return count!=null && count>0;
    }
    static String imageType(byte[] bytes) throws IOException {
        try (ImageInputStream stream=ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))) {
            if (stream==null) return null;
            Iterator<ImageReader> readers=ImageIO.getImageReaders(stream);
            if (!readers.hasNext()) return null;
            ImageReader reader=readers.next();
            try {
                reader.setInput(stream,true,true);
                String format=reader.getFormatName().toLowerCase(java.util.Locale.ROOT);
                int width=reader.getWidth(0),height=reader.getHeight(0);
                if (width<1 || height<1 || width>12000 || height>12000 || (long)width*height>40_000_000L) return null;
                String type = switch (format) { case "jpeg", "jpg" -> "image/jpeg"; case "png" -> "image/png"; default -> null; };
                if (type == null) return null;
                final boolean[] warning = {false};
                reader.addIIOReadWarningListener((source, message) -> warning[0] = true);
                var decoded = reader.read(0);
                if (decoded == null || warning[0]) return null;
                decoded.flush();
                return type;
            } finally { reader.dispose(); }
        }
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:photo')")
    @org.springframework.transaction.annotation.Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @PostMapping("/{id}/photos")
    public AjaxResult upload(@PathVariable long id, @RequestParam("file") MultipartFile file, jakarta.servlet.http.HttpServletResponse response) throws IOException {
        if (!inScope(id,"equipment:order:photo",false,true)) return error("工单不存在或无权上传");
        if (file.isEmpty() || file.getSize()>MAX_BYTES) return error("照片大小必须在 5 MB 以内");
        boolean all=departmentScope.enabled() ? departmentScope.current("equipment:order:viewAll").actionGranted() : SecurityUtils.hasPermi("equipment:order:viewAll");
        long user=SecurityUtils.getUserId();
        String allowed=all ? "1=1" : "((reporter_id=? AND status='REPORTED') OR technician_id=?)";
        Long count=all ? jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order WHERE id=? AND status NOT IN ('CLOSED','CANCELLED')",Long.class,id) : jdbc.queryForObject("SELECT COUNT(*) FROM ems_work_order WHERE id=? AND status NOT IN ('CLOSED','CANCELLED') AND "+allowed,Long.class,id,user,user);
        if (count==null || count==0) return error("工单不存在、已结束或无权上传");
        if (!IMAGE_DECODER.tryAcquire()) {
            long rejected=IMAGE_REJECTIONS.incrementAndGet();
            if ((rejected & (rejected-1))==0) LOG.warn("Image decode capacity reached; rejected={}",rejected);
            response.setStatus(503); response.setHeader("Retry-After","2");
            return AjaxResult.error(503,"照片处理中，请稍后重试");
        }
        byte[] bytes;
        String type;
        try {
            bytes=file.getBytes();
            try { type=imageType(bytes); } catch (IOException | RuntimeException invalid) { return error("照片内容无效"); }
        } finally { IMAGE_DECODER.release(); }
        if (type==null) return error("仅支持完整且尺寸合理的 JPEG 或 PNG 照片");
        String name=UUID.randomUUID()+(type.equals("image/jpeg")?".jpg":".png");
        Path target=photoStorage.store(name,bytes);
        if (target==null) return error("照片存储空间不足，请联系管理员处理");
        try { PhotoRollbackCleanup.register(target); }
        catch (RuntimeException ex) {
            try { Files.deleteIfExists(target); } catch (IOException cleanup) { ex.addSuppressed(cleanup); }
            throw ex;
        }
        try {
            String sql="INSERT INTO ems_work_order_photo(work_order_id,stored_name,media_type,file_size,uploaded_by) SELECT id,?,?,?,? FROM ems_work_order WHERE id=? AND status NOT IN ('CLOSED','CANCELLED') AND "+allowed;
            int inserted=all ? jdbc.update(sql,name,type,bytes.length,user,id) : jdbc.update(sql,name,type,bytes.length,user,id,user,user);
            if (inserted!=1) { Files.deleteIfExists(target); return error("工单状态或权限已变化，请刷新后重试"); }
        } catch (IOException | RuntimeException ex) {
            try { Files.deleteIfExists(target); } catch (IOException cleanup) { ex.addSuppressed(cleanup); }
            throw ex;
        }
        return success();
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:list')")
    @org.springframework.transaction.annotation.Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/{id}/photos")
    public AjaxResult list(@PathVariable long id, @RequestParam(required=false) Long afterId) {
        if (departmentScope.enabled() && !inScope(id,"equipment:order:list",PendingOrderPermission.current(departmentScope),true)) return error("无权查看工单照片");
        if (!canView(id)) return error("无权查看工单照片");
        if (afterId != null && afterId <= 0) return error("照片分页参数无效");
        String columns="SELECT id,media_type,file_size,uploaded_by,uploaded_at FROM ems_work_order_photo WHERE work_order_id=?";
        return success(afterId == null
            ? jdbc.queryForList(columns+" ORDER BY id LIMIT 20",id)
            : jdbc.queryForList(columns+" AND id>? ORDER BY id LIMIT 20",id,afterId));
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:list')")
    @org.springframework.transaction.annotation.Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    @GetMapping("/photos/{photoId}")
    public ResponseEntity<byte[]> photo(@PathVariable long photoId) throws IOException {
        var rows=jdbc.queryForList("SELECT work_order_id,stored_name,media_type FROM ems_work_order_photo WHERE id=?",photoId);
        if (rows.isEmpty()) return ResponseEntity.notFound().build();
        Map<String,Object> row=rows.get(0);
        long orderId=((Number)row.get("work_order_id")).longValue();
        if (departmentScope.enabled() && !inScope(orderId,"equipment:order:list",PendingOrderPermission.current(departmentScope),true)) return ResponseEntity.notFound().build();
        if (!canView(orderId)) return ResponseEntity.notFound().build();
        String name=String.valueOf(row.get("stored_name"));
        String type=String.valueOf(row.get("media_type"));
        if (!name.matches("[0-9a-f-]{36}\\.(jpg|png)") || !(type.equals("image/jpeg") || type.equals("image/png"))) return ResponseEntity.notFound().build();
        Path target=storage.resolve(name).normalize();
        if (!target.getParent().equals(storage) || !Files.isRegularFile(target) || Files.size(target)>MAX_BYTES) return ResponseEntity.notFound().build();
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(type)).cacheControl(CacheControl.noStore()).header("X-Content-Type-Options","nosniff").body(Files.readAllBytes(target));
    }
}

