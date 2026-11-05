const crypto = require('crypto');

function verifyWorkerToken(received, expected) {
  if (typeof received !== 'string' || typeof expected !== 'string') return false;
  const receivedBytes = Buffer.from(received, 'utf8');
  const expectedBytes = Buffer.from(expected, 'utf8');
  return receivedBytes.length === expectedBytes.length &&
    crypto.timingSafeEqual(receivedBytes, expectedBytes);
}

function validateHeartbeat(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null;
  const keys = Object.keys(body).sort();
  if (keys.length !== 2 || keys[0] !== 'demo' || keys[1] !== 'positionsCount') return null;
  if (body.demo !== true || !Number.isSafeInteger(body.positionsCount) || body.positionsCount < 0) return null;
  return { demo: true, positionsCount: body.positionsCount };
}

module.exports = { validateHeartbeat, verifyWorkerToken };
