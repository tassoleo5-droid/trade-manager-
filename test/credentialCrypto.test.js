'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { encryptCredential, decryptCredential } = require('../credentialCrypto');
const key = Buffer.alloc(32, 7).toString('base64');

test('credential is encrypted and decryptable for same user and account', () => {
  const secret = 'Demo_password_ABC!';
  const a = encryptCredential(secret, 42, 'accountA', key);
  const b = encryptCredential(secret, 42, 'accountA', key);
  assert.notEqual(a, b);
  assert.ok(!a.includes(secret));
  assert.equal(decryptCredential(a, 42, 'accountA', key), secret);
});

test('ciphertext cannot be swapped between accounts or users', () => {
  const encrypted = encryptCredential('secret', 42, 'accountA', key);
  assert.throws(() => decryptCredential(encrypted, 43, 'accountA', key));
  assert.throws(() => decryptCredential(encrypted, 42, 'accountB', key));
});

test('tampered ciphertext cannot decrypt', () => {
  const encrypted = encryptCredential('secret', 42, 'accountA', key);
  const pieces = encrypted.split('.');
  pieces[3] = Buffer.from('not the original plaintext').toString('base64url');
  assert.throws(() => decryptCredential(pieces.join('.'), 42, 'accountA', key));
});

test('invalid encryption configuration is rejected', () => {
  assert.throws(() => encryptCredential('secret', 42, 'accountA', 'bad'));
  assert.throws(() => encryptCredential('', 42, 'accountA', key));
  assert.throws(() => encryptCredential('secret', 42, '../../bad', key));
});
