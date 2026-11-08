<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const props=defineProps({ row: { type: Object, required: true } })
const emit=defineEmits(['saved'])
const visible=ref(false), loading=ref(false), saving=ref(false), departments=ref([]), history=ref([]), selected=ref(null)

async function open() {
  if (loading.value) return
  loading.value=true
  try {
    const [choices, detail]=await Promise.all([
      request({url:'/equipment/assets/departments',method:'get'}),
      request({url:`/equipment/assets/${props.row.id}/department`,method:'get'})
    ])
    const current=detail.data.current[0]
    departments.value=choices.data || []
    if (current && !departments.value.some(item=>item.dept_id===current.dept_id)) departments.value=[...departments.value,{...current,unavailable:true}]
    selected.value=current?.dept_id ?? null
    history.value=detail.data.history || []
    visible.value=true
  } finally { loading.value=false }
}
async function save() {
  if (saving.value) return
  saving.value=true
  try {
    const deptId=selected.value || null
    await request({url:`/equipment/assets/${props.row.id}/department`,method:'put',data:{deptId,clear:deptId===null}})
    ElMessage.success('部门归属已保存')
    visible.value=false
    emit('saved')
  } finally { saving.value=false }
}
</script>

<template>
  <span>
    <el-button link type="primary" :loading="loading" @click="open">设置</el-button>
    <el-dialog v-model="visible" append-to-body title="设备部门归属" width="min(95%, 620px)">
      <p class="hint">{{ row.code }} · {{ row.name }}</p>
      <p class="hint">部门归属用于记录设备管理单位；目前不会限制设备和工单的访问范围。</p>
      <el-form label-position="top"><el-form-item label="归属部门"><el-select v-model="selected" clearable filterable placeholder="未设置"><el-option v-for="item in departments" :key="item.dept_id" :label="`${item.dept_name}（${item.dept_id}）${item.unavailable ? '（已停用）' : ''}`" :value="item.dept_id" :disabled="item.unavailable"/></el-select></el-form-item></el-form>
      <h4>归属变更记录（最近 200 条）</h4>
      <el-table :data="history"><el-table-column label="原部门" min-width="100"><template #default="{row}">{{ row.old_dept_name || '未设置' }}</template></el-table-column><el-table-column label="新部门" min-width="100"><template #default="{row}">{{ row.new_dept_name || '未设置' }}</template></el-table-column><el-table-column prop="changed_at" label="变更时间" min-width="160"/><el-table-column prop="changed_by" label="操作人 ID" min-width="100"/></el-table>
      <template #footer><el-button @click="visible=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </span>
</template>

<style scoped>
.hint { color:#718096; margin:0 0 12px; overflow-wrap:anywhere; }
</style>
