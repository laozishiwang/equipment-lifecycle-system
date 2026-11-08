package com.ruoyi.web.controller.equipment;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.BooleanSupplier;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Only remove a staged file after commit and a fresh reference check. */
final class StagePhotoCommitCleanup {
    private static final org.slf4j.Logger LOG=org.slf4j.LoggerFactory.getLogger(StagePhotoCommitCleanup.class);
    private StagePhotoCommitCleanup() {}
    static void register(Path target, BooleanSupplier unreferenced) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) throw new IllegalStateException("Transaction required");
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override public void afterCommit() {
                try { if (unreferenced.getAsBoolean()) Files.deleteIfExists(target); }
                catch (IOException | RuntimeException ex) { LOG.error("Unable to reconcile staged photo {}",target.getFileName(),ex); }
            }
        });
    }
}
