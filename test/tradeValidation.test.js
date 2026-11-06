'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {validateTradeRequest:v}=require('../tradeValidation');
test('allows positions read',()=>assert.deepEqual(v({method:'GET',path:'/positions'}),{method:'GET',path:'/positions'}));
test('allows strictly specified trade actions',()=>{
  assert.equal(v({method:'POST',path:'/trade',body:{actionType:'POSITION_CLOSE',positionId:'123'}}).body.actionType,'POSITION_CLOSE');
  assert.equal(v({method:'POST',path:'/trade',body:{actionType:'POSITION_MODIFY',positionId:123,stopLoss:1.234}}).body.stopLoss,1.234);
  assert.equal(v({method:'POST',path:'/trade',body:{actionType:'POSITION_PARTIAL_CLOSE',positionId:'123',volume:0.1}}).body.volume,0.1);
});
test('rejects forbidden and malformed operations',()=>{
  const cases=[
    {method:'DELETE',path:'/positions'},
    {method:'GET',path:'/account-information'},
    {method:'POST',path:'/trade',body:{actionType:'ORDER_TYPE_BUY',positionId:'123'}},
    {method:'POST',path:'/trade',body:{actionType:'POSITION_CLOSE',positionId:'123',extra:1}},
    {method:'POST',path:'/trade',body:{actionType:'POSITION_MODIFY',positionId:'123',stopLoss:'1.5'}},
    {method:'POST',path:'/trade',body:{actionType:'POSITION_PARTIAL_CLOSE',positionId:'123',volume:-1}},
    {method:'POST',path:'/trade',body:{actionType:'POSITION_CLOSE',positionId:'../etc'}},
  ];
  for(const c of cases) assert.ok(v(c).error,JSON.stringify(c));
});
