<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMediaQuery } from '@vueuse/core'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import OrderActions from './OrderActions.vue'
import OrderHistory from './OrderHistory.vue'
import useUserStore from '@/store/modules/user'
const user = useUserStore()
const ratingStars=ref(5), ratingRemark=ref(''), ratingSaving=ref(false)
async function submitRating(){ ratingSaving.value=true; try { await request({url:`/equipment/orders/${detail.value.id}/rating`,method:'post',data:{stars:ratingStars.value,remark:ratingRemark.value}}); ElMessage.success('评价已提交'); await showDetail({id:detail.value.id}) } finally { ratingSaving.value=false } }
const mobile=useMediaQuery('(max-width: 767px)')
const orders = ref([]), assets = ref([]), loading = ref(false), reportOpen = ref(false), completeOpen = ref(false)
const report = ref({ equipmentId: null, description: '' })
const hasMore=ref(false), selectedStatus=ref(''),searchText=ref(''),appliedKeyword=ref('')
let loadVersion=0
async function cancelOrder(row,withdraw){let response;try{response=await ElMessageBox.prompt(withdraw?'请输入撤回原因':'请输入取消原因',withdraw?'撤回报修':'取消工单',{confirmButtonText:'确定',cancelButtonText:'取消',inputType:'textarea',inputValidator:value=>value && value.trim() && value.length<=1000 ? true : '请输入不超过 1000 字的原因'})}catch{return}await request({url:'/equipment/orders/'+row.id+(withdraw?'/withdraw':'/cancel'),method:'post',data:{reason:response.value}});ElMessage.success(withdraw?'已撤回':'已取消');await load()}
const current = ref(null)
const assignOpen=ref(false),technicians=ref([]),assignment=ref({technicianId:null,reason:''}),assigning=ref(false)
async function openAssign(row){current.value=row;technicians.value=(await request({url:'/equipment/orders/technicians',method:'get'})).data||[];assignment.value={technicianId:null,reason:''};assignOpen.value=true}
async function submitAssignment(){if(!assignment.value.technicianId||!assignment.value.reason.trim())return ElMessage.warning('请选择维修人员并填写原因');assigning.value=true;try{await request({url:'/equipment/orders/'+current.value.id+'/assign',method:'post',data:assignment.value});assignOpen.value=false;ElMessage.success('转派成功');await load()}finally{assigning.value=false}}
const trialOpen=ref(false),trialForm=ref({result:'PASS',notes:''}),trialSaving=ref(false)
function openTrial(row){current.value=row;trialForm.value={result:'PASS',notes:''};trialOpen.value=true}
async function submitTrial(){if(trialForm.value.result==='FAIL'&&!trialForm.value.notes.trim())return ElMessage.warning('未通过时请填写说明');trialSaving.value=true;try{await request({url:'/equipment/orders/'+current.value.id+'/trial',method:'post',data:trialForm.value});trialOpen.value=false;ElMessage.success('试运行已记录');await load()}finally{trialSaving.value=false}}
const photos=ref([]), selectedPhoto=ref(null), photoBusy=ref(false), photoInput=ref(null), previewUrl=ref('')
function clearPhotoPreview(){previewUrl.value='';selectedPhoto.value=null}
const photoHasMore=ref(false), photoListBusy=ref(false), thumbnails=ref({}), thumbnailLoading=ref({})
let thumbnailVersion=0
function clearThumbnails(){thumbnailVersion++;Object.values(thumbnails.value).forEach(url=>URL.revokeObjectURL(url));thumbnails.value={};thumbnailLoading.value={}}
function closeDetail(){clearPhotoPreview();clearThumbnails();photos.value=[]}
async function loadThumbnail(row,version){thumbnailLoading.value={...thumbnailLoading.value,[row.id]:true};try{const blob=await request({url:'/equipment/orders/photos/'+row.id,method:'get',responseType:'blob',timeout:90000});if(version===thumbnailVersion && detailOpen.value && ['image/jpeg','image/png'].includes(blob.type)) thumbnails.value={...thumbnails.value,[row.id]:URL.createObjectURL(blob)}}catch{/* 可点击重试 */}finally{if(version===thumbnailVersion)thumbnailLoading.value={...thumbnailLoading.value,[row.id]:false}}}
async function loadPhotos(append=false){
  if(photoListBusy.value)return
  photoListBusy.value=true
  try {
    const afterId=append && photos.value.length ? photos.value[photos.value.length-1].id : undefined
    const rows=(await request({url:'/equipment/orders/'+detail.value.id+'/photos',method:'get',params:afterId ? {afterId} : {}})).data||[]
    if(!append)clearThumbnails()
    photos.value=append ? [...photos.value,...rows] : rows
    const version=thumbnailVersion
    rows.forEach(row=>loadThumbnail(row,version))
    photoHasMore.value=rows.length===20
  } finally { photoListBusy.value=false }
}
async function showPhoto(row){if(thumbnailLoading.value[row.id])return;if(!thumbnails.value[row.id])await loadThumbnail(row,thumbnailVersion);if(thumbnails.value[row.id])previewUrl.value=thumbnails.value[row.id];else ElMessage.error('无法读取照片，请重试')}
async function uploadPhoto(){if(!selectedPhoto.value)return ElMessage.warning('请选择照片');if(selectedPhoto.value.size>5*1024*1024)return ElMessage.warning('照片不能超过 5 MB');photoBusy.value=true;try{const form=new FormData();form.append('file',selectedPhoto.value);await request({url:'/equipment/orders/'+detail.value.id+'/photos',method:'post',data:form,headers:{'Content-Type':undefined,isRepeatSubmit:false}});selectedPhoto.value=null;if(photoInput.value)photoInput.value.value='';ElMessage.success('照片已上传');await loadPhotos()}finally{photoBusy.value=false}}
onBeforeUnmount(closeDetail)
const detailOpen = ref(false), detail = ref(null)
const route = useRoute()
async function showDetail(row) { closeDetail(); detail.value = (await request({ url: '/equipment/orders/' + row.id, method: 'get' })).data; detailOpen.value = true; await loadPhotos() }
const costOpen = ref(false), costRows = ref([])
async function showCosts(row) { current.value = row; costRows.value = (await request({ url: '/equipment/orders/' + row.id + '/costs', method: 'get' })).data || []; costOpen.value = true }
const completeSaving=ref(false)
const completion = ref({ repairDate: '', diagnosis: '', faultCategory: null, faultCodeId: null, description: '', costs: [] })
const currentRepairTotal = computed(() => (completion.value.costs.reduce((total, item) => {
  const amount = Number(item.amount)
  return total + (Number.isFinite(amount) ? Math.round(amount * 100) : 0)
}, 0) / 100).toFixed(2))
const faultCategories = {MECHANICAL:'机械故障',ELECTRICAL:'电气故障',HYDRAULIC:'液压气动',CONTROL:'控制与仪表',OTHER:'其他'}
const labels = { NEW: '创建', REPORTED: '待接单', ACCEPTED: '待到场', ARRIVED: '维修中', TESTING: '待试运行', COMPLETED: '待确认', CLOSED: '已关闭', CANCELLED: '已取消' }
async function load(more=false) {
  if (more && loading.value) return
  const version = ++loadVersion
  const params = {}
  if (selectedStatus.value) params.status = selectedStatus.value
  if (appliedKeyword.value) params.keyword = appliedKeyword.value
  if (more && orders.value.length) params.beforeId = orders.value[orders.value.length-1].id
  if (!more) { orders.value = []; hasMore.value = false }
  loading.value = true
  try {
    const page = (await request({ url: '/equipment/orders', method: 'get', params })).data || []
    if (version !== loadVersion) return
    orders.value = more ? [...orders.value, ...page] : page
    hasMore.value = page.length === 200
  } finally { if (version === loadVersion) loading.value = false }
}
function applySearch(){appliedKeyword.value=searchText.value.trim();load()}
let assetSearchVersion = 0
async function searchAssets(keyword = '') { const version = ++assetSearchVersion; const response = await request({ url: '/equipment/assets', method: 'get', params: { keyword } }); if (version === assetSearchVersion) assets.value = response.data || [] }
async function openReport() { await searchAssets(); reportOpen.value = true }
async function submitReport() { if (!report.value.equipmentId || !report.value.description.trim()) return ElMessage.warning('请选择设备并填写故障描述'); await request({ url: '/equipment/orders', method: 'post', data: report.value }); reportOpen.value = false; report.value = { equipmentId: null, description: '' }; ElMessage.success('报修已提交'); await load() }
async function arrive(row) { await request({ url: '/equipment/orders/' + row.id + '/arrive', method: 'post' }); ElMessage.success('已记录到场'); await load() }
async function accept(row) { await request({ url: `/equipment/orders/${row.id}/accept`, method: 'post' }); ElMessage.success('接单成功'); await load() }
const faultCodes=ref([]), faultCodesBusy=ref(false), faultCodesMore=ref(false)
async function loadFaultCodes(more=false){if(faultCodesBusy.value)return;faultCodesBusy.value=true;try{const params=more&&faultCodes.value.length?{afterId:faultCodes.value[faultCodes.value.length-1].id}:{};const data=(await request({url:'/equipment/fault-codes',method:'get',params})).data||[];faultCodes.value=more?[...faultCodes.value,...data]:data;faultCodesMore.value=data.length===200}finally{faultCodesBusy.value=false}}
async function openComplete(row) { current.value = row; completion.value = { repairDate: '', diagnosis: '', faultCategory: null, faultCodeId: null, description: '', costs: [] }; faultCodes.value=[];faultCodesMore.value=false;completeOpen.value = true;await loadFaultCodes() }
async function submitComplete() { if (completeSaving.value) return; if (!completion.value.repairDate || !completion.value.description.trim()) return ElMessage.warning('请填写维修日期和维修内容'); if (completion.value.costs.some(cost => !cost.description.trim())) return ElMessage.warning('请填写每项费用的说明'); if (completion.value.costs.some(cost => cost.amount == null || !Number.isFinite(Number(cost.amount)) || Number(cost.amount) < 0 || Number(cost.amount) > 9999999999.99)) return ElMessage.warning('请填写有效的费用金额'); completeSaving.value=true; try { await request({ url: `/equipment/orders/${current.value.id}/complete`, method: 'post', data: {...completion.value, faultCategory: completion.value.faultCategory || null, faultCodeId: completion.value.faultCodeId || null} }); completeOpen.value = false; ElMessage.success('维修记录已提交，请完成试运行'); await load() } finally { completeSaving.value=false } }
async function close(row) { await request({ url: `/equipment/orders/${row.id}/close`, method: 'post' }); ElMessage.success('工单已关闭'); await load() }
function handleOrderAction(action, row) {
  const handlers = {
    trial: openTrial, assign: openAssign, withdraw: item => cancelOrder(item, true),
    cancel: item => cancelOrder(item, false), detail: showDetail, costs: showCosts,
    accept, arrive, complete: openComplete, close
  }
  return handlers[action]?.(row)
}
async function openLinkedOrder(value) {
  const id=String(value ?? '')
  if (!/^[1-9]\d{0,14}$/.test(id)) return
  await showDetail({id})
}
onMounted(async()=>{await load();await openLinkedOrder(route.query.open)})
watch(()=>route.query.open,(value,previous)=>{if(value!==previous) openLinkedOrder(value)})
</script>
<template>
  <div class="app-container">
    <div class="heading"><div><h2>维修工单</h2><p>跟踪现场报修和维修进度</p></div><el-button v-hasPermi="['equipment:order:report']" type="primary" @click="openReport">提交报修</el-button></div>
    <el-alert title="按创建顺序显示工单，可加载更早记录" type="info" :closable="false" />
    <div class="order-filter"><label for="order-keyword">搜索工单</label><el-input id="order-keyword" v-model="searchText" maxlength="100" clearable placeholder="设备、故障描述或工单号" @keyup.enter="applySearch" @clear="applySearch"/><el-button @click="applySearch">搜索</el-button><label for="order-status-filter">工单状态</label><el-select id="order-status-filter" v-model="selectedStatus" placeholder="全部状态" @change="load()"><el-option label="全部状态" value=""/><el-option v-for="status in ['REPORTED','ACCEPTED','ARRIVED','TESTING','COMPLETED','CLOSED','CANCELLED']" :key="status" :label="labels[status]" :value="status"/></el-select></div>
    <el-table class="desktop-orders" v-loading="loading" :data="orders" style="margin-top:16px">
      <el-table-column prop="code" label="设备编号" min-width="120"/><el-table-column prop="name" label="设备" min-width="120"/><el-table-column label="报修人" min-width="100"><template #default="{row}">{{ row.reporter_name || (row.reporter_id ? `用户 ${row.reporter_id}` : '—') }}</template></el-table-column><el-table-column prop="description" label="故障描述" min-width="180"/><el-table-column label="状态" width="100"><template #default="{row}">{{ labels[row.status] || row.status }}</template></el-table-column>
      <el-table-column label="操作" width="430" fixed="right"><template #default="{row}"><OrderActions :row="row" @action="handleOrderAction" /></template></el-table-column>
    </el-table>
    <div class="mobile-orders" v-loading="loading">
      <p v-if="!loading && !orders.length" class="empty-orders">暂无维修工单</p>
      <article v-for="row in orders" :key="row.id" class="order-card">
        <div class="card-heading"><div><strong>{{ row.name }}</strong><p>{{ row.code }}</p></div><span class="order-status">{{ labels[row.status] || row.status }}</span></div>
        <p class="order-description">{{ row.description }}</p><p>报修人：{{ row.reporter_name || (row.reporter_id ? `用户 ${row.reporter_id}` : '—') }}</p>
        <OrderActions :row="row" @action="handleOrderAction" />
      </article>
    </div>
    <div style="text-align:center;margin:20px"><el-button v-if="hasMore" :loading="loading" @click="load(true)">加载更早工单</el-button></div>
    <el-dialog v-model="trialOpen" title="记录试运行" width="min(95%, 520px)"><el-form label-position="top"><el-form-item label="试运行结果"><el-radio-group v-model="trialForm.result"><el-radio value="PASS">通过</el-radio><el-radio value="FAIL">未通过，返回维修</el-radio></el-radio-group></el-form-item><el-form-item label="说明"><el-input v-model="trialForm.notes" type="textarea" maxlength="1000" placeholder="未通过时必填"/></el-form-item></el-form><template #footer><el-button @click="trialOpen=false">取消</el-button><el-button type="primary" :loading="trialSaving" @click="submitTrial">提交</el-button></template></el-dialog>
    <el-dialog v-model="assignOpen" title="转派维修工单" width="min(95%, 520px)"><el-form label-position="top"><el-form-item label="新维修人员"><el-select v-model="assignment.technicianId" filterable placeholder="选择维修人员"><el-option v-for="person in technicians" :key="person.user_id" :value="person.user_id" :label="`${person.nick_name} (${person.user_name})`"/></el-select></el-form-item><el-form-item label="转派原因"><el-input v-model="assignment.reason" type="textarea" maxlength="1000"/></el-form-item></el-form><template #footer><el-button @click="assignOpen=false">取消</el-button><el-button type="primary" :loading="assigning" @click="submitAssignment">确认转派</el-button></template></el-dialog>
    <el-dialog v-model="detailOpen" title="维修工单详情" @closed="closeDetail" width="min(94%, 820px)" class="order-detail-dialog">
      <template v-if="detail">
        <section class="detail-section"><h3>报修信息 <el-tag>{{ labels[detail.status] || detail.status }}</el-tag></h3>
          <el-descriptions :column="mobile ? 1 : 2" border>
            <el-descriptions-item label="工单号">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="设备">{{ detail.code }} · {{ detail.name }}</el-descriptions-item>
            <el-descriptions-item label="报修人">{{ detail.reporter_name || detail.reporter_id }}</el-descriptions-item>
            <el-descriptions-item label="维修人">{{ detail.technician_id || '未接单' }}</el-descriptions-item>
            <el-descriptions-item label="故障描述" :span="mobile ? 1 : 2">{{ detail.description }}</el-descriptions-item>
          </el-descriptions>
          <el-alert v-if="detail.cancellation" :title="'取消原因：' + detail.cancellation.reason" type="warning" :closable="false"/>
        </section>
        <section class="detail-section"><h3>现场照片 <span class="section-note">{{ photos.length }} 张</span></h3>
          <p v-if="!photos.length && !photoListBusy" class="detail-empty">暂无照片</p>
          <div v-loading="photoListBusy" class="photo-list"><article v-for="(row, index) in photos" :key="row.id" class="photo-item"><img v-if="thumbnails[row.id]" :src="thumbnails[row.id]" :alt="`现场照片 ${index + 1}`" class="photo-thumb" @click="showPhoto(row)"/><div v-else class="photo-placeholder">{{ thumbnailLoading[row.id] ? '加载中…' : '图片未加载' }}</div><div><strong>照片 {{ index + 1 }}</strong><p>{{ row.uploaded_at }}</p></div><el-button type="primary" plain @click="showPhoto(row)">查看照片</el-button></article></div>
          <el-button v-if="photoHasMore" :loading="photoListBusy" @click="loadPhotos(true)">加载更多照片</el-button>
          <img v-if="previewUrl" :src="previewUrl" alt="工单现场照片" class="photo-preview"/>
          <div v-if="!['CLOSED','CANCELLED'].includes(detail.status)" v-hasPermi="['equipment:order:photo']" class="photo-upload"><input ref="photoInput" type="file" accept="image/jpeg,image/png" @change="selectedPhoto=$event.target.files?.[0] || null"/><el-button :loading="photoBusy" @click="uploadPhoto">上传照片</el-button><p>每张照片不超过 5 MB</p></div>
        </section>
        <section class="detail-section"><h3>维修记录</h3><el-descriptions :column="mobile ? 1 : 2" border><el-descriptions-item label="维修日期">{{ detail.repair_date || '尚未记录' }}</el-descriptions-item><el-descriptions-item label="维修内容">{{ detail.repair_description || '尚未记录' }}</el-descriptions-item></el-descriptions><OrderHistory :detail="detail" :labels="labels" :fault-categories="faultCategories"/></section>
        <section class="detail-section"><h3>维修评价</h3><div v-if="detail.rating"><el-rate :model-value="detail.rating.stars" disabled/><p>{{ detail.rating.remark || '无备注' }}</p></div><div v-else-if="detail.status === 'CLOSED' && String(detail.reporter_id) === String(user.id)"><el-rate v-model="ratingStars"/><el-input v-model="ratingRemark" type="textarea" maxlength="500" placeholder="补充评价（选填）"/><el-button type="primary" :loading="ratingSaving" @click="submitRating">提交评价</el-button></div><p v-else class="detail-empty">暂无评价</p></section>
      </template>
    </el-dialog>
    <el-dialog v-model="costOpen" title="维修费用" width="min(95%, 560px)"><el-table v-if="!mobile" :data="costRows"><el-table-column label="维修记录" min-width="150"><template #default="{row}">{{row.repair_id ? `#${row.repair_id} · ${row.repair_date}` : "历史记录"}}</template></el-table-column><el-table-column label="类别"><template #default="{row}">{{ {LABOR:"人工费",PARTS:"配件费",OTHER:"其他"}[row.category] }}</template></el-table-column><el-table-column prop="description" label="说明"/><el-table-column prop="amount" label="金额（元）"/></el-table><div v-else><p v-if="!costRows.length" class="detail-empty">暂无费用记录</p><article v-for="row in costRows" :key="row.id" class="detail-card"><strong>{{ {LABOR:"人工费",PARTS:"配件费",OTHER:"其他"}[row.category] }} · ¥ {{ Number(row.amount).toFixed(2) }}</strong><p>{{ row.description }}</p><p>{{ row.repair_id ? `维修记录 #${row.repair_id} · ${row.repair_date}` : "历史记录" }}</p></article></div><p>合计：¥ {{ (costRows.reduce((sum, item) => sum + Math.round(Number(item.amount) * 100), 0) / 100).toFixed(2) }}</p></el-dialog>
    <el-dialog v-model="reportOpen" title="提交报修" width="min(90%, 520px)"><el-form label-position="top"><el-form-item label="设备"><el-select v-model="report.equipmentId" filterable remote :remote-method="searchAssets" placeholder="搜索设备编号或名称"><el-option v-for="asset in assets" :key="asset.id" :label="`${asset.code} · ${asset.name}`" :value="asset.id"/></el-select></el-form-item><el-form-item label="故障描述"><el-input v-model="report.description" type="textarea" maxlength="2000" /></el-form-item></el-form><template #footer><el-button @click="reportOpen=false">取消</el-button><el-button type="primary" @click="submitReport">提交</el-button></template></el-dialog>
    <el-dialog v-model="completeOpen" title="填写维修记录" width="min(95%, 650px)" :close-on-click-modal="!completeSaving" :close-on-press-escape="!completeSaving" :show-close="!completeSaving"><el-form label-position="top" :disabled="completeSaving"><el-form-item label="维修日期"><el-date-picker v-model="completion.repairDate" type="date" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="故障类别（选填）"><el-select v-model="completion.faultCategory" clearable placeholder="请选择故障类别"><el-option v-for="(label, value) in faultCategories" :key="value" :label="label" :value="value"/></el-select></el-form-item><el-form-item label="故障代码（选填）"><el-select v-model="completion.faultCodeId" filterable clearable placeholder="选择已启用的代码"><el-option v-for="item in faultCodes" :key="item.id" :value="item.id" :label="`${item.code} · ${item.category} / ${item.part} / ${item.symptom}`"/></el-select><el-button v-if="faultCodesMore" :loading="faultCodesBusy" @click="loadFaultCodes(true)">加载更多代码</el-button></el-form-item><el-form-item label="诊断原因（选填）"><el-input v-model="completion.diagnosis" type="textarea" maxlength="2000" show-word-limit placeholder="例如轴承磨损、传感器故障"/></el-form-item><el-form-item label="维修方法"><el-input v-model="completion.description" type="textarea" maxlength="2000"/></el-form-item><el-form-item label="费用明细"><div v-for="(cost,i) in completion.costs" :key="i" class="cost"><el-select v-model="cost.category" style="width:110px"><el-option label="人工费" value="LABOR"/><el-option label="配件费" value="PARTS"/><el-option label="其他" value="OTHER"/></el-select><el-input v-model="cost.description" placeholder="费用说明（必填）" maxlength="255"/><el-input-number v-model="cost.amount" :min="0" :max="9999999999.99" :precision="2"/><el-button link type="danger" @click="completion.costs.splice(i,1)">删除</el-button></div><el-button @click="completion.costs.push({category:'LABOR',description:'',amount:0})">添加费用</el-button><p class="repair-total">本次维修合计：¥ {{ currentRepairTotal }}</p></el-form-item></el-form><template #footer><el-button :disabled="completeSaving" @click="completeOpen=false">取消</el-button><el-button type="primary" :loading="completeSaving" @click="submitComplete">提交完工</el-button></template></el-dialog>
  </div>
</template>
<style scoped>:deep(.el-descriptions__cell){overflow-wrap:anywhere;word-break:break-word}input[type=file]{max-width:100%}.detail-card{padding:12px;margin:8px 0;border:1px solid #e6edf5;border-radius:10px;background:#f6f9fc;overflow-wrap:anywhere}.detail-card p{margin:6px 0;white-space:pre-wrap}.detail-empty{padding:12px 0;font-size:14px}.heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}h2{margin:0 0 8px}p{margin:0;color:#7b8794}.cost{display:flex;gap:8px;width:100%;margin-bottom:8px;flex-wrap:wrap}.order-filter{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px}.order-filter .el-input{width:240px}.order-filter .el-select{width:180px}.order-filter label{white-space:nowrap;color:#53657a}.repair-total{width:100%;margin:8px 0 0;color:#243b53;font-weight:600}.mobile-orders{display:none}
@media (max-width:767px){
  .desktop-orders{display:none}
  .mobile-orders{display:block;margin-top:16px;min-height:80px}
  .order-card{background:#fff;border:1px solid #e6edf5;border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px #193b560d}
  .card-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
  .card-heading strong{font-size:16px;overflow-wrap:anywhere}
  .card-heading p{font-size:13px;margin-top:4px;overflow-wrap:anywhere}
  .order-status{white-space:nowrap;background:#eaf3ff;color:#2468b4;border-radius:99px;padding:5px 10px;font-size:12px}
  .order-description{color:#36475b;white-space:pre-wrap;overflow-wrap:anywhere;margin:14px 0}
  .empty-orders{text-align:center;padding:24px}
}
</style>















<style scoped>
.detail-section{padding:0 0 22px;margin-bottom:22px;border-bottom:1px solid #e8edf3}.detail-section:last-child{border-bottom:0;margin-bottom:0}.detail-section h3{display:flex;align-items:center;gap:10px;color:#1d3449;font-size:16px;margin:0 0 14px}.section-note,.detail-empty{font-size:13px;color:#8391a0;font-weight:400}.photo-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.photo-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px;border:1px solid #e5ebf1;border-radius:8px}.photo-thumb,.photo-placeholder{width:80px;height:64px;object-fit:cover;border-radius:6px;cursor:pointer}.photo-placeholder{display:grid;place-items:center;background:#f2f5f8;color:#8391a0;font-size:12px}.photo-item p,.photo-upload p{margin:5px 0 0;color:#8391a0;font-size:12px}.photo-preview{display:block;max-width:100%;max-height:500px;margin-top:14px;border-radius:8px}.photo-upload{margin-top:16px}.photo-upload input{max-width:100%;margin-right:8px}@media(max-width:767px){.photo-list{grid-template-columns:1fr}.photo-item{flex-wrap:wrap}}
</style>
