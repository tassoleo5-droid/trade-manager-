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

function validatePositions(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body) || !Array.isArray(body.positions)) return null;
  if (Object.keys(body).length !== 1 || body.positions.length > 50) return null;
  const positions = [];
  for (const position of body.positions) {
    if (!position || typeof position !== 'object' || Array.isArray(position)) return null;
    const keys = Object.keys(position).sort();
    if (keys.join(',') !== 'id,openPrice,side,stopLoss,symbol,volume') return null;
    if (typeof position.id !== 'string' || !/^[0-9]{1,20}$/.test(position.id)) return null;
    if (typeof position.symbol !== 'string' || !/^[A-Z0-9._-]{1,32}$/.test(position.symbol)) return null;
    if (position.side !== 'BUY' && position.side !== 'SELL') return null;
    if (!Number.isFinite(position.volume) || position.volume <= 0 || position.volume > 1000) return null;
    if (!Number.isFinite(position.openPrice) || position.openPrice <= 0) return null;
    if (!Number.isFinite(position.stopLoss) || position.stopLoss < 0) return null;
    positions.push({ id: position.id, symbol: position.symbol, side: position.side,
      volume: position.volume, openPrice: position.openPrice, stopLoss: position.stopLoss });
  }
  return positions;
}

module.exports = { validateHeartbeat, validatePositions, verifyWorkerToken };
