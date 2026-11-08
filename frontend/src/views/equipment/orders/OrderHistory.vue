<script setup>
import { useMediaQuery } from '@vueuse/core'
defineProps({ detail:{type:Object,required:true}, labels:{type:Object,required:true}, faultCategories:{type:Object,required:true} })
const mobile=useMediaQuery('(max-width: 767px)')
</script>

<template>
  <h4>维修记录</h4>
  <template v-if="mobile">
    <p v-if="!detail.repairs?.length" class="empty">暂无维修记录</p>
    <article v-for="(row,index) in detail.repairs" :key="index" class="history-card">
      <strong>{{ row.repair_date }} · 维修人 ID {{ row.technician_id }}</strong>
      <p>故障类别：{{ faultCategories[row.fault_category] || '—' }}</p>
      <p>故障代码：{{ row.fault_code ? `${row.fault_code} · ${row.fault_code_category} / ${row.fault_part} / ${row.fault_symptom}` : '—' }}</p>
      <p>诊断原因：{{ row.diagnosis || '—' }}</p><p>维修方法：{{ row.description || '—' }}</p>
    </article>
  </template>
  <el-table v-else :data="detail.repairs"><el-table-column prop="repair_date" label="维修日期"/><el-table-column prop="technician_id" label="维修人 ID"/><el-table-column label="故障类别"><template #default="{row}">{{ faultCategories[row.fault_category] || '—' }}</template></el-table-column><el-table-column label="故障代码"><template #default="{row}">{{ row.fault_code ? `${row.fault_code} · ${row.fault_code_category} / ${row.fault_part} / ${row.fault_symptom}` : '—' }}</template></el-table-column><el-table-column prop="diagnosis" label="诊断原因"/><el-table-column prop="description" label="维修方法"/></el-table>
  <h4>试运行记录</h4>
  <template v-if="mobile">
    <p v-if="!detail.trials?.length" class="empty">暂无试运行记录</p>
    <article v-for="(row,index) in detail.trials" :key="index" class="history-card"><strong>{{ row.result === 'PASS' ? '通过' : '未通过' }}</strong><p>{{ row.tested_at }}</p><p>说明：{{ row.notes || '—' }}</p></article>
  </template>
  <el-table v-else :data="detail.trials"><el-table-column prop="tested_at" label="时间"/><el-table-column label="结果"><template #default="{row}">{{ row.result === 'PASS' ? '通过' : '未通过' }}</template></el-table-column><el-table-column prop="notes" label="说明"/></el-table>
  <h4>转派记录</h4>
  <template v-if="mobile">
    <p v-if="!detail.assignments?.length" class="empty">暂无转派记录</p>
    <article v-for="(row,index) in detail.assignments" :key="index" class="history-card"><strong>{{ row.assigned_at }}</strong><p>维修人 ID：{{ row.from_user_id }} → {{ row.to_user_id }}</p><p>原因：{{ row.reason || '—' }}</p></article>
  </template>
  <el-table v-else :data="detail.assignments"><el-table-column prop="assigned_at" label="时间"/><el-table-column prop="from_user_id" label="原维修人 ID"/><el-table-column prop="to_user_id" label="新维修人 ID"/><el-table-column prop="reason" label="原因"/></el-table>
  <h4>处理记录</h4>
  <template v-if="mobile">
    <p v-if="!detail.transitions?.length" class="empty">暂无处理记录</p>
    <article v-for="(row,index) in detail.transitions" :key="index" class="history-card"><strong>{{ labels[row.from_status] || row.from_status }} → {{ labels[row.to_status] || row.to_status }}</strong><p>{{ row.operated_at }} · 操作人 ID {{ row.operator_id }}</p></article>
  </template>
  <el-table v-else :data="detail.transitions"><el-table-column prop="operated_at" label="时间"/><el-table-column label="状态变更"><template #default="{row}">{{ labels[row.from_status] || row.from_status }} → {{ labels[row.to_status] || row.to_status }}</template></el-table-column><el-table-column prop="operator_id" label="操作人 ID"/></el-table>
</template>

<style scoped>
h4{margin:20px 0 10px}.history-card{padding:12px;margin:8px 0;background:#f6f9fc;border:1px solid #e6edf5;border-radius:10px;overflow-wrap:anywhere}.history-card p{margin:6px 0 0;color:#52677a;white-space:pre-wrap}.empty{color:#8a98a6;font-size:14px}
</style>
