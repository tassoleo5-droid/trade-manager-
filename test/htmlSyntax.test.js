'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

test('all inline UI JavaScript parses',()=>{
  for(const page of ['accounts.html','index.html','landing.html']){
    const html=fs.readFileSync(path.join(__dirname,'../public',page),'utf8');
    const inline=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
    assert.ok(inline.length>0,page+' contains no inline script');
    for(const match of inline){
      assert.doesNotThrow(()=>new vm.Script(match[1],{filename:page}),page+' JS syntax error');
    }
  }
});
test('new MT5 onboarding page never hardcodes demo trading credentials',()=>{
  const html=fs.readFileSync(path.join(__dirname,'../public/accounts.html'),'utf8');
  assert.ok(html.includes('type="password"'));
  assert.ok(html.includes("'/api/demo/accounts'"));
  assert.ok(!html.includes('METAAPI_TOKEN'));
  assert.ok(!html.includes('MYFLOWFX_CREDENTIAL_KEY'));
});
