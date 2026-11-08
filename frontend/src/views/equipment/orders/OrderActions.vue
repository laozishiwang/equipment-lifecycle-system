<script setup>
import useUserStore from '@/store/modules/user'
defineProps({ row: { type: Object, required: true } })
defineEmits(['action'])
const user = useUserStore()
</script>
<template>
  <div class="order-actions"><el-button v-if="row.status === 'TESTING' &amp;&amp; String(row.technician_id) === String(user.id)" v-hasPermi="['equipment:order:trial']" link type="primary" @click="$emit('action', 'trial', row)">试运行</el-button><el-button v-if="['ACCEPTED','ARRIVED','TESTING'].includes(row.status)" v-hasPermi="['equipment:order:assign']" link type="primary" @click="$emit('action', 'assign', row)">转派</el-button><el-button v-if="row.status === 'REPORTED' && String(row.reporter_id) === String(user.id)" v-hasPermi="['equipment:order:report']" link type="warning" @click="$emit('action', 'withdraw', row)">撤回</el-button><el-button v-if="['REPORTED','ACCEPTED','ARRIVED','TESTING','COMPLETED'].includes(row.status)" v-hasPermi="['equipment:order:cancel']" link type="danger" @click="$emit('action', 'cancel', row)">取消</el-button><el-button link type="primary" @click="$emit('action', 'detail', row)">详情</el-button><el-button v-if="['COMPLETED','CLOSED','CANCELLED'].includes(row.status)" link type="primary" @click="$emit('action', 'costs', row)">费用</el-button><el-button v-if="row.status === 'REPORTED'" v-hasPermi="['equipment:order:accept']" link type="primary" @click="$emit('action', 'accept', row)">接单</el-button><el-button v-if="row.status === 'ACCEPTED' &amp;&amp; String(row.technician_id) === String(user.id)" v-hasPermi="['equipment:order:arrive']" link type="primary" @click="$emit('action', 'arrive', row)">到场</el-button><el-button v-if="row.status === 'ARRIVED' &amp;&amp; String(row.technician_id) === String(user.id)" v-hasPermi="['equipment:order:complete']" link type="primary" @click="$emit('action', 'complete', row)">提交维修</el-button><el-button v-if="row.status === 'COMPLETED'" v-hasPermi="['equipment:order:close']" link type="primary" @click="$emit('action', 'close', row)">确认关闭</el-button></div>
</template>
<style scoped>
.order-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; }
.order-actions :deep(.el-button + .el-button) { margin-left: 0; }
@media (max-width: 767px) { .order-actions :deep(.el-button) { min-height: 40px; } }
</style>
