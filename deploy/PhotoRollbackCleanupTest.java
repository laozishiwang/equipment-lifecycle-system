package com.ruoyi.web.controller.equipment;
import java.nio.file.*;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
public class PhotoRollbackCleanupTest {
 public static void main(String[] args) throws Exception {
  Path committed=Files.createTempFile("photo-committed-", ".png");
  Path rolledBack=Files.createTempFile("photo-rollback-", ".png");
  try {
   TransactionSynchronizationManager.initSynchronization();
   PhotoRollbackCleanup.register(committed);
   for (var s:TransactionSynchronizationManager.getSynchronizations()) s.afterCompletion(TransactionSynchronization.STATUS_COMMITTED);
   TransactionSynchronizationManager.clearSynchronization();
   if (!Files.exists(committed)) throw new AssertionError("committed file deleted");
   TransactionSynchronizationManager.initSynchronization();
   PhotoRollbackCleanup.register(rolledBack);
   for (var s:TransactionSynchronizationManager.getSynchronizations()) s.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK);
   TransactionSynchronizationManager.clearSynchronization();
   if (Files.exists(rolledBack)) throw new AssertionError("rolled-back file retained");
   TransactionSynchronizationManager.initSynchronization();
   PhotoRollbackCleanup.register(committed);
   for (var sync:TransactionSynchronizationManager.getSynchronizations()) sync.afterCompletion(TransactionSynchronization.STATUS_UNKNOWN);
   TransactionSynchronizationManager.clearSynchronization();
   if (!Files.exists(committed)) throw new AssertionError("unknown outcome file deleted");
   try { PhotoRollbackCleanup.register(committed); throw new AssertionError("missing synchronization accepted"); }
   catch (IllegalStateException expected) { }
   System.out.println("photo transaction cleanup contract passed");
  } finally { Files.deleteIfExists(committed); Files.deleteIfExists(rolledBack); }
 }
}
