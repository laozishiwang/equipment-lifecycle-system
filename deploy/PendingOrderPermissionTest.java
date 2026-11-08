package com.ruoyi.web.controller.equipment;
public class PendingOrderPermissionTest {
 public static void main(String[] args) {
  if (!PendingOrderPermission.allowed(true,false,false)) throw new AssertionError("legacy behavior changed");
  if (PendingOrderPermission.allowed(true,true,false)) throw new AssertionError("revoked permission still grants queue");
  if (!PendingOrderPermission.allowed(true,true,true)) throw new AssertionError("active permission denied");
  if (PendingOrderPermission.allowed(false,true,true)) throw new AssertionError("missing cached permission grants queue");
  System.out.println("pending queue permission contract passed");
 }
}
