-- Index the per-user unbound-stage quota lookup; safely repeatable on MySQL 8.
SET SESSION lock_wait_timeout=5;
SET @stage_index_exists=(SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='ems_inspection_photo_stage' AND index_name='idx_inspection_stage_uploader_pending');
SET @stage_index_sql=IF(@stage_index_exists=0,'ALTER TABLE ems_inspection_photo_stage ADD INDEX idx_inspection_stage_uploader_pending (uploaded_by,inspection_id), ALGORITHM=INPLACE, LOCK=NONE','DO 0');
PREPARE stage_index_stmt FROM @stage_index_sql;
EXECUTE stage_index_stmt;
DEALLOCATE PREPARE stage_index_stmt;
