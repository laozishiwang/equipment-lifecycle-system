<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const form = reactive({ enabled: false, webhook: '', secret: '', clearSecret: false, keyword: '', template: 'basic' })
const configured = reactive({ hasWebhook: false, hasSecret: false })
const lastDelivery = ref(null)
const loading = ref(false), saving = ref(false), testing = ref(false)
async function loadRecent() {
  const recent = (await request({ url: '/monitor/dingtalk/recent', method: 'get' })).data || []
  lastDelivery.value = recent[0] || null
}
async function load() {
  loading.value = true
  try {
    const data = (await request({ url: '/monitor/dingtalk/config', method: 'get' })).data || {}
    Object.assign(form, { enabled: !!data.enabled, webhook: '', secret: '', clearSecret: false, keyword: data.keyword || '', template: data.template || 'basic' })
    Object.assign(configured, { hasWebhook: !!data.hasWebhook, hasSecret: !!data.hasSecret })
    await loadRecent()
  } finally { loading.value = false }
}
async function save() {
  if (!form.webhook.trim() && !configured.hasWebhook) return ElMessage.warning('请填写钉钉机器人 Webhook')
  saving.value = true
  try {
    await request({ url: '/monitor/dingtalk/config', method: 'put', data: { ...form, webhook: form.webhook.trim(), secret: form.secret.trim(), keyword: form.keyword.trim() } })
    ElMessage.success('配置已保存')
    await load()
  } finally { saving.value = false }
}
async function test() {
  testing.value = true
  try {
    await request({ url: '/monitor/dingtalk/test', method: 'post' })
    ElMessage.success('测试通知已发送，请查看钉钉群')
  } finally { testing.value = false }
}
onMounted(load)
</script>

<template>
  <main class="notification-page" v-loading="loading">
    <header><span>通知管理</span><h1>钉钉群通知</h1><p>设备报修和维修完成时，向指定的钉钉群发送通知。</p></header>
    <section class="settings">
      <div class="section-heading"><div><h2>机器人配置</h2><p>在钉钉群添加自定义机器人后，填写机器人的信息。</p></div><el-switch v-model="form.enabled" active-text="启用通知" /></div>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Webhook 地址" required><el-input v-model="form.webhook" type="password" show-password :placeholder="configured.hasWebhook ? '已配置，留空保持不变' : '粘贴钉钉机器人 Webhook 地址'" /></el-form-item>
        <el-form-item label="加签密钥（选填）"><el-input v-model="form.secret" type="password" show-password :placeholder="configured.hasSecret ? '已配置，留空保持不变' : '若机器人启用了加签，请填写密钥'" /><el-checkbox v-if="configured.hasSecret" v-model="form.clearSecret">清除已保存的加签密钥</el-checkbox></el-form-item>
        <el-form-item label="自定义关键词（选填）"><el-input v-model="form.keyword" maxlength="50" placeholder="若机器人使用关键词，请填写相同关键词" /><p class="hint">填写后，通知内容会包含该关键词。</p></el-form-item>
        <p class="hint ip-note">如启用 IP 白名单，请将服务器实际公网出口 IP 添加到钉钉机器人配置。出口 IP 可能与访问地址不同，请以服务器实际出口为准。</p>
        <el-form-item label="通知模板"><el-radio-group v-model="form.template"><el-radio value="basic">简洁模板</el-radio><el-radio value="detailed">详细模板</el-radio></el-radio-group><p class="hint">简洁模板显示设备和状态；详细模板包含更多工单信息。</p></el-form-item>
      </el-form>
      <div class="actions"><el-button type="primary" :loading="saving" @click="save">保存配置</el-button><el-button :loading="testing" @click="test">发送测试通知</el-button></div>
      <p class="hint">测试使用已保存的配置。修改后请先保存，再发送测试。</p>
      <div v-if="lastDelivery" class="delivery-status">
        <h2>最近一条通知</h2>
        <p>工单 {{ lastDelivery.order_id }} · {{ lastDelivery.event_type === 'CLOSED' ? '维修完成' : '设备报修' }} · {{ ({ PENDING: '待发送', SENT: '已发送', FAILED: '发送失败' })[lastDelivery.status] || lastDelivery.status }}</p>
        <p v-if="lastDelivery.last_error">{{ lastDelivery.last_error }}</p>
        <p class="hint">{{ lastDelivery.created_at }}</p>
        <el-button link type="primary" @click="loadRecent">刷新状态</el-button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.notification-page{max-width:920px;margin:auto;padding:28px;color:#1d3449}header{margin-bottom:24px}header span{font-size:13px;color:#6e8193}h1{font-size:26px;margin:8px 0}p{color:#6e8193;line-height:1.6;margin:0}.settings{padding:26px;background:#fff;border:1px solid #e6edf3;border-radius:14px}.section-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:24px}.section-heading h2{margin:0 0 8px;font-size:18px}.hint{font-size:13px;margin-top:8px;width:100%}.ip-note{margin:0 0 18px}.actions{display:flex;gap:8px}.actions :deep(.el-button){margin:0}.delivery-status{border-top:1px solid #e6edf3;margin-top:24px;padding-top:18px}.delivery-status h2{font-size:16px;margin:0 0 8px}@media(max-width:600px){.notification-page{padding:16px}.settings{padding:18px}.section-heading{display:block}.section-heading :deep(.el-switch){margin-top:16px}.actions{flex-wrap:wrap}}
</style>
