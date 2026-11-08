export function closeFieldPage() {
  if (/MicroMessenger/i.test(navigator.userAgent) && window.WeixinJSBridge) {
    window.WeixinJSBridge.call('closeWindow')
    return
  }
  window.close()
}
