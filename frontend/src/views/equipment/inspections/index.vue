<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import InspectionItems from './InspectionItems.vue'
import InspectionPhotoStage from './InspectionPhotoStage.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
const records = ref([]), assets = ref([]), dialog = ref(false), saving = ref(false), loading = ref(false), hasMore = ref(false)
const router = useRouter()
const orderStatus = { REPORTED:'待接单', ACCEPTED:'待到场', ARRIVED:'维修中', TESTING:'待试运行', COMPLETED:'待关单', CLOSED:'已关单', CANCELLED:'已取消' }
function openOrder(row) { router.push({ path:'/equipment/orders', query:{ open:String(row.order_id) } }) }
const historyOpen=ref(false), historyRows=ref([]), historyLoading=ref(false), historyMore=ref(false), historyInspectionId=ref(null)
let historyVersion=0
async function showOrderHistory(row) {
  historyInspectionId.value=row.id;historyRows.value=[];historyMore.value=false;historyOpen.value=true
  await loadOrderHistory()
}
async function loadOrderHistory(more=false) {
  if(more && historyLoading.value)return
  const version=++historyVersion, inspection=historyInspectionId.value
  const params=more && historyRows.value.length ? {beforeId:historyRows.value[historyRows.value.length-1].id} : {}
  historyLoading.value=true
  try {
    const rows=(await request({url:`/equipment/inspections/${inspection}/work-orders`,method:'get',params})).data || []
    if(version!==historyVersion)return
    historyRows.value=more ? [...historyRows.value,...rows] : rows
    historyMore.value=rows.length===20
  } finally { if(version===historyVersion)historyLoading.value=false }
}
function closeOrderHistory() { historyVersion++;historyLoading.value=false }
const convertingId = ref(null)
async function createOrderFromInspection(row) {
  if (convertingId.value !== null) return
  let result
  try {
    result = await ElMessageBox.prompt(row.order_status === 'CANCELLED' ? '原工单已取消，请确认故障仍存在并补充描述；提交后将生成新工单。' : '请确认或补充故障描述，提交后将生成维修工单。', '异常巡检转报修', {
      inputValue: row.remark || '', inputType: 'textarea', inputPlaceholder: '请描述故障现象',
      inputValidator: value => !!value?.trim() && value.length <= 2000 || '请填写故障描述，最多 2000 字',
      confirmButtonText: '生成工单', cancelButtonText: '取消'
    })
  } catch { return }
  convertingId.value = row.id
  try {
    await request({url:`/equipment/inspections/${row.id}/work-order`,method:'post',data:{description:result.value.trim()}})
    ElMessage.success('已生成维修工单')
    await load()
  } finally { convertingId.value = null }
}
const form = ref({ equipmentId: null, result: 'NORMAL', remark: '', createOrder: false, templateId: null, items: [] })
const templateReady = ref(false), templateLoading = ref(false), templateName = ref(''), templateError = ref(false), requireAbnormalPhoto=ref(false), stagedPhotoIds=ref([]), stagedPhotoBusy=ref(false)
let automaticallyAbnormal=false
watch(()=>form.value.items, items=>{
  if(items.some(item=>item.result==='ABNORMAL')) {
    if(form.value.result!=='ABNORMAL') { form.value.result='ABNORMAL'; automaticallyAbnormal=true }
  } else if(automaticallyAbnormal) {
    form.value.result='NORMAL'; automaticallyAbnormal=false; form.value.createOrder=false
  }
})
function onResultChange(){automaticallyAbnormal=false;form.value.createOrder=false}
let templateRequestVersion = 0
async function loadTemplate(equipmentId) {
  const version=++templateRequestVersion
  templateReady.value=false; templateLoading.value=true; templateError.value=false; templateName.value=''; requireAbnormalPhoto.value=false; stagedPhotoIds.value=[]; form.value.items=[]; form.value.templateId=null
  try {
    const data=(await request({url:'/equipment/assets/'+equipmentId+'/inspection-template',method:'get'})).data
    if(version!==templateRequestVersion) return
    form.value.templateId=data.id || null
    templateName.value=data.name || ''
    requireAbnormalPhoto.value=data.requireAbnormalPhoto === true
    form.value.items=(data.items || []).map(item=>({name:item.item_name,standard:item.standard_text || '',lowerBound:item.lower_bound,upperBound:item.upper_bound,unit:item.unit || '',measuredValue:'',templateItem:true,result:'',remark:''}))
    templateReady.value=true
  } catch { if(version===templateRequestVersion) templateError.value=true }
  finally { if(version===templateRequestVersion) templateLoading.value=false }
}
const itemDialog = ref(false), itemRows = ref([]), snapshotRows = ref([]), photoRows=ref([]), photoHasMore=ref(false), photoBusy=ref(false), inspectionPreview=ref(''), inspectionId=ref(null)
function clearInspectionPreview(){if(inspectionPreview.value) URL.revokeObjectURL(inspectionPreview.value); inspectionPreview.value=''}
onBeforeUnmount(clearInspectionPreview)
async function showInspectionPhoto(row){const version=itemRequestVersion;const blob=await request({url:'/equipment/inspections/photos/'+row.id,method:'get',responseType:'blob'});if(version!==itemRequestVersion || !itemDialog.value) return;if(!['image/jpeg','image/png'].includes(blob.type))return ElMessage.error('无法读取照片');clearInspectionPreview();inspectionPreview.value=URL.createObjectURL(blob)}
async function moreInspectionPhotos(){if(photoBusy.value || !photoRows.value.length)return;photoBusy.value=true;const version=itemRequestVersion;try{const rows=(await request({url:'/equipment/inspections/'+inspectionId.value+'/photos',method:'get',params:{afterId:photoRows.value[photoRows.value.length-1].id}})).data || [];if(version!==itemRequestVersion)return;photoRows.value=[...photoRows.value,...rows];photoHasMore.value=rows.length===20}finally{photoBusy.value=false}}
let itemRequestVersion = 0
async function showItems(row) {
  const version = ++itemRequestVersion
  const [items, snapshot, photos] = await Promise.all([
    request({url:'/equipment/inspections/'+row.id+'/items',method:'get'}),
    request({url:'/equipment/inspections/'+row.id+'/template-snapshot',method:'get'}),
    request({url:'/equipment/inspections/'+row.id+'/photos',method:'get'})
  ])
  if (version !== itemRequestVersion) return
  clearInspectionPreview(); inspectionId.value=row.id
  itemRows.value=items.data || []
  snapshotRows.value=snapshot.data || []
  photoRows.value=photos.data || []; photoHasMore.value=photoRows.value.length===20
  itemDialog.value=true
}
const selectedResult=ref('')
let loadVersion=0
async function load(more=false) {
  if(more && loading.value) return
  const version=++loadVersion, params={}
  if(selectedResult.value) params.result=selectedResult.value
  if(more && records.value.length) params.beforeId=records.value[records.value.length-1].id
  if(!more) { records.value=[]; hasMore.value=false }
  loading.value=true
  try {
    const page=(await request({url:'/equipment/inspections',method:'get',params})).data || []
    if(version!==loadVersion) return
    records.value=more ? [...records.value,...page] : page
    hasMore.value=page.length===200
  } finally { if(version===loadVersion) loading.value=false }
}
let assetSearchVersion = 0
async function searchAssets(keyword = '') { const version = ++assetSearchVersion; const response = await request({ url: '/equipment/assets', method: 'get', params: { keyword } }); if (version === assetSearchVersion) assets.value = response.data || [] }
async function open() { await searchAssets(); dialog.value = true }
async function submit() { if(stagedPhotoBusy.value) return ElMessage.warning('请等待照片上传完成'); if(requireAbnormalPhoto.value && form.value.result==='ABNORMAL' && !stagedPhotoIds.value.length) return ElMessage.warning('异常巡检请先上传照片'); if (!templateReady.value) return ElMessage.warning('请先选择设备并加载巡检配置'); if (form.value.items.some(item=>!item.name.trim())) return ElMessage.warning('请填写检查项目名称'); if (form.value.items.some(item=>!['NORMAL','ABNORMAL'].includes(item.result))) return ElMessage.warning('请选择每个检查项目的结果'); if (form.value.result==='NORMAL' && form.value.items.some(item=>item.result==='ABNORMAL')) return ElMessage.warning('存在异常项目时，请选择巡检异常'); if (!form.value.equipmentId) return ElMessage.warning('请选择设备'); if (form.value.createOrder && !form.value.remark.trim()) return ElMessage.warning('请填写异常说明'); saving.value = true; try { await request({url:'/equipment/inspections',method:'post',data:{...form.value,photoStageIds:form.value.result==='ABNORMAL' ? stagedPhotoIds.value : [],items:form.value.items.map(({name,result,remark,measuredValue})=>({name,result,remark,measuredValue:measuredValue==null || measuredValue==='' ? null : String(measuredValue)}))}}); ElMessage.success('巡检已记录'); dialog.value = false; form.value = {equipmentId:null,result:'NORMAL',remark:'',createOrder:false,templateId:null,items:[]}; templateReady.value=false; templateName.value=''; requireAbnormalPhoto.value=false; stagedPhotoIds.value=[]; automaticallyAbnormal=false; await load() } finally { saving.value = false } }
onMounted(load)
</script>
<template>
<div class="app-container"><div class="heading"><div><h2>设备巡检</h2><p>记录现场状态，异常可直接转报修</p></div><el-button v-hasPermi="['equipment:inspection:add']" type="primary" @click="open">记录巡检</el-button></div>
<div class="result-filter"><label for="inspection-result-filter">巡检结果</label><el-select id="inspection-result-filter" v-model="selectedResult" placeholder="全部结果" @change="load()"><el-option label="全部结果" value=""/><el-option label="正常" value="NORMAL"/><el-option label="异常" value="ABNORMAL"/></el-select></div>
<el-table class="desktop-records" v-loading="loading" :data="records"><el-table-column prop="code" label="设备编号" min-width="130"/><el-table-column prop="name" label="设备" min-width="120"/><el-table-column label="结果" width="100"><template #default="{row}">{{ row.result === 'NORMAL' ? '正常' : '异常' }}</template></el-table-column><el-table-column prop="remark" label="说明" min-width="180"/><el-table-column label="巡检人" min-width="100"><template #default="{row}">{{ row.inspector_name || (row.inspector_id ? `用户 ${row.inspector_id}` : '—') }}</template></el-table-column><el-table-column prop="inspected_at" label="巡检时间" min-width="180"/><el-table-column label="关联维修" min-width="150"><template #default="{row}"><el-button v-if="row.order_id" link type="primary" @click="openOrder(row)">#{{ row.order_id }} · {{ orderStatus[row.order_status] || row.order_status }}</el-button><el-button v-if="row.result === 'ABNORMAL' &amp;&amp; row.can_report" v-hasPermi="['equipment:order:report']" link type="primary" :loading="convertingId === row.id" @click="createOrderFromInspection(row)">{{ row.order_id ? '重新报修' : '转报修' }}</el-button><span v-if="row.result === 'ABNORMAL' &amp;&amp; !row.order_id &amp;&amp; !row.can_report" class="order-unavailable">已有处理记录或暂不可报修</span><el-button v-if="row.result === 'ABNORMAL'" v-hasPermi="['equipment:order:list']" link type="primary" @click="showOrderHistory(row)">工单记录</el-button><span v-if="!row.order_id &amp;&amp; row.result !== 'ABNORMAL'">—</span></template></el-table-column><el-table-column label="项目" width="100"><template #default="{row}"><el-button link type="primary" @click="showItems(row)">查看项目</el-button></template></el-table-column></el-table><div class="mobile-records" v-loading="loading"><article v-for="row in records" :key="row.id" class="inspection-card"><div class="card-heading"><div><strong>{{ row.name }}</strong><p>{{ row.code }}</p></div><span class="result-badge" :class="{ abnormal: row.result === 'ABNORMAL' }">{{ row.result === 'NORMAL' ? '正常' : '异常' }}</span></div><p class="inspection-remark">{{ row.remark || '无巡检说明' }}</p><p class="inspection-time">巡检人：{{ row.inspector_name || (row.inspector_id ? `用户 ${row.inspector_id}` : '—') }} · {{ row.inspected_at }}</p><p v-if="row.order_id" class="inspection-time">维修工单 #{{ row.order_id }} · {{ orderStatus[row.order_status] || row.order_status }}</p><el-button v-if="row.order_id" link type="primary" @click="openOrder(row)">查看维修工单</el-button><el-button v-if="row.result === 'ABNORMAL' &amp;&amp; row.can_report" v-hasPermi="['equipment:order:report']" link type="primary" :loading="convertingId === row.id" @click="createOrderFromInspection(row)">{{ row.order_id ? '重新报修' : '转报修' }}</el-button><span v-if="row.result === 'ABNORMAL' &amp;&amp; !row.order_id &amp;&amp; !row.can_report" class="order-unavailable">已有处理记录或暂不可报修</span><el-button v-if="row.result === 'ABNORMAL'" v-hasPermi="['equipment:order:list']" link type="primary" @click="showOrderHistory(row)">工单记录</el-button><el-button link type="primary" @click="showItems(row)">查看项目和照片</el-button></article><el-empty v-if="!loading && !records.length" description="暂无巡检记录" /></div><div style="text-align:center;margin:20px"><el-button v-if="hasMore" :loading="loading" @click="load(true)">加载更早巡检</el-button></div>
<el-dialog v-model="historyOpen" title="关联工单记录" width="min(95%, 560px)" @closed="closeOrderHistory"><div v-loading="historyLoading"><el-empty v-if="!historyLoading &amp;&amp; !historyRows.length" description="暂无可查看的关联工单"/><article v-for="order in historyRows" :key="order.id" class="history-order"><strong>工单 #{{ order.id }} · {{ orderStatus[order.status] || order.status }}</strong><p>{{ order.description }}</p><p>{{ order.created_at }}</p><el-button link type="primary" @click="openOrder({order_id:order.id})">查看工单详情</el-button></article><el-button v-if="historyMore" :loading="historyLoading" @click="loadOrderHistory(true)">加载更早工单</el-button></div></el-dialog>
<el-dialog v-model="itemDialog" @closed="clearInspectionPreview" title="巡检项目" width="min(95%, 620px)"><el-empty v-if="!itemRows.length" description="该记录没有项目明细"/><el-table v-else :data="itemRows"><el-table-column prop="item_name" label="项目"/><el-table-column label="结果"><template #default="{row}">{{ row.result === 'NORMAL' ? '正常' : '异常' }}</template></el-table-column><el-table-column prop="remark" label="说明"/><el-table-column label="读数"><template #default="{row}">{{ row.measured_value == null ? '—' : row.measured_value + ' ' + (row.unit || '') }}</template></el-table-column><el-table-column label="当时数值范围"><template #default="{row}">{{ row.measured_value == null ? '—' : (row.lower_bound ?? '不限') + ' ～ ' + (row.upper_bound ?? '不限') }}</template></el-table-column></el-table><template v-if="snapshotRows.length"><h4>提交时的模板：{{ snapshotRows[0].template_name }}</h4><el-table :data="snapshotRows"><el-table-column prop="item_name" label="模板项目"/><el-table-column prop="standard_text" label="当时的检查标准"/></el-table></template><p v-else>该记录没有模板快照。</p><h4>巡检照片</h4><el-empty v-if="!photoRows.length" description="暂无巡检照片"/><el-table v-else :data="photoRows"><el-table-column prop="uploaded_at" label="上传时间"/><el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="showInspectionPhoto(row)">查看</el-button></template></el-table-column></el-table><el-button v-if="photoHasMore" :loading="photoBusy" @click="moreInspectionPhotos">加载更多照片</el-button><img v-if="inspectionPreview" :src="inspectionPreview" alt="巡检照片" style="max-width:100%;max-height:500px;margin-top:12px"/></el-dialog>
<el-dialog v-model="dialog" title="记录巡检" width="min(90%, 520px)"><el-form label-position="top"><el-form-item label="设备"><el-select v-model="form.equipmentId" :disabled="stagedPhotoBusy" filterable remote :remote-method="searchAssets" @change="loadTemplate" placeholder="搜索设备编号或名称"><el-option v-for="asset in assets" :key="asset.id" :label="`${asset.code} · ${asset.name}`" :value="asset.id"/></el-select></el-form-item><el-form-item label="巡检结果"><el-radio-group v-model="form.result" @change="onResultChange"><el-radio value="NORMAL">正常</el-radio><el-radio value="ABNORMAL">异常</el-radio></el-radio-group></el-form-item><el-form-item label="说明"><el-input v-model="form.remark" type="textarea" maxlength="1000"/></el-form-item><el-form-item label="检查项目"><div v-if="templateLoading">正在加载巡检配置…</div><template v-else-if="templateReady"><p v-if="templateName">当前模板：{{ templateName }}</p><InspectionItems v-model="form.items"/></template><template v-else-if="templateError"><p>巡检配置加载失败，请检查网络后重试。</p><el-button @click="loadTemplate(form.equipmentId)">重新加载</el-button></template><p v-else>请选择设备并加载巡检配置。</p></el-form-item><InspectionPhotoStage v-if="templateReady && requireAbnormalPhoto" v-show="form.result==='ABNORMAL'" v-model="stagedPhotoIds" v-model:busy="stagedPhotoBusy" :equipment-id="form.equipmentId"/><el-checkbox v-if="form.result === 'ABNORMAL'" v-model="form.createOrder">同时生成报修工单</el-checkbox></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!templateReady || stagedPhotoBusy" @click="submit">保存</el-button></template></el-dialog></div>
</template>
<style scoped>.order-unavailable{font-size:12px;color:#7b8794;margin-right:8px}.history-order{padding:12px 0;border-bottom:1px solid #e6edf5;overflow-wrap:anywhere}.history-order p{margin:6px 0;white-space:pre-wrap}.result-filter{display:flex;align-items:center;gap:12px;margin:16px 0}.result-filter .el-select{width:180px}.result-filter label{white-space:nowrap;color:#53657a}.heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}h2{margin:0 0 8px}p{margin:0;color:#7b8794}.mobile-records{display:none}@media(max-width:767px){.desktop-records{display:none}.mobile-records{display:block;min-height:80px}.inspection-card{background:#fff;border:1px solid #e6edf5;border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px #193b560d}.card-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.card-heading strong,.card-heading p,.inspection-remark{overflow-wrap:anywhere}.card-heading p,.inspection-time{font-size:13px;margin-top:4px}.result-badge{white-space:nowrap;background:#e8f7ef;color:#198754;border-radius:99px;padding:5px 10px;font-size:12px}.result-badge.abnormal{background:#fff0ef;color:#c0362c}.inspection-remark{white-space:pre-wrap;color:#36475b;margin:14px 0 4px}.inspection-time{margin-bottom:8px}}</style>



