'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {validateDemoAccount:v,validUuid,validWorkerId}=require('../demoAccountValidation');
const valid={login:'12345678',server:'Broker-Demo01',password:'not-a-real-password',label:'Test',confirmDemoOnly:true};
test('allows demo-only MT5 credentials',()=>{
  assert.equal(v(valid).account.login,'12345678');
  assert.equal(v(valid).account.password,valid.password);
});
test('rejects live/invalid broker credentials',()=>{
  for(const x of [
    {...valid,confirmDemoOnly:false}, {...valid,confirmDemoOnly:undefined},
    {...valid,login:'abc'}, {...valid,login:'0'}, {...valid,login:123456},
    {...valid,server:'https://bad.example'}, {...valid,server:'../..\\n'},
    {...valid,password:''}, {...valid,password:'x',extra:true}
  ]) assert.ok(v(x).error);
});
test('validates account ids and worker identity',()=>{
 assert.ok(validUuid('ecb045bb-83e7-4887-a22b-cbc54a1629e7'));
 assert.ok(!validUuid('../foo'));
 assert.ok(validWorkerId('worker-01'));
 assert.ok(!validWorkerId('a'));
});
