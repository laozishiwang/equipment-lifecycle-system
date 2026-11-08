<script setup>
import { ref, onMounted } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import MaintenanceActions from './MaintenanceActions.vue'
const mobile=useMediaQuery('(max-width: 767px)')
const dueLabels={OVERDUE:'已逾期',DUE:'今日到期',UPCOMING:'未到期',INACTIVE:'已停用'}
const plans=ref([]),assets=ref([]),creating=ref(false),completing=ref(false),recordsOpen=ref(false),records=ref([]),selected=ref(null),busy=ref(false),loading=ref(false),hasMore=ref(false)
const form=ref({equipmentId:null,title:'',intervalDays:30,nextDue:''}),done=ref({completedDate:'',notes:''})
const editing=ref(false),editForm=ref({})
function openEdit(row){selected.value=row;editForm.value={title:row.title,intervalDays:row.interval_days,nextDue:row.next_due};editing.value=true}
async function saveEdit(){if(!editForm.value.title?.trim()||!editForm.value.nextDue)return ElMessage.warning('请填写完整计划');busy.value=true;try{await request({url:'/equipment/maintenance/'+selected.value.id,method:'put',data:editForm.value});editing.value=false;ElMessage.success('计划已更新');await load()}finally{busy.value=false}}
async function deactivate(row){try{await ElMessageBox.confirm('停用后不能再登记该计划的保养记录，确定停用吗？','停用保养计划',{type:'warning'})}catch{return}await request({url:'/equipment/maintenance/'+row.id+'/deactivate',method:'post'});ElMessage.success('计划已停用');await load()}
const searchText=ref(''),appliedKeyword=ref(''),dueStatus=ref('')
let version=0,loadVersion=0
async function searchAssets(keyword=''){const v=++version;const r=await request({url:'/equipment/assets',method:'get',params:{keyword}});if(v===version)assets.value=r.data||[]}
async function load(more=false){
  if(more && loading.value)return
  const current=++loadVersion,last=plans.value[plans.value.length-1],params={}
  if(dueStatus.value)params.dueStatus=dueStatus.value
  if(appliedKeyword.value)params.keyword=appliedKeyword.value
  if(more && last)Object.assign(params,{afterActive:last.active,afterDue:last.next_due,afterId:last.id})
  if(!more){plans.value=[];hasMore.value=false}
  loading.value=true
  try{const page=(await request({url:'/equipment/maintenance',method:'get',params})).data||[];if(current!==loadVersion)return;plans.value=more?[...plans.value,...page]:page;hasMore.value=page.length===200}
  finally{if(current===loadVersion)loading.value=false}
}
function applySearch(){appliedKeyword.value=searchText.value.trim();load()}
async function openCreate(){await searchAssets();creating.value=true}
async function create(){if(!form.value.equipmentId||!form.value.title.trim()||!form.value.nextDue)return ElMessage.warning('请填写完整计划');busy.value=true;try{await request({url:'/equipment/maintenance',method:'post',data:form.value});creating.value=false;form.value={equipmentId:null,title:'',intervalDays:30,nextDue:''};ElMessage.success('计划已创建');await load()}finally{busy.value=false}}
function openComplete(row){selected.value=row;done.value={completedDate:'',notes:''};completing.value=true}
async function complete(){if(!done.value.completedDate||!done.value.notes.trim())return ElMessage.warning('请填写完成日期及保养内容');busy.value=true;try{await request({url:'/equipment/maintenance/'+selected.value.id+'/complete',method:'post',data:done.value});completing.value=false;ElMessage.success('保养已记录');await load()}finally{busy.value=false}}
const recordsPlanId=ref(null),recordsLoading=ref(false),recordsMore=ref(false)
let recordsVersion=0
async function showRecords(row){recordsPlanId.value=row.id;records.value=[];recordsMore.value=false;recordsOpen.value=true;await loadRecords()}
async function loadRecords(more=false){
  if(more && recordsLoading.value)return
  const current=++recordsVersion,planId=recordsPlanId.value
  const params=more && records.value.length ? {beforeId:records.value[records.value.length-1].id} : {}
  recordsLoading.value=true
  try{
    const page=(await request({url:'/equipment/maintenance/'+planId+'/records',method:'get',params})).data||[]
    if(current!==recordsVersion)return
    records.value=more?[...records.value,...page]:page
    recordsMore.value=page.length===200
  }finally{if(current===recordsVersion)recordsLoading.value=false}
}
function closeRecords(){recordsVersion++;recordsLoading.value=false}
function handleAction(action,row){return {edit:openEdit,deactivate,records:showRecords,complete:openComplete}[action]?.(row)}
onMounted(load)
</script>
<template><div class="app-container"><div class="heading"><div><h2>保养计划</h2><p>按周期跟进设备保养</p></div><el-button v-hasPermi="['equipment:maintenance:add']" type="primary" @click="openCreate">新增计划</el-button></div><el-alert title="计划按到期日排序，可加载更多；完成后从实际完成日期起计算下次到期日。" type="info" :closable="false"/><div class="maintenance-filter"><label for="maintenance-keyword">搜索设备或计划</label><el-input id="maintenance-keyword" v-model="searchText" maxlength="100" clearable placeholder="设备编号、名称或保养内容" @keyup.enter="applySearch" @clear="applySearch"/><el-button @click="applySearch">搜索</el-button><label for="maintenance-status">到期状态</label><el-select id="maintenance-status" v-model="dueStatus" @change="load()"><el-option label="全部状态" value=""/><el-option label="已逾期" value="OVERDUE"/><el-option label="今日到期" value="DUE"/><el-option label="未到期" value="UPCOMING"/><el-option label="已停用" value="INACTIVE"/></el-select></div><el-table v-if="!mobile" v-loading="loading" :data="plans" style="margin-top:16px"><el-table-column prop="code" label="设备编号" min-width="130"/><el-table-column prop="name" label="设备" min-width="120"/><el-table-column prop="title" label="保养内容" min-width="150"/><el-table-column prop="interval_days" label="周期（天）" width="110"/><el-table-column prop="next_due" label="下次到期" width="120"/><el-table-column label="到期状态" width="100"><template #default="{row}"><el-tag :type="row.due_status === 'OVERDUE' ? 'danger' : row.due_status === 'DUE' ? 'warning' : 'info'">{{ {OVERDUE:"已逾期",DUE:"今日到期",UPCOMING:"未到期",INACTIVE:"已停用"}[row.due_status] }}</el-tag></template></el-table-column><el-table-column label="状态" width="100"><template #default="{row}">{{ row.active ? "启用" : "停用" }}</template></el-table-column><el-table-column label="操作" width="250"><template #default="{row}"><MaintenanceActions :row="row" @action="handleAction"/></template></el-table-column></el-table><div v-else v-loading="loading" class="mobile-plans"><el-empty v-if="!loading &amp;&amp; !plans.length" description="暂无保养计划"/><article v-for="row in plans" :key="row.id" class="plan-card"><div class="plan-heading"><div><strong>{{ row.name }}</strong><p>{{ row.code }}</p></div><el-tag :type="row.due_status === 'OVERDUE' ? 'danger' : row.due_status === 'DUE' ? 'warning' : 'info'">{{ dueLabels[row.due_status] || row.due_status }}</el-tag></div><p class="plan-title">{{ row.title }}</p><p class="plan-meta">周期 {{ row.interval_days }} 天 · 下次到期 {{ row.next_due }}</p><MaintenanceActions :row="row" @action="handleAction"/></article></div><div style="text-align:center;margin:20px"><el-button v-if="hasMore" :loading="loading" @click="load(true)">加载更多计划</el-button></div>
<el-dialog v-model="creating" title="新增保养计划" width="min(95%, 520px)"><el-form label-position="top"><el-form-item label="设备"><el-select v-model="form.equipmentId" filterable remote :remote-method="searchAssets" placeholder="搜索设备"><el-option v-for="a in assets" :key="a.id" :label="`${a.code} · ${a.name}`" :value="a.id"/></el-select></el-form-item><el-form-item label="计划名称"><el-input v-model="form.title" maxlength="128"/></el-form-item><el-form-item label="周期天数"><el-input-number v-model="form.intervalDays" :min="1" :max="3650"/></el-form-item><el-form-item label="首次到期日"><el-date-picker v-model="form.nextDue" value-format="YYYY-MM-DD"/></el-form-item></el-form><template #footer><el-button @click="creating=false">取消</el-button><el-button type="primary" :loading="busy" @click="create">保存</el-button></template></el-dialog>
<el-dialog v-model="editing" title="编辑保养计划" width="min(95%, 520px)"><el-form label-position="top"><el-form-item label="计划名称"><el-input v-model="editForm.title" maxlength="128"/></el-form-item><el-form-item label="周期天数"><el-input-number v-model="editForm.intervalDays" :min="1" :max="3650"/></el-form-item><el-form-item label="下次到期日"><el-date-picker v-model="editForm.nextDue" value-format="YYYY-MM-DD"/></el-form-item></el-form><template #footer><el-button @click="editing=false">取消</el-button><el-button type="primary" :loading="busy" @click="saveEdit">保存</el-button></template></el-dialog>
<el-dialog v-model="completing" title="记录保养" width="min(95%, 520px)"><el-form label-position="top"><el-form-item label="完成日期"><el-date-picker v-model="done.completedDate" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="保养内容"><el-input v-model="done.notes" type="textarea" maxlength="2000"/></el-form-item><p>完成日期不能早于本次到期日或晚于今天。</p></el-form><template #footer><el-button @click="completing=false">取消</el-button><el-button type="primary" :loading="busy" @click="complete">提交</el-button></template></el-dialog>
<el-dialog v-model="recordsOpen" title="保养记录" width="min(95%, 700px)" @closed="closeRecords"><div v-loading="recordsLoading"><el-table v-if="!mobile" :data="records"><el-table-column prop="completed_date" label="完成日期"/><el-table-column prop="completed_by" label="操作人 ID"/><el-table-column prop="notes" label="保养内容"/></el-table><div v-else><el-empty v-if="!recordsLoading &amp;&amp; !records.length" description="暂无保养记录"/><article v-for="record in records" :key="record.id" class="record-card"><strong>{{ record.completed_date }}</strong><p class="record-notes">{{ record.notes }}</p><p>操作人 ID：{{ record.completed_by }}</p></article></div><el-button v-if="recordsMore" :loading="recordsLoading" @click="loadRecords(true)">加载更早记录</el-button></div></el-dialog></div></template>
<style scoped>.maintenance-filter{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px}.maintenance-filter label{font-size:14px;color:#53657a}.maintenance-filter .el-input{width:240px}.maintenance-filter .el-select{width:150px}@media(max-width:767px){.maintenance-filter .el-input{width:min(100%,240px)}.maintenance-filter{gap:8px}}.mobile-plans{margin-top:16px;min-height:80px}.plan-card,.record-card{background:#fff;border:1px solid #e6edf5;border-radius:14px;padding:16px;margin-bottom:12px}.plan-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.plan-heading strong,.plan-heading p,.plan-title,.record-notes{overflow-wrap:anywhere}.plan-heading p,.plan-meta,.record-card p{font-size:13px;margin-top:5px}.plan-title{color:#36475b;margin:14px 0 4px;white-space:pre-wrap}.plan-meta{margin-bottom:10px}.record-notes{color:#36475b;white-space:pre-wrap}.heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}h2{margin:0 0 8px}p{margin:0;color:#7b8794}</style>



