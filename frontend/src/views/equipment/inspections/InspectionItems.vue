<script setup>
const items = defineModel({ type: Array, required: true })
function add() { if (items.value.length < 20) items.value = [...items.value, { name: '', result: '', remark: '' }] }
function update(index, key, value) { items.value = items.value.map((item, i) => i === index ? { ...item, [key]: value } : item) }
function remove(index) { items.value = items.value.filter((_, i) => i !== index) }
function setReading(index, value) {
  const item=items.value[index]
  let result=''
  if (/^-?\d{1,9}(\.\d{1,4})?$/.test(value)) {
    const reading=Math.round(Number(value)*10000)
    const low=item.lowerBound == null ? null : Math.round(Number(item.lowerBound)*10000)
    const high=item.upperBound == null ? null : Math.round(Number(item.upperBound)*10000)
    result=((low!==null && reading<low) || (high!==null && reading>high)) ? 'ABNORMAL' : 'NORMAL'
  }
  items.value=items.value.map((row,i)=>i===index ? {...row,measuredValue:value,result} : row)
}
</script>
<template>
  <div class="inspection-items">
    <p>模板项目不可修改或删除；可补充检查项目，总计最多 20 项。</p>
    <div v-for="(item, index) in items" :key="index" class="inspection-item">
      <el-input :model-value="item.name" :disabled="item.templateItem === true" maxlength="120" placeholder="检查项目名称" :aria-label="`第 ${index + 1} 项名称`" @update:model-value="update(index, 'name', $event)" />
      <p v-if="item.standard">检查标准：{{ item.standard }}</p>
      <template v-if="item.lowerBound != null || item.upperBound != null"><p>允许范围：{{ item.lowerBound ?? '不限' }} ～ {{ item.upperBound ?? '不限' }} {{ item.unit || '' }}</p><el-input :model-value="item.measuredValue" inputmode="decimal" placeholder="填写检查数值" :aria-label="`第 ${index + 1} 项读数`" @update:model-value="setReading(index, $event)"/><p>数值结果：{{ item.result === 'NORMAL' ? '正常' : item.result === 'ABNORMAL' ? '异常' : '请填写有效读数' }}</p></template>
      <el-radio-group v-else :model-value="item.result" :aria-label="`第 ${index + 1} 项结果`" @update:model-value="update(index, 'result', $event)"><el-radio value="NORMAL">正常</el-radio><el-radio value="ABNORMAL">异常</el-radio></el-radio-group>
      <el-input :model-value="item.remark" maxlength="500" placeholder="项目说明（选填）" :aria-label="`第 ${index + 1} 项说明`" @update:model-value="update(index, 'remark', $event)" />
      <el-button v-if="!item.templateItem" link type="danger" @click="remove(index)">删除项目</el-button>
    </div>
    <el-button :disabled="items.length >= 20" @click="add">添加检查项目</el-button>
  </div>
</template>
<style scoped>
.inspection-items{width:100%;min-width:0}.inspection-items p{color:#6b7b8c;font-size:13px;margin:0 0 8px;overflow-wrap:anywhere}.inspection-item{min-width:0;padding:12px;margin-bottom:10px;background:#f6f9fc;border:1px solid #e5edf5;border-radius:10px;display:grid;grid-template-columns:minmax(0,1fr);gap:8px}.inspection-item :deep(.el-radio-group){width:100%}
</style>
