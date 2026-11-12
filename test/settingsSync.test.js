const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const elements={};let saved;
const source=fs.readFileSync(require('node:path').join(__dirname,'../public/index.html'),'utf8').match(/<script>([\\s\\S]*?)<\\/script>/)[1];
const rules={enabled:false,beThreshold:1.5,tpCount:2,tpPercents:[50,50],tpTargetsR:[1,3]};
const ctx={console,window:{addEventListener(){}},document:{body:{style:{}},getElementById(id){return elements[id] ||= {style:{},value:'',textContent:'',innerHTML:''}}},localStorage:{getItem(){return null},setItem(){},removeItem(){}},fetch:async(url,opt)=>{if(url==='/api/rules'&&opt.method==='PUT'){saved=JSON.parse(opt.body);return {ok:true,json:async()=>({rules:saved})}}return {ok:true,json:async()=>({rules})}},setTimeout(){}};
vm.createContext(ctx);vm.runInContext(source,ctx);
(async()=>{await vm.runInContext('loadServerRules()',ctx);assert.equal(vm.runInContext('settings.beThreshold',ctx),1.5);vm.runInContext('onTpTargetChange(1,4)',ctx);await vm.runInContext('saveAlgoSettings()',ctx);assert.equal(saved.tpTargetsR[1],4);assert.equal(saved.enabled,false);ctx.fetch=async()=>({ok:false});await assert.rejects(vm.runInContext('loadServerRules()',ctx));assert.equal(vm.runInContext('rulesLoaded',ctx),false);console.log('settings sync tests passed')})().catch(e=>{console.error(e);process.exitCode=1});
