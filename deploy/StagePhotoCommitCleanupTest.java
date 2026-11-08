package com.ruoyi.web.controller.equipment;
import java.nio.file.*;
import org.springframework.transaction.support.*;
public class StagePhotoCommitCleanupTest {
 public static void main(String[] args) throws Exception {
  Path p=Files.createTempFile("stage-photo-", ".png");
  try {
   TransactionSynchronizationManager.initSynchronization(); StagePhotoCommitCleanup.register(p,()->true);
   for(var x:TransactionSynchronizationManager.getSynchronizations()) x.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK);
   TransactionSynchronizationManager.clearSynchronization(); if(!Files.exists(p)) throw new AssertionError("rollback lost file");
   TransactionSynchronizationManager.initSynchronization(); StagePhotoCommitCleanup.register(p,()->false);
   for(var x:TransactionSynchronizationManager.getSynchronizations()) x.afterCommit();
   TransactionSynchronizationManager.clearSynchronization(); if(!Files.exists(p)) throw new AssertionError("referenced file deleted");
   TransactionSynchronizationManager.initSynchronization(); StagePhotoCommitCleanup.register(p,()->true);
   for(var x:TransactionSynchronizationManager.getSynchronizations()) x.afterCommit();
   TransactionSynchronizationManager.clearSynchronization(); if(Files.exists(p)) throw new AssertionError("unreferenced file retained");
   System.out.println("stage photo commit cleanup contract passed");
  } finally {Files.deleteIfExists(p);}
 }
}
