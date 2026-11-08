// Isolated component test: mount the real field SFC with a fake Vue renderer and controlled network replies.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const { createRequire } = require('node:module')
const frontendRequire = createRequire(process.cwd() + '/package.json')
const { parse, compileScript } = frontendRequire('@vue/compiler-sfc')
const esbuild = frontendRequire('esbuild')
const vue = frontendRequire('vue')

function deferred() { let resolve; const promise=new Promise(r=>{resolve=r});return {promise,resolve} }
const route=vue.reactive({params:{id:'1'}}), oldAsset=deferred(), oldReport=deferred(), retryReport=deferred(), retryTemplate=deferred()
let reportCount=0,template4Count=0
const calls=[]
function request(config) {
  calls.push(config)
  if(config.url==='/equipment/assets/1') return oldAsset.promise
  if(config.url==='/equipment/assets/2') return Promise.resolve({data:{id:2,name:'设备二',code:'B',location:'二区'}})
  if(config.url==='/equipment/assets/2/inspection-template') return Promise.resolve({data:{items:[]}})
  if(config.url==='/equipment/assets/3') return Promise.resolve({data:{id:3,name:'设备三',code:'C',location:'三区'}})
  if(config.url==='/equipment/assets/3/inspection-template') return Promise.resolve({data:{items:[]}})
  if(config.url==='/equipment/assets/4') return Promise.resolve({data:{id:4,name:'设备四',code:'D',location:'四区'}})
  if(config.url==='/equipment/assets/4/inspection-template') return ++template4Count===1?Promise.reject(new Error('template unavailable')):retryTemplate.promise
  if(config.url==='/equipment/orders') return ++reportCount===1?oldReport.promise:retryReport.promise
  throw new Error('unexpected request '+config.url)
}
const path='src/views/equipment/field/index.vue'
const {descriptor}=parse(fs.readFileSync(path,'utf8'),{filename:path})
const compiled=compileScript(descriptor,{id:'field-race',inlineTemplate:true})
const code=esbuild.transformSync(compiled.content,{format:'cjs',loader:'js'}).code
const fakeRequire=id=>{
  if(id==='vue')return vue
  if(id==='vue-router')return {useRoute:()=>route}
  if(id==='element-plus')return {ElMessage:{warning:()=>{},success:()=>{}}}
  if(id==='@/utils/request')return {__esModule:true,default:request}
  if(id.startsWith('@/views/'))return {__esModule:true,default:{render:()=>null}}
  return frontendRequire(id)
}
const moduleObj={exports:{}}
vm.runInNewContext('(function(require,module,exports){'+code+'\n})',{console})(fakeRequire,moduleObj,moduleObj.exports)
function node(type,text=''){return {type,text,children:[],props:{},parent:null}}
const renderer=vue.createRenderer({
  createElement:type=>node(type),createText:text=>node('#text',text),createComment:text=>node('#comment',text),
  setText:(n,t)=>{n.text=t},setElementText:(n,t)=>{n.text=t;n.children=[]},
  parentNode:n=>n.parent,nextSibling:n=>{const a=n.parent?.children||[];return a[a.indexOf(n)+1]||null},
  insert:(n,p,anchor)=>{if(n.parent){const a=n.parent.children;const i=a.indexOf(n);if(i>=0)a.splice(i,1)}n.parent=p;const i=anchor?p.children.indexOf(anchor):-1;i<0?p.children.push(n):p.children.splice(i,0,n)},
  remove:n=>{if(n.parent){const a=n.parent.children;const i=a.indexOf(n);if(i>=0)a.splice(i,1)}},
  patchProp:(n,key,prev,value)=>{n.props[key]=value}
})
const root=node('root'),app=renderer.createApp(moduleObj.exports.default)
app.directive('hasPermi',{});app.config.warnHandler=()=>{}
app.mount(root)
const settle=async()=>{for(let i=0;i<8;i++){await Promise.resolve();await vue.nextTick()}}
function all(n){return [n,...n.children.flatMap(all)]}
function text(n){return [n.text,...n.children.map(text)].join(' ')}

;(async()=>{
  route.params.id='2';await settle()
  assert.match(text(root),/设备二/)
  oldAsset.resolve({data:{id:1,name:'过期设备一',code:'A'}});await settle()
  assert.match(text(root),/设备二/);assert.doesNotMatch(text(root),/过期设备一/)
  const input=all(root).find(n=>n.type==='el-input' && n.props.placeholder==='请描述故障现象')
  assert.ok(input);input.props['onUpdate:modelValue']('旧设备故障');await settle()
  const submit=all(root).find(n=>n.type==='el-button' && text(n).includes('提交报修'))
  assert.ok(submit);submit.props.onClick();await settle()
  assert.equal(calls.find(x=>x.url==='/equipment/orders').data.equipmentId,2)
  route.params.id='3';await settle();assert.match(text(root),/设备三/)
  oldReport.resolve({data:{id:987654}});await settle()
  assert.match(text(root),/设备三/);assert.doesNotMatch(text(root),/987654/)
  assert.equal(all(root).find(n=>n.type==='el-input' && n.props.placeholder==='请描述故障现象').props.modelValue,'')
  route.params.id='4';await settle();assert.match(text(root),/设备或巡检配置加载失败/)
  all(root).find(n=>n.type==='el-input' && n.props.placeholder==='请描述故障现象').props['onUpdate:modelValue']('同设备报修');await settle()
  all(root).find(n=>n.type==='el-button' && text(n).includes('提交报修')).props.onClick();await settle()
  all(root).find(n=>n.type==='el-button' && text(n).includes('重新加载')).props.onClick();await settle()
  retryTemplate.resolve({data:{items:[]}});await settle()
  retryReport.resolve({data:{id:123456}});await settle()
  assert.match(text(root),/123456/,'same-device template retry must not discard a successful report')
  const count=calls.length; route.params.id=undefined; await settle()
  assert.equal(calls.length,count,'leaving the field route must not request an undefined equipment ID')
  app.unmount();console.log('field route reuse, route exit and same-device retry passed')
})().catch(error=>{console.error(error);process.exitCode=1})
