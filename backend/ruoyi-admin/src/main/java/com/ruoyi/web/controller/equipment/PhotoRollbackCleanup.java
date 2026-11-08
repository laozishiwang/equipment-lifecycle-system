package com.ruoyi.web.controller.equipment;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Cleans a newly written private file when the surrounding DB transaction fails. */
final class PhotoRollbackCleanup {
    private static final org.slf4j.Logger LOG=org.slf4j.LoggerFactory.getLogger(PhotoRollbackCleanup.class);
    private PhotoRollbackCleanup() {}
    static void register(Path target) {
        if (!TransactionSynchronizationManager.isSynchronizationActive())
            throw new IllegalStateException("Photo upload requires a transaction");
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override public void afterCompletion(int status) {
                if (status == STATUS_ROLLED_BACK) {
                    try { Files.deleteIfExists(target); }
                    catch (IOException ex) { LOG.error("Failed to clean photo after transaction rollback: {}",target.getFileName(),ex); }
                } else if (status == STATUS_UNKNOWN) {
                    LOG.error("Photo transaction outcome unknown; retain file for reconciliation: {}", target.getFileName());
                }
            }
        });
    }
}
