<script setup>
import { ref, onMounted } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
import QRCode from 'qrcode'
import FaultCodeCatalog from './FaultCodeCatalog.vue'
import DepartmentOwnership from './DepartmentOwnership.vue'
import { checkPermi } from '@/utils/permission'

const qrVisible = ref(false), qrImage = ref(''), qrUrl = ref(''), qrWarning=ref('')
const mobile=useMediaQuery('(max-width: 767px)')
async function showQr(row) {
  const data=(await request({url:'/equipment/assets/qr-base',method:'get'})).data
  const base=data.baseUrl || window.location.origin
  const address=new URL(base)
  const host=address.hostname.toLowerCase().replace(/^\[|\]$/g,'')
  const local=host==='localhost' || host==='::1' || /^127\./.test(host) || /^10\./.test(host) || /^192\.168\./.test(host) || /^172\.(1[6-9]|2[0-9]|3[01])\./.test(host)
  qrWarning.value=address.protocol!=='https:' || local ? '当前地址不是可供公网手机安全访问的 HTTPS 地址，请勿打印为正式设备二维码。' : ''
  qrUrl.value=address.origin+'/field/'+row.id
  qrImage.value=await QRCode.toDataURL(qrUrl.value,{width:320,margin:2})
  qrVisible.value=true
}
const historyOpen = ref(false), history = ref(null)
async function showHistory(row) { history.value = (await request({ url: '/equipment/assets/' + row.id + '/history', method: 'get' })).data; historyOpen.value = true }
const keyword = ref(''), appliedKeyword = ref(''), ownership = ref('ALL'), appliedOwnership = ref('ALL')
const rows = ref([])
const loading = ref(false), hasMore = ref(false)
const visible = ref(false)
const createDepartments=ref([]), createDeptRequired=ref(false), createDeptLoading=ref(false), createDeptError=ref(false)
async function loadCreateDepartments() {
  createDeptLoading.value=true
  createDeptError.value=false
  try {
    const data=(await request({url:'/equipment/assets/create-departments',method:'get'})).data
    createDepartments.value=data.departments || []
    createDeptRequired.value=!!data.required
  } catch { createDeptError.value=true }
  finally { createDeptLoading.value=false }
}
async function openCreate() {
  createDepartments.value=[]
  createDeptRequired.value=false
  form.value.deptId=null
  visible.value=true
  await loadCreateDepartments()
}
const saving = ref(false)
const selectedAssets=ref([]), batchOpen=ref(false), batchSaving=ref(false), batchDepartments=ref([]), batchDept=ref(null), batchAssets=ref([])
async function openBatch() {
  if (!selectedAssets.value.length || selectedAssets.value.length>100) return ElMessage.warning('请选择 1 至 100 台未设置部门的设备')
  batchAssets.value=selectedAssets.value.map(row=>({id:row.id,code:row.code,name:row.name}))
  batchDepartments.value=(await request({url:'/equipment/assets/departments',method:'get'})).data || []
  batchDept.value=null
  batchOpen.value=true
}
async function saveBatch() {
  if (!batchDept.value) return ElMessage.warning('请选择归属部门')
  if (batchSaving.value) return
  batchSaving.value=true
  try {
    await request({url:'/equipment/assets/departments/batch',method:'post',data:{deptId:batchDept.value,equipmentIds:batchAssets.value.map(row=>row.id)}})
    ElMessage.success(`已分配 ${batchAssets.value.length} 台设备`)
    batchOpen.value=false
    selectedAssets.value=[]
    await load(false)
  } finally { batchSaving.value=false }
}
const templateOpen=ref(false), templateSaving=ref(false), templateAsset=ref(null), templateForm=ref({name:'',items:[],requireAbnormalPhoto:false})
async function openTemplate(row) {
  const data=(await request({url:'/equipment/assets/'+row.id+'/inspection-template',method:'get'})).data
  templateAsset.value=row
  templateForm.value={name:data.name || '',requireAbnormalPhoto:data.requireAbnormalPhoto === true,items:(data.items || []).map(item=>({name:item.item_name,standard:item.standard_text || '',lowerBound:item.lower_bound ?? '',upperBound:item.upper_bound ?? '',unit:item.unit || ''}))}
  templateOpen.value=true
}
async function saveTemplate() {
  if(!templateForm.value.name.trim() || !templateForm.value.items.length || templateForm.value.items.some(item=>!item.name.trim())) return ElMessage.warning('请填写模板名称及项目名称')
  const validNumber=value=>value==='' || /^-?\d{1,9}(\.\d{1,4})?$/.test(String(value))
  if(templateForm.value.items.some(item=>!validNumber(item.lowerBound) || !validNumber(item.upperBound) || (item.lowerBound!=='' && item.upperBound!=='' && Number(item.lowerBound)>Number(item.upperBound)) || (item.lowerBound==='' && item.upperBound==='' && item.unit.trim()))) return ElMessage.warning('数值范围或单位不正确，最多 9 位整数和 4 位小数')
  const data={...templateForm.value,ruleSchemaVersion:1,items:templateForm.value.items.map(item=>({...item,lowerBound:item.lowerBound===''?null:String(item.lowerBound),upperBound:item.upperBound===''?null:String(item.upperBound)}))}
  templateSaving.value=true
  try { await request({url:'/equipment/assets/'+templateAsset.value.id+'/inspection-template',method:'put',data}); templateOpen.value=false; ElMessage.success('巡检模板已保存') }
  finally { templateSaving.value=false }
}
const editOpen = ref(false), editForm = ref({})
async function openEdit(row) { const d = (await request({url:'/equipment/assets/' + row.id, method:'get'})).data; editForm.value = { ...d, serialNumber:d.serial_number, purchaseDate:d.purchase_date, warrantyUntil:d.warranty_until }; editOpen.value = true }
async function saveEdit() { if (!editForm.value.name?.trim()) return ElMessage.warning('请填写设备名称'); saving.value = true; try { await request({url:'/equipment/assets/' + editForm.value.id,method:'put',data:editForm.value}); editOpen.value=false; ElMessage.success('设备已更新'); await load() } finally { saving.value=false } }
const form = ref({ code: '', name: '', model: '', location: '', manufacturer:'', serialNumber:'', purchaseDate:null, warrantyUntil:null, deptId:null })
let loadVersion=0
async function load(more=false) {
  if (more && loading.value) return
  const version=++loadVersion
  loading.value = true
  try { if (!more) { appliedKeyword.value = keyword.value; appliedOwnership.value = ownership.value } const params = { keyword: appliedKeyword.value, ownership: appliedOwnership.value }; if (more && rows.value.length) params.beforeId = rows.value[rows.value.length-1].id; const page = (await request({ url: '/equipment/assets', method: 'get', params })).data || []; if (version!==loadVersion) return; rows.value = more ? [...rows.value, ...page] : page; hasMore.value = page.length === 200 }
  finally { if (version===loadVersion) loading.value = false }
}
async function save() {
  if (!form.value.code.trim() || !form.value.name.trim()) { ElMessage.warning('请填写设备编号和名称'); return }
  if (createDeptLoading.value || createDeptError.value) return ElMessage.warning('请先加载归属部门')
  if (createDeptRequired.value && !form.value.deptId) return ElMessage.warning('请选择归属部门')
  if (saving.value) return
  saving.value = true
  try {
    await request({ url: '/equipment/assets', method: 'post', data: form.value })
    ElMessage.success('设备已创建')
    visible.value = false
    form.value = { code: '', name: '', model: '', location: '', manufacturer:'', serialNumber:'', purchaseDate:null, warrantyUntil:null, deptId:null }
    await load()
  } finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <div class="app-container">
    <div class="heading"><div><h2>设备台账</h2><p>统一查看和登记厂区设备</p></div><div><FaultCodeCatalog v-hasPermi="['equipment:asset:edit']"/><el-button v-hasPermi="['equipment:asset:add']" type="primary" @click="openCreate">新增设备</el-button></div></div>
    <div class="search"><el-input v-model="keyword" placeholder="搜索设备编号或名称" clearable @keyup.enter="load(false)"/><el-button type="primary" plain @click="load(false)">搜索</el-button></div>
    <div class="ownership-filter"><label for="asset-ownership-filter">部门归属</label><el-select id="asset-ownership-filter" v-model="ownership" @change="load(false)"><el-option label="全部设备" value="ALL"/><el-option label="已设置部门" value="ASSIGNED"/><el-option label="未设置部门" value="UNASSIGNED"/></el-select><el-button v-if="checkPermi(['equipment:asset:edit'])" class="batch-control" :disabled="!selectedAssets.length" @click="openBatch">批量设置部门（{{ selectedAssets.length }}）</el-button></div>
    <el-alert title="按设备编号或名称搜索，可加载更早记录" type="info" :closable="false" show-icon />
    <el-table v-if="!mobile" class="desktop-assets" v-loading="loading" :data="rows" style="margin-top: 16px" @selection-change="selectedAssets=$event">
      <el-table-column v-if="checkPermi(['equipment:asset:edit'])" type="selection" width="48" :selectable="row => !row.dept_id" />
      <el-table-column prop="code" label="设备编号" min-width="140" />
      <el-table-column prop="name" label="设备名称" min-width="140" />
      <el-table-column prop="model" label="型号" min-width="120" />
      <el-table-column prop="location" label="位置" min-width="140" />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column label="编辑" width="90"><template #default="{row}"><el-button v-hasPermi="['equipment:asset:edit']" link type="primary" @click="openEdit(row)">编辑</el-button></template></el-table-column>
      <el-table-column label="归属部门" min-width="150"><template #default="{row}"><span>{{ row.dept_name || '未设置' }}</span> <DepartmentOwnership v-hasPermi="['equipment:asset:edit']" :row="row" @saved="load(false)"/></template></el-table-column>
      <el-table-column label="巡检模板" width="100"><template #default="{row}"><el-button v-hasPermi="['equipment:asset:edit']" link type="primary" @click="openTemplate(row)">配置</el-button></template></el-table-column>
      <el-table-column label="履历" width="90"><template #default="{row}"><el-button v-hasPermi="['equipment:asset:history']" link type="primary" @click="showHistory(row)">查看</el-button></template></el-table-column>
      <el-table-column label="二维码" width="100"><template #default="{row}"><el-button link type="primary" @click="showQr(row)">查看</el-button></template></el-table-column>
    </el-table>
    <div v-else class="mobile-assets" v-loading="loading">
      <article v-for="row in rows" :key="row.id" class="asset-card">
        <div class="card-heading"><div><strong>{{ row.name }}</strong><p>{{ row.code }}</p></div><span class="asset-status" :class="{retired:row.status==='RETIRED'}">{{ row.status==='ACTIVE' ? '在用' : row.status==='RETIRED' ? '报废' : row.status }}</span></div>
        <dl><div><dt>位置</dt><dd>{{ row.location || '未设置' }}</dd></div><div><dt>型号</dt><dd>{{ row.model || '未设置' }}</dd></div><div><dt>归属部门</dt><dd>{{ row.dept_name || '未设置' }}</dd></div></dl>
        <div class="card-actions"><el-button v-if="checkPermi(['equipment:inspection:add','equipment:order:report'])" link type="primary" @click="$router.push('/field/'+row.id)">现场巡检 / 报修</el-button><el-button link type="primary" @click="showQr(row)">二维码</el-button><el-button v-hasPermi="['equipment:asset:edit']" link type="primary" @click="openEdit(row)">编辑</el-button><el-button v-hasPermi="['equipment:asset:edit']" link type="primary" @click="openTemplate(row)">巡检模板</el-button><DepartmentOwnership v-hasPermi="['equipment:asset:edit']" :row="row" @saved="load(false)"/><el-button v-hasPermi="['equipment:asset:history']" link type="primary" @click="showHistory(row)">履历</el-button></div>
      </article>
      <el-empty v-if="!loading && !rows.length" description="暂无设备" />
    </div>
    <div style="text-align:center;margin:20px"><el-button v-if="hasMore" :loading="loading" @click="load(true)">加载更多设备</el-button></div>
    <el-dialog v-model="batchOpen" title="批量设置设备部门" width="min(95%, 620px)" :close-on-click-modal="!batchSaving" :show-close="!batchSaving"><p>仅分配未设置部门的设备；若设备已被其他人分配，本次将全部取消，请刷新后重试。</p><el-form label-position="top"><el-form-item label="归属部门"><el-select v-model="batchDept" filterable placeholder="请选择部门"><el-option v-for="item in batchDepartments" :key="item.dept_id" :label="`${item.dept_name}（${item.dept_id}）`" :value="item.dept_id"/></el-select></el-form-item></el-form><p>待分配 {{ batchAssets.length }} 台设备</p><el-table :data="batchAssets" max-height="300"><el-table-column prop="code" label="设备编号"/><el-table-column prop="name" label="设备名称"/></el-table><template #footer><el-button :disabled="batchSaving" @click="batchOpen=false">取消</el-button><el-button type="primary" :loading="batchSaving" @click="saveBatch">确认分配</el-button></template></el-dialog>
    <el-dialog v-model="templateOpen" title="配置设备巡检模板" width="min(95%, 600px)">
      <p>填写上下限可自动判定数值结果；不填上下限时使用人工判定。</p>
      <el-form label-position="top"><el-form-item label="模板名称"><el-input v-model="templateForm.name" maxlength="120" /></el-form-item><el-form-item><el-checkbox v-model="templateForm.requireAbnormalPhoto">异常巡检提交前必须上传照片</el-checkbox></el-form-item>
        <el-form-item label="检查项目"><div v-for="(item,index) in templateForm.items" :key="index" class="template-item"><el-input v-model="item.name" maxlength="120" placeholder="项目名称"/><el-input v-model="item.standard" maxlength="500" placeholder="检查标准（选填）"/><el-input v-model="item.lowerBound" inputmode="decimal" placeholder="数值下限（选填）"/><el-input v-model="item.upperBound" inputmode="decimal" placeholder="数值上限（选填）"/><el-input v-model="item.unit" maxlength="32" placeholder="单位（选填）"/><el-button link type="danger" @click="templateForm.items.splice(index,1)">删除</el-button></div><el-button :disabled="templateForm.items.length >= 20" @click="templateForm.items.push({name:'',standard:'',lowerBound:'',upperBound:'',unit:''})">添加项目</el-button></el-form-item>
      </el-form><template #footer><el-button @click="templateOpen=false">取消</el-button><el-button type="primary" :loading="templateSaving" @click="saveTemplate">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="editOpen" title="编辑设备" width="min(90%, 520px)"><el-form label-position="top"><el-form-item label="设备编号"><el-input :model-value="editForm.code" disabled/></el-form-item><el-form-item label="名称"><el-input v-model="editForm.name" maxlength="128"/></el-form-item><el-form-item label="型号"><el-input v-model="editForm.model" maxlength="128"/></el-form-item><el-form-item label="位置"><el-input v-model="editForm.location" maxlength="255"/></el-form-item><el-form-item label="厂家"><el-input v-model="editForm.manufacturer" maxlength="128"/></el-form-item><el-form-item label="出厂编号"><el-input v-model="editForm.serialNumber" maxlength="128"/></el-form-item><el-form-item label="购置日期"><el-date-picker v-model="editForm.purchaseDate" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="质保截止"><el-date-picker v-model="editForm.warrantyUntil" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="状态"><el-select v-model="editForm.status"><el-option label="在用" value="ACTIVE"/><el-option label="报废" value="RETIRED"/></el-select></el-form-item></el-form><template #footer><el-button @click="editOpen=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template></el-dialog>
    <el-dialog v-model="historyOpen" title="设备履历" width="min(95%, 900px)"><template v-if="history"><h3>{{ history.equipment.code }} · {{ history.equipment.name }}</h3><el-descriptions :column="2" border><el-descriptions-item label="厂家">{{ history.equipment.manufacturer || "—" }}</el-descriptions-item><el-descriptions-item label="出厂编号">{{ history.equipment.serial_number || "—" }}</el-descriptions-item><el-descriptions-item label="购置日期">{{ history.equipment.purchase_date || "—" }}</el-descriptions-item><el-descriptions-item label="质保截止">{{ history.equipment.warranty_until || "—" }}</el-descriptions-item></el-descriptions><h4>位置变更（最近 200 条）</h4><el-table :data="history.locations"><el-table-column prop="location" label="位置"/><el-table-column prop="changed_at" label="变更时间"/><el-table-column prop="changed_by" label="操作人 ID"/></el-table><h4>维修工单（最近 200 条）</h4><el-table :data="history.orders"><el-table-column prop="description" label="故障"/><el-table-column prop="repair_description" label="维修内容"/><el-table-column prop="repair_date" label="维修日期"/><el-table-column prop="total_cost" label="费用合计"/><el-table-column prop="status" label="状态"/></el-table><h4>保养记录（最近 200 条）</h4><el-table :data="history.maintenance"><el-table-column prop="title" label="保养计划"/><el-table-column prop="completed_date" label="完成日期"/><el-table-column prop="completed_by" label="操作人 ID"/><el-table-column prop="notes" label="保养内容"/></el-table><h4>巡检记录（最近 200 条）</h4><el-table :data="history.inspections"><el-table-column prop="inspected_at" label="时间"/><el-table-column prop="result" label="结果"/><el-table-column prop="remark" label="说明"/></el-table></template></el-dialog>
    <el-dialog v-model="qrVisible" title="设备二维码" width="min(90%, 420px)"><el-alert v-if="qrWarning" :title="qrWarning" type="warning" :closable="false" show-icon/><div style="text-align:center"><img :src="qrImage" alt="设备二维码" style="max-width:100%"><p style="overflow-wrap:anywhere">{{ qrUrl }}</p><p>打印前请确认地址可从手机访问。</p></div></el-dialog>
    <el-dialog v-model="visible" title="新增设备" width="min(90%, 520px)">
      <el-alert v-if="createDeptError" title="归属部门加载失败，请重试" type="error" :closable="false" show-icon><el-button link type="primary" @click="loadCreateDepartments">重新加载</el-button></el-alert>
      <el-form label-position="top">
        <el-form-item label="设备编号"><el-input v-model="form.code" maxlength="64" /></el-form-item>
        <el-form-item label="设备名称"><el-input v-model="form.name" maxlength="128" /></el-form-item>
        <el-form-item v-if="createDeptRequired || createDepartments.length" label="归属部门" :required="createDeptRequired"><el-select v-model="form.deptId" :clearable="!createDeptRequired" filterable placeholder="请选择归属部门"><el-option v-for="item in createDepartments" :key="item.dept_id" :label="item.dept_name" :value="item.dept_id"/></el-select></el-form-item>
        <el-form-item label="型号"><el-input v-model="form.model" maxlength="128" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="form.location" maxlength="255" /></el-form-item>
        <el-form-item label="厂家"><el-input v-model="form.manufacturer" maxlength="128" /></el-form-item><el-form-item label="出厂编号"><el-input v-model="form.serialNumber" maxlength="128" /></el-form-item><el-form-item label="购置日期"><el-date-picker v-model="form.purchaseDate" value-format="YYYY-MM-DD" /></el-form-item><el-form-item label="质保截止"><el-date-picker v-model="form.warrantyUntil" value-format="YYYY-MM-DD" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="createDeptLoading || createDeptError" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.template-item{display:flex;gap:8px;width:100%;margin-bottom:8px;flex-wrap:wrap}.template-item .el-input{flex:1;min-width:150px}
.search { display:flex; gap:8px; max-width:420px; margin-bottom:16px; }
.ownership-filter { display:flex; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px; } .ownership-filter label { white-space:nowrap; color:#53657a; } .ownership-filter .el-select { width:180px; }
.heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 22px; }
h2 { margin: 0 0 8px; font-size: 24px; } p { margin: 0; color: #7b8794; }
.mobile-assets { display:none; }
@media (max-width:767px) {
  .desktop-assets,.batch-control { display:none; }
  .mobile-assets { display:block; min-height:80px; margin-top:16px; }
  .heading { align-items:flex-start; flex-wrap:wrap; }
  .asset-card { background:#fff; border:1px solid #e6edf5; border-radius:14px; padding:16px; margin-bottom:12px; box-shadow:0 4px 16px #193b560d; }
  .card-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
  .card-heading strong,.card-heading p,dd { overflow-wrap:anywhere; }
  .card-heading p { font-size:13px; margin-top:4px; }
  .asset-status { flex:none; background:#e8f7ef; color:#198754; border-radius:99px; padding:5px 10px; font-size:12px; }
  .asset-status.retired { background:#f1f3f5; color:#6c757d; }
  dl { margin:14px 0; display:grid; gap:7px; font-size:13px; }
  dl div { display:flex; gap:12px; min-width:0; } dt { color:#7b8794; flex:none; width:52px; } dd { margin:0; color:#36475b; min-width:0; }
  .card-actions { display:flex; flex-wrap:wrap; gap:8px 14px; } .card-actions :deep(.el-button) { margin:0; }
}
</style>










