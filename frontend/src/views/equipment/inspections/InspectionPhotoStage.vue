<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
const props=defineProps({ equipmentId: { type: [Number, String], required: true } })
const ids=defineModel({ type: Array, required: true })
const busy=defineModel('busy', { type: Boolean, required: true })
const input=ref(null), selected=ref(null)
watch(()=>props.equipmentId,()=>{selected.value=null;if(input.value)input.value.value=''})
async function upload() {
  if(busy.value) return
  if(!selected.value) return ElMessage.warning('请选择照片')
  if(selected.value.size>5*1024*1024) return ElMessage.warning('照片不能超过 5 MB')
  if(ids.value.length>=6) return ElMessage.warning('最多上传 6 张照片')
  const equipment=String(props.equipmentId)
  const form=new FormData();form.append('equipmentId',equipment);form.append('file',selected.value)
  busy.value=true
  try {
    const response=await request({url:'/equipment/inspections/staged-photos',method:'post',data:form,headers:{'Content-Type':undefined,isRepeatSubmit:false}})
    if(String(props.equipmentId)!==equipment) return ElMessage.warning('设备已变化，请重新上传照片')
    ids.value=[...ids.value,response.data.id];selected.value=null;if(input.value)input.value.value=''
    ElMessage.success('照片已上传，请继续提交巡检')
  } finally {busy.value=false}
}
async function remove(id) {
  if(busy.value) return
  busy.value=true
  try {
    await request({url:'/equipment/inspections/staged-photos/'+id,method:'delete'})
    ids.value=ids.value.filter(value=>value!==id)
    ElMessage.success('照片已移除')
  } finally { busy.value=false }
}
</script>
<template>
  <div class="staged-photos">
    <p>异常时至少上传一张照片，最多 6 张、每张不超过 5 MB。上传后请在 2 小时内提交巡检。</p>
    <input ref="input" type="file" accept="image/jpeg,image/png" @change="selected=$event.target.files?.[0] || null" />
    <el-button :loading="busy" :disabled="ids.length >= 6" @click="upload">上传待提交照片</el-button>
    <p v-if="ids.length">已上传 {{ ids.length }} 张</p>
    <div v-for="(id,index) in ids" :key="id"><span>照片 {{ index+1 }}</span><el-button link type="danger" :disabled="busy" @click="remove(id)">移除</el-button></div>
  </div>
</template>
<style scoped>.staged-photos{width:100%;padding:12px;border:1px solid #f2d4a3;border-radius:10px;background:#fffaf1}.staged-photos p{font-size:13px;color:#785c30;margin:0 0 8px}.staged-photos input{max-width:100%;margin-bottom:8px}.staged-photos span{font-size:13px;margin-right:8px}</style>
