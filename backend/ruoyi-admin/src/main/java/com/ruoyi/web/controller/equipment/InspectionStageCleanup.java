package com.ruoyi.web.controller.equipment;

import java.nio.file.Path;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@Configuration
@EnableScheduling
public class InspectionStageCleanup {
    private static final Logger LOG=LoggerFactory.getLogger(InspectionStageCleanup.class);
    private final JdbcTemplate jdbc;
    private final TransactionTemplate transactions;
    private final Path storage;
    private java.sql.Timestamp cursorTime;
    private long cursorId;
    private record Candidate(long id, java.sql.Timestamp expiresAt) {}
    public InspectionStageCleanup(JdbcTemplate jdbc, PlatformTransactionManager manager, @Value("${ems.private-upload-dir:./private-uploads}") String directory) {
        this.jdbc=jdbc; this.transactions=new TransactionTemplate(manager); this.storage=Path.of(directory).toAbsolutePath().normalize();
    }
    @Scheduled(initialDelayString="${ems.stage-cleanup-initial-delay-ms:60000}", fixedDelayString="${ems.stage-cleanup-delay-ms:60000}")
    public synchronized void cleanExpired() {
        String base="SELECT id,expires_at FROM ems_inspection_photo_stage WHERE inspection_id IS NULL AND expires_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)";
        org.springframework.jdbc.core.RowMapper<Candidate> mapper=(rs,row) -> new Candidate(rs.getLong("id"),rs.getTimestamp("expires_at"));
        var candidates=cursorTime==null
            ? jdbc.query(base+" ORDER BY expires_at,id LIMIT 100",mapper)
            : jdbc.query(base+" AND (expires_at>? OR (expires_at=? AND id>?)) ORDER BY expires_at,id LIMIT 100",mapper,cursorTime,cursorTime,cursorId);
        for (Candidate candidate:candidates) {
            try { transactions.executeWithoutResult(status -> cleanOne(candidate.id())); }
            catch (RuntimeException ex) { LOG.warn("Failed to clean expired inspection photo stage id={}",candidate.id(),ex); }
            cursorTime=candidate.expiresAt(); cursorId=candidate.id();
        }
        // Wrap after the end so failed items are retried without blocking later rows.
        if (candidates.size()<100) { cursorTime=null; cursorId=0; }
    }
    private void cleanOne(long id) {
        var rows=jdbc.queryForList("SELECT stored_name FROM ems_inspection_photo_stage WHERE id=? AND inspection_id IS NULL AND expires_at < DATE_SUB(NOW(), INTERVAL 1 HOUR) FOR UPDATE",id);
        if (rows.isEmpty()) return;
        String name=String.valueOf(rows.get(0).get("stored_name"));
        if (!name.matches("[0-9a-f-]{36}\\.(jpg|png)")) { LOG.error("Invalid staged photo name for id={}",id); return; }
        Long references=jdbc.queryForObject("SELECT (SELECT COUNT(*) FROM ems_inspection_photo WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_work_order_photo WHERE stored_name=?)",Long.class,name,name);
        if (references==null || references!=0) { LOG.error("Expired staged photo id={} is referenced; preserving file",id); return; }
        Path target=storage.resolve(name).normalize();
        if (!target.getParent().equals(storage)) throw new IllegalStateException("Invalid staged photo path");
        if (jdbc.update("DELETE FROM ems_inspection_photo_stage WHERE id=? AND inspection_id IS NULL",id)!=1)
            throw new IllegalStateException("Expired staged photo removal failed");
        StagePhotoCommitCleanup.register(target, () -> {
            Long remaining=jdbc.queryForObject("SELECT (SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_inspection_photo WHERE stored_name=?)+(SELECT COUNT(*) FROM ems_work_order_photo WHERE stored_name=?)",Long.class,name,name,name);
            return remaining != null && remaining == 0;
        });
    }
}
