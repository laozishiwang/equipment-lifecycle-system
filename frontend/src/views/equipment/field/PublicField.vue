<script setup>
import { ref, reactive, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import InspectionItems from '@/views/equipment/inspections/InspectionItems.vue'
import { closeFieldPage } from './closeFieldPage'
const route=useRoute(), device=ref(null), person=ref(''), description=ref(''), result=ref('NORMAL'), remark=ref(''), busy=ref(false), error=ref(false)
const step=ref('choose')
function choose(kind){if(!person.value.trim()) return ElMessage.warning('请填写姓名');step.value=kind;window.scrollTo(0,0)}
const items=ref([]), templateId=ref(null), createOrder=ref(false), photoRequired=ref(false), photoTokens=ref([]), reportPhotoTokens=ref([]), photoBusy=ref(false)
const pendingUpload={reports:null,inspections:null}
const photoError=ref({reports:false,inspections:false})
const previews=ref({reports:[],inspections:[]})
function clearPreviews(kind){for(const photo of previews.value[kind]) URL.revokeObjectURL(photo.url);previews.value[kind]=[]}
function removePhoto(kind,index){const photo=previews.value[kind][index]; URL.revokeObjectURL(photo.url); previews.value[kind].splice(index,1); if(photo.token){const tokens=kind==='reports'?reportPhotoTokens:photoTokens;tokens.value=tokens.value.filter(token=>token!==photo.token)} if(!previews.value[kind].some(item=>item.status==='failed')) {photoError.value[kind]=false;pendingUpload[kind]=null}}
onBeforeUnmount(()=>{clearPreviews('reports');clearPreviews('inspections')})
function uploadPhoto(event,kind){
 const file=event.target.files?.[0];if(!file)return
 if(file.size>5*1024*1024){photoError.value[kind]=true;event.target.value='';return ElMessage.warning('照片不能超过 5 MB，请选择较小的照片')}
 photoBusy.value=true;photoError.value[kind]=false
 const photo=reactive({url:URL.createObjectURL(file),status:'uploading',token:null});previews.value[kind].push(photo)
 const data=new FormData();data.append('file',file)
 pendingUpload[kind]=request({url:`${base()}/photos`,method:'post',data,timeout:90000,headers:{'Content-Type':undefined,isRepeatSubmit:false}})
  .then(response=>{photo.token=response.data.token;photo.status='done';(kind==='reports'?reportPhotoTokens:photoTokens).value.push(photo.token);return true})
  .catch(()=>{photo.status='failed';photoError.value[kind]=true;return false})
  .finally(()=>{photoBusy.value=false;event.target.value=''})
}

const base=()=>`/public/field/${route.params.id}`
let loadVersion=0
async function load(){
 const version=++loadVersion
 clearPreviews('reports');clearPreviews('inspections');step.value='choose'; pendingUpload.reports=null;pendingUpload.inspections=null;photoError.value={reports:false,inspections:false}; device.value=null; error.value=false; person.value='';description.value='';remark.value='';items.value=[];photoTokens.value=[];reportPhotoTokens.value=[];createOrder.value=false
 if(!/^\d+$/.test(String(route.params.id || ''))) return
 try{
  const loaded=(await request({url:base(),method:'get'})).data
  if(version!==loadVersion)return
  device.value=loaded
  const template=(loaded.templates || [])[0]
  templateId.value=template?.id || null;photoRequired.value=Number(template?.photo_required)===1
  items.value=(template?.items || []).map(item=>({name:item.item_name,standard:item.standard_text || '',lowerBound:item.lower_bound,upperBound:item.upper_bound,unit:item.unit || '',measuredValue:'',result:'',remark:'',templateItem:true}))
 }catch{if(version===loadVersion)error.value=true}
}
async function submit(kind){
 if(busy.value)return
 if(!person.value.trim()) return ElMessage.warning('请填写姓名')
 if(kind==='reports'&&!description.value.trim()) return ElMessage.warning('请描述故障')
 busy.value=true
 try {
 if(pendingUpload[kind] && !(await pendingUpload[kind])) return ElMessage.warning('照片上传失败，请重新选择照片')
 if(photoError.value[kind]) return ElMessage.warning('照片上传失败，请重新选择照片')
 if(kind==='inspections' && result.value==='NORMAL' && items.value.some(item=>item.result==='ABNORMAL')) return ElMessage.warning('存在异常项目时，请选择巡检异常')
 if(kind==='inspections' && createOrder.value && !remark.value.trim()) return ElMessage.warning('请填写异常说明')
 if(kind==='inspections' && result.value==='ABNORMAL' && photoRequired.value && !photoTokens.value.length) return ElMessage.warning('异常巡检请先上传照片')
 if(kind==='inspections' && items.value.some(item=>!item.name.trim() || !['NORMAL','ABNORMAL'].includes(item.result))) return ElMessage.warning('请完成巡检项目')
 let response
 try { response=await request({url:`${base()}/${kind}`,method:'post',data:kind==='reports'?{name:person.value.trim(),description:description.value.trim(),photoTokens:reportPhotoTokens.value}:{name:person.value.trim(),result:result.value,remark:remark.value.trim(),createOrder:result.value==='ABNORMAL' && createOrder.value,templateId:templateId.value,photoTokens:result.value==='ABNORMAL'?photoTokens.value:[],items:items.value.map(({name,result,remark,measuredValue})=>({name,result,remark,measuredValue:measuredValue || null}))}}) } catch { return ElMessageBox.alert('暂时无法确认提交结果，请联系管理员核实后再试，避免重复提交。','提交结果未确认',{confirmButtonText:'知道了'}) }
 person.value='';description.value='';remark.value='';photoTokens.value=[];reportPhotoTokens.value=[];clearPreviews('reports');clearPreviews('inspections');createOrder.value=false;pendingUpload[kind]=null;step.value='choose';const id=kind==='reports' ? response.data?.orderId : response.data?.inspectionId;await ElMessageBox.alert(`${kind==='reports'?'报修':'巡检'}已提交成功${id ? `（编号 ${id}）` : ''}。点击关闭页面；若未关闭，请点击右上角关闭或返回微信。`,'提交完成',{confirmButtonText:'关闭页面',showClose:false,closeOnClickModal:false,closeOnPressEscape:false});closeFieldPage();ElMessage.info('如页面未关闭，请点击右上角关闭或返回微信')}finally{busy.value=false}
}
watch(()=>route.params.id,load,{immediate:true})
</script>
<template><main class="field"><header><span>设备现场</span><h1>{{ device?.name || (error ? '设备加载失败' : '正在加载设备') }}</h1><p>{{ device?.code }}　{{ device?.location }}</p></header><section v-if="device && step==='choose'"><h2>您的姓名</h2><el-input v-model="person" maxlength="50" placeholder="请填写姓名，每次提交均需填写"/><p>请选择需要办理的事项</p><div class="choices"><el-button type="primary" @click="choose('reports')">我要报修</el-button><el-button @click="choose('inspections')">我要巡检</el-button></div></section><section v-if="device && step==='reports'"><el-button text :disabled="busy" @click="step='choose'">← 返回选择</el-button><h2>扫码报修</h2><p>提交人：{{ person }}</p><el-input v-model="description" type="textarea" :rows="3" maxlength="2000" placeholder="请描述故障现象"/><p>现场照片（{{ reportPhotoTokens.length }} 张）</p><input type="file" accept="image/jpeg,image/png" :disabled="photoBusy || busy" @change="uploadPhoto($event,'reports')"/><div class="photo-previews"><div v-for="(photo,index) in previews.reports" :key="photo.url" class="photo-card"><img :src="photo.url" alt="已选择的现场照片"/><span>{{ photo.status==='uploading' ? '上传中' : photo.status==='done' ? '已上传' : '上传失败，请删除后重选' }}</span><el-button text :disabled="photoBusy || busy" @click="removePhoto('reports',index)">删除</el-button></div></div><p v-if="photoBusy">照片上传中，请稍候，可直接点击提交报修。</p><el-button type="primary" :loading="busy" @click="submit('reports')">提交报修</el-button></section><section v-if="device && step==='inspections'"><el-button text :disabled="busy" @click="step='choose'">← 返回选择</el-button><h2>扫码巡检</h2><p>提交人：{{ person }}</p><el-radio-group v-model="result"><el-radio value="NORMAL">正常</el-radio><el-radio value="ABNORMAL">异常</el-radio></el-radio-group><el-input v-model="remark" type="textarea" :rows="3" maxlength="1000" placeholder="巡检说明（选填）"/><InspectionItems v-model="items"/><el-checkbox v-if="result==='ABNORMAL'" v-model="createOrder">同时生成报修单</el-checkbox><div v-if="result==='ABNORMAL'"><p>{{ photoRequired ? '异常巡检需上传照片' : '可上传巡检照片' }}（{{ photoTokens.length }} 张）</p><input type="file" accept="image/jpeg,image/png" :disabled="photoBusy || busy" @change="uploadPhoto($event,'inspections')"/><div class="photo-previews"><div v-for="(photo,index) in previews.inspections" :key="photo.url" class="photo-card"><img :src="photo.url" alt="已选择的现场照片"/><span>{{ photo.status==='uploading' ? '上传中' : photo.status==='done' ? '已上传' : '上传失败，请删除后重选' }}</span><el-button text :disabled="photoBusy || busy" @click="removePhoto('inspections',index)">删除</el-button></div></div><p v-if="photoBusy">照片上传中，请稍候，可直接点击提交巡检。</p></div><el-button type="primary" plain :loading="busy" @click="submit('inspections')">提交巡检</el-button></section><section v-if="error"><p>设备加载失败，请检查网络或二维码。</p><el-button @click="load">重新加载</el-button></section></main></template>
<style scoped>.field{box-sizing:border-box;max-width:600px;min-height:100vh;margin:auto;padding:20px 16px;background:#f3f6fa}header,section{background:#fff;border-radius:16px;padding:20px;margin-bottom:14px}h1{font-size:24px}h2{font-size:18px;margin:0 0 14px}p{color:#718096}section :deep(.el-button){width:100%;margin-top:16px}section :deep(.el-textarea){margin-top:10px}.choices{display:grid;gap:12px;margin-top:20px}.choices :deep(.el-button){margin:0;height:52px;font-size:17px}.field h2{margin-top:12px}.photo-previews{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}.photo-card{width:120px;display:flex;flex-direction:column;gap:5px;font-size:13px}.photo-card img{width:120px;height:100px;object-fit:cover;border-radius:8px}.photo-card :deep(.el-button){margin:0;width:auto;align-self:flex-start}</style>
