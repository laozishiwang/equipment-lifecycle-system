<script setup>
defineProps({ row: { type: Object, required: true } })
defineEmits(['action'])
</script>

<template>
  <div class="maintenance-actions">
    <el-button v-if="row.active" v-hasPermi="['equipment:maintenance:edit']" link type="primary" @click="$emit('action', 'edit', row)">编辑</el-button>
    <el-button v-if="row.active" v-hasPermi="['equipment:maintenance:edit']" link type="danger" @click="$emit('action', 'deactivate', row)">停用</el-button>
    <el-button link type="primary" @click="$emit('action', 'records', row)">保养记录</el-button>
    <el-button v-if="row.active" v-hasPermi="['equipment:maintenance:complete']" link type="primary" @click="$emit('action', 'complete', row)">登记保养</el-button>
  </div>
</template>

<style scoped>
.maintenance-actions{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center}
.maintenance-actions :deep(.el-button + .el-button){margin-left:0}
</style>
