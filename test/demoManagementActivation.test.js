const assert = require('node:assert/strict');
const {registerDemoAccountsApi}=require('../demoAccountsApi');
async function execute(count, enabled, user=7) {
 const routes={};const app={post:(p,...h)=>routes[p]=h,get:()=>{},delete:()=>{}};
 let calls=[];const pool={query:async(sql,args)=>{calls.push({sql,args});return {rowCount:count,rows:count?[{management_enabled:enabled}]:[]}}};
 registerDemoAccountsApi(app,pool,()=>{});
 const req={params:{id:'123e4567-e89b-42d3-a456-426614174000'},body:{enabled},user:{id:user}};
 const res={code:200,set(){return this},status(n){this.code=n;return this},json(x){this.body=x;return this}};
 await routes['/api/demo/accounts/:id/management'].at(-1)(req,res);
 return {res,calls};
}
(async()=>{let a=await execute(1,true);assert.equal(a.res.body.managementEnabled,true);assert.deepEqual(a.calls[0].args,['123e4567-e89b-42d3-a456-426614174000',7,true]);assert.match(a.calls[0].sql,/user_id=\$2 AND status='verified_demo'/);let b=await execute(0,true);assert.equal(b.res.code,409);let c=await execute(1,'true');assert.equal(c.res.code,400);assert.equal(c.calls.length,0);console.log('demo activation ownership checks passed')})().catch(e=>{console.error(e);process.exitCode=1});
