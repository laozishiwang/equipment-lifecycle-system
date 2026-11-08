<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import InspectionItems from '@/views/equipment/inspections/InspectionItems.vue'
import InspectionPhotoStage from '@/views/equipment/inspections/InspectionPhotoStage.vue'
const route=useRoute(), asset=ref(null), description=ref(''), result=ref('NORMAL'), remark=ref(''), createOrder=ref(false), busy=ref(false), lastOrderId=ref(null), photo=ref(null), photoBusy=ref(false)
async function sendReport(){if(busy.value || !asset.value) return;if(!description.value.trim()) return ElMessage.warning('请描述故障');const version=fieldVersion;busy.value=true; try{const response=await request({url:'/equipment/orders',method:'post',data:{equipmentId:Number(route.params.id),description:description.value}});if(version!==fieldVersion)return;lastOrderId.value=response.data.id;photo.value=null;if(photoInput.value)photoInput.value.value='';description.value='';ElMessage.success('报修已提交，可补充现场照片')}finally{busy.value=false}}
async function sendInspection(){if(busy.value || !templateReady.value)return;if(stagedPhotoBusy.value) return ElMessage.warning('请等待照片上传完成');if(requireAbnormalPhoto.value && result.value==='ABNORMAL' && !stagedPhotoIds.value.length) return ElMessage.warning('异常巡检请先上传照片');if(inspectionItems.value.some(item=>!item.name.trim())) return ElMessage.warning('请填写检查项目名称');if(inspectionItems.value.some(item=>!['NORMAL','ABNORMAL'].includes(item.result))) return ElMessage.warning('请选择每个检查项目的结果');if(result.value==='NORMAL' && inspectionItems.value.some(item=>item.result==='ABNORMAL')) return ElMessage.warning('存在异常项目时，请选择巡检异常');if(createOrder.value && !remark.value.trim()) return ElMessage.warning('请填写异常说明');const version=fieldVersion;busy.value=true;try{const response=await request({url:'/equipment/inspections',method:'post',data:{equipmentId:Number(route.params.id),result:result.value,remark:remark.value,createOrder:createOrder.value,templateId:templateId.value,photoStageIds:result.value==='ABNORMAL' ? stagedPhotoIds.value : [],items:inspectionItems.value.map(({name,result,remark,measuredValue})=>({name,result,remark,measuredValue:measuredValue==null || measuredValue==='' ? null : String(measuredValue)}))}});if(version!==fieldVersion)return;lastInspectionId.value=response.data.inspectionId;inspectionPhoto.value=null;if(inspectionPhotoInput.value)inspectionPhotoInput.value.value='';if(response.data.orderId){lastOrderId.value=response.data.orderId;photo.value=null;if(photoInput.value)photoInput.value.value=''}remark.value='';createOrder.value=false;stagedPhotoIds.value=[];resetInspectionItems();ElMessage.success('巡检已记录')}finally{busy.value=false}}
const inspectionItems=ref([]), templateItems=ref([]), templateName=ref(''), templateId=ref(null), requireAbnormalPhoto=ref(false), stagedPhotoIds=ref([]), stagedPhotoBusy=ref(false), templateReady=ref(false), fieldLoading=ref(false), fieldError=ref(false)
let automaticallyAbnormal=false
watch(inspectionItems, items=>{
  if(items.some(item=>item.result==='ABNORMAL')) {
    if(result.value!=='ABNORMAL') { result.value='ABNORMAL'; automaticallyAbnormal=true }
  } else if(automaticallyAbnormal) {
    result.value='NORMAL'; automaticallyAbnormal=false; createOrder.value=false
  }
})
function onResultChange(){automaticallyAbnormal=false;createOrder.value=false}
function resetInspectionItems(){inspectionItems.value=templateItems.value.map(item=>({...item,result:'',remark:''}))}
const photoInput=ref(null), lastInspectionId=ref(null), inspectionPhoto=ref(null), inspectionPhotoInput=ref(null), inspectionPhotoBusy=ref(false)
async function uploadInspectionPhoto(){
  if(inspectionPhotoBusy.value || !lastInspectionId.value) return
  if(!inspectionPhoto.value) return ElMessage.warning('请选择照片')
  if(inspectionPhoto.value.size>5*1024*1024) return ElMessage.warning('照片不能超过 5 MB')
  const version=fieldVersion, id=lastInspectionId.value
  inspectionPhotoBusy.value=true
  try { const form=new FormData(); form.append('file',inspectionPhoto.value); await request({url:'/equipment/inspections/'+id+'/photos',method:'post',data:form,headers:{'Content-Type':undefined,isRepeatSubmit:false}}); if(version!==fieldVersion || lastInspectionId.value!==id)return;inspectionPhoto.value=null; if(inspectionPhotoInput.value) inspectionPhotoInput.value.value=''; ElMessage.success('巡检照片已上传') }
  finally { inspectionPhotoBusy.value=false }
}
async function uploadPhoto(){if(photoBusy.value || !lastOrderId.value)return;if(!photo.value)return ElMessage.warning('请选择照片');if(photo.value.size>5*1024*1024)return ElMessage.warning('照片不能超过 5 MB');const version=fieldVersion,id=lastOrderId.value;photoBusy.value=true;try{const form=new FormData();form.append('file',photo.value);await request({url:'/equipment/orders/'+id+'/photos',method:'post',data:form,headers:{'Content-Type':undefined,isRepeatSubmit:false}});if(version!==fieldVersion || lastOrderId.value!==id)return;photo.value=null;if(photoInput.value)photoInput.value.value='';ElMessage.success('照片已上传')}finally{photoBusy.value=false}}
let fieldVersion=0,fieldLoadVersion=0
async function loadField(){
  const version=++fieldLoadVersion, equipmentId=route.params.id
  fieldLoading.value=true; fieldError.value=false
  try {
    const loadedAsset=(await request({url:`/equipment/assets/${equipmentId}`,method:'get'})).data
    if(version!==fieldLoadVersion)return
    asset.value=loadedAsset
    const data=(await request({url:`/equipment/assets/${equipmentId}/inspection-template`,method:'get'})).data
    if(version!==fieldLoadVersion)return
    templateName.value=data.name || ''
    templateId.value=data.id || null
    requireAbnormalPhoto.value=data.requireAbnormalPhoto === true
    templateItems.value=(data.items || []).map(item=>({name:item.item_name,standard:item.standard_text || '',lowerBound:item.lower_bound,upperBound:item.upper_bound,unit:item.unit || '',measuredValue:'',templateItem:true}))
    resetInspectionItems()
    templateReady.value=true
  } catch { if(version===fieldLoadVersion)fieldError.value=true }
  finally { if(version===fieldLoadVersion)fieldLoading.value=false }
}
watch(()=>route.params.id,()=>{
  fieldVersion++
  asset.value=null;description.value='';result.value='NORMAL';remark.value='';createOrder.value=false;automaticallyAbnormal=false
  lastOrderId.value=null;photo.value=null;lastInspectionId.value=null;inspectionPhoto.value=null
  templateReady.value=false;templateName.value='';templateId.value=null;templateItems.value=[];inspectionItems.value=[];requireAbnormalPhoto.value=false;stagedPhotoIds.value=[]
  if(photoInput.value)photoInput.value.value='';if(inspectionPhotoInput.value)inspectionPhotoInput.value.value=''
  if (route.params.id) loadField()
  else fieldLoadVersion++
},{immediate:true,flush:'sync'})
</script>
<template><main class="field"><header><span>设备现场</span><h1>{{ asset?.name || (fieldError ? '设备加载失败' : '正在加载设备') }}</h1><p>{{ asset?.code }}　{{ asset?.location }}</p><el-button v-hasPermi="['equipment:order:list']" plain @click="$router.push('/equipment/orders')">查看维修工单</el-button></header><section><h2>快速报修</h2><el-input v-model="description" type="textarea" :rows="3" placeholder="请描述故障现象" maxlength="2000"/><el-button v-hasPermi="['equipment:order:report']" type="primary" :loading="busy" :disabled="!asset" @click="sendReport">提交报修</el-button></section><section v-if="lastOrderId" v-hasPermi="['equipment:order:photo']"><h2>补充报修照片</h2><p>工单 #{{ lastOrderId }} 已提交，可选择 JPEG 或 PNG 照片（最大 5 MB）。</p><input ref="photoInput" type="file" accept="image/jpeg,image/png" @change="photo=$event.target.files?.[0] || null"/><el-button type="primary" plain :loading="photoBusy" @click="uploadPhoto">上传照片</el-button></section><section v-if="templateReady"><h2>设备巡检</h2><el-radio-group v-model="result" @change="onResultChange"><el-radio value="NORMAL">正常</el-radio><el-radio value="ABNORMAL">异常</el-radio></el-radio-group><el-input v-model="remark" type="textarea" :rows="3" placeholder="填写巡检说明" maxlength="1000"/><p v-if="templateName">当前模板：{{ templateName }}（请逐项核对）</p><InspectionItems v-model="inspectionItems"/><InspectionPhotoStage v-if="requireAbnormalPhoto" v-show="result==='ABNORMAL'" v-model="stagedPhotoIds" v-model:busy="stagedPhotoBusy" :equipment-id="route.params.id"/><el-checkbox v-if="result==='ABNORMAL'" v-model="createOrder">同时生成报修单</el-checkbox><el-button v-hasPermi="['equipment:inspection:add']" type="primary" plain :loading="busy" :disabled="stagedPhotoBusy" @click="sendInspection">保存巡检</el-button></section><section v-else><h2>设备巡检</h2><p v-if="fieldError">设备或巡检配置加载失败，请检查网络后重试。</p><p v-else>正在加载设备和巡检配置…</p><el-button v-if="fieldError" :loading="fieldLoading" @click="loadField">重新加载</el-button></section><section v-if="lastInspectionId" v-hasPermi="['equipment:inspection:add']"><h2>补充巡检照片</h2><p>巡检 #{{ lastInspectionId }} 已记录，可上传 JPEG 或 PNG 照片（最大 5 MB）。</p><input ref="inspectionPhotoInput" type="file" accept="image/jpeg,image/png" @change="inspectionPhoto=$event.target.files?.[0] || null"/><el-button plain :loading="inspectionPhotoBusy" @click="uploadInspectionPhoto">上传巡检照片</el-button></section></main></template>
<style scoped>.field{width:100%;max-width:600px;margin:auto;padding:24px 16px;min-height:100vh;background:#f3f6fa}header,section{min-width:0;background:white;border-radius:16px;padding:22px;margin-bottom:16px;box-shadow:0 6px 24px #193b5610}header span{color:#2872d0;font-weight:600}h1{font-size:24px;margin:12px 0}h1,p{overflow-wrap:anywhere}p{color:#718096}h2{font-size:18px;margin:0 0 16px}input[type=file]{display:block;max-width:100%}section :deep(.el-button){margin-top:16px;width:100%}section :deep(.el-textarea){margin-top:10px}@media(max-width:360px){.field{padding:16px 12px}header,section{padding:16px}}</style>


