'use strict';
// Cryptography utility only. Not wired to any public endpoint until the
// Windows connector, authentication, and account lifecycle are production-ready.
const crypto = require('node:crypto');

function getKey(encoded) {
  if (typeof encoded !== 'string' || !/^[A-Za-z0-9+/]{43}=$/.test(encoded)) {
    throw new Error('MYFLOWFX_CREDENTIAL_KEY must be a 32-byte base64 key');
  }
  const key = Buffer.from(encoded, 'base64');
  if (key.length !== 32 || key.toString('base64') !== encoded) {
    throw new Error('Invalid credential encryption key');
  }
  return key;
}

function context(userId, accountId) {
  if (!Number.isSafeInteger(userId) || userId < 1 ||
      typeof accountId !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(accountId)) {
    throw new Error('Invalid credential encryption context');
  }
  return Buffer.from(JSON.stringify(['MyFlowFX', 'MT5', 1, userId, accountId]));
}

function encryptCredential(plaintext, userId, accountId, encodedKey = process.env.MYFLOWFX_CREDENTIAL_KEY) {
  if (typeof plaintext !== 'string' || !plaintext || plaintext.length > 4096) {
    throw new Error('Invalid credential');
  }
  const key = getKey(encodedKey);
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(context(userId, accountId));
  const data = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return ['v1', iv.toString('base64url'), tag.toString('base64url'), data.toString('base64url')].join('.');
}

function decryptCredential(ciphertext, userId, accountId, encodedKey = process.env.MYFLOWFX_CREDENTIAL_KEY) {
  if (typeof ciphertext !== 'string' || ciphertext.length > 8192) throw new Error('Invalid ciphertext');
  const parts = ciphertext.split('.');
  if (parts.length !== 4 || parts[0] !== 'v1') throw new Error('Unknown ciphertext version');
  const [ , ivB64, tagB64, dataB64 ] = parts;
  const iv = Buffer.from(ivB64, 'base64url');
  const tag = Buffer.from(tagB64, 'base64url');
  if (iv.length !== 12 || tag.length !== 16) throw new Error('Invalid ciphertext');
  const decipher = crypto.createDecipheriv('aes-256-gcm', getKey(encodedKey), iv);
  decipher.setAAD(context(userId, accountId));
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(Buffer.from(dataB64, 'base64url')), decipher.final()]).toString('utf8');
}

module.exports = { encryptCredential, decryptCredential };
