const assert = require('node:assert/strict');
const {registerDemoAccountsApi}=require('../demoAccountsApi');
async function call(matches, rules, body={login:'569657',server:'FusionMarkets-Demo'}) {
 const routes={};const app={post:(p,...h)=>routes[p]=h,get:()=>{},delete:()=>{}};
 const queries=[];const pool={query:async(sql,args)=>{queries.push([sql,args]);return sql.includes('demo_mt5_accounts')?{rowCount:matches,rows:matches?[{id:'account-1',user_id:7}]:[]}:{rows:rules?[{rules}]:[]}}};
 registerDemoAccountsApi(app,pool,()=>{});
 const handlers=routes['/api/demo/worker/rules'];const req={body,headers:{}};
 const res={code:200,set(){return this},status(n){this.code=n;return this},json(x){this.body=x;return this}};
 let invoked=false;handlers[0](req,res,()=>{invoked=true});assert.equal(invoked,false);assert.equal(res.code,401);
 res.code=200;await handlers.at(-1)(req,res);return {res,queries};
}
(async()=>{let a=await call(1);assert.equal(a.res.code,200);assert.equal(a.res.body.executionEnabled,false);assert.equal(a.res.body.rules.enabled,false);assert.deepEqual(a.queries[1][1],[7]);let b=await call(2);assert.equal(b.res.code,409);assert.equal(b.queries.length,1);let c=await call(0);assert.equal(c.res.code,409);let d=await call(1,null,{login:'bad',server:'x'});assert.equal(d.res.code,400);assert.equal(d.queries.length,0);let e=await call(1,{enabled:true});assert.equal(e.res.code,409);console.log('rules sync tests passed')})().catch(e=>{console.error(e);process.exitCode=1});
