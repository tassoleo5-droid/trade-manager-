'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {DEFAULT_RULES,validateRules:v}=require('../rulesValidation');

test('default rules are disabled and valid',()=> {
  assert.equal(DEFAULT_RULES.enabled,false);
  assert.deepEqual(v(DEFAULT_RULES).rules,DEFAULT_RULES);
});
test('validates persisted TP percentages',()=> {
  assert.equal(v({enabled:false,beThreshold:1.5,tpCount:2,tpPercents:[50,50]}).rules.tpCount,2);
});
test('rejects unordered take profit R targets',()=> {
  const base={...DEFAULT_RULES};
  for(const tpTargetsR of [[1,1,2],[0,1,3],[1,2,31],[1,2],[1,"2",3]])
    assert.ok(v({...base,tpTargetsR}).error);
});
test('allows explicit ordered R targets',()=> {
  assert.deepEqual(v({...DEFAULT_RULES,tpTargetsR:[0.5,1.5,3]}).rules.tpTargetsR,[0.5,1.5,3]);
});

test('rejects malformed rules and premature live activation',()=> {
  const base={...DEFAULT_RULES};
  for (const bad of [
    {...base, enabled:true},
    {...base, beThreshold:0},
    {...base, tpCount:4},
    {...base, tpPercents:[40,30,20]},
    {...base, tpPercents:[50,25,25],debug:true},
    {...base, tpPercents:['50',25,25]}
  ]) assert.ok(v(bad).error,JSON.stringify(bad));
});
