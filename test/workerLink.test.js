const test = require('node:test');
const assert = require('node:assert/strict');
const { validateHeartbeat, verifyWorkerToken } = require('../workerLink');

test('accepts only the minimal demo read-only heartbeat', () => {
  assert.deepEqual(validateHeartbeat({ demo: true, positionsCount: 0 }), { demo: true, automation: false, positionsCount: 0 });
  assert.deepEqual(validateHeartbeat({ demo: true, automation: true, positionsCount: 1 }), { demo: true, automation: true, positionsCount: 1 });
  assert.equal(validateHeartbeat({ demo: false, positionsCount: 0 }), null);
  assert.equal(validateHeartbeat({ demo: true, positionsCount: -1 }), null);
  assert.equal(validateHeartbeat({ demo: true, positionsCount: 1, account: 'secret' }), null);
});

test('requires an exact worker token', () => {
  const token = 'a'.repeat(32);
  assert.equal(verifyWorkerToken(token, token), true);
  assert.equal(verifyWorkerToken(token.slice(1), token), false);
  assert.equal(verifyWorkerToken(undefined, token), false);
});
