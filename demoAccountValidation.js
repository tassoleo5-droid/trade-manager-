'use strict';
const ID_RE = /^[0-9]{1,20}$/;
const SERVER_RE = /^[a-zA-Z0-9][a-zA-Z0-9._ :/-]{0,127}$/;
const UUID_RE = /^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const WORKER_RE = /^[a-zA-Z0-9_-]{3,64}$/;

function validateDemoAccount(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body) ||
      Object.keys(body).some(k => !['login','server','password','label','confirmDemoOnly'].includes(k))) {
    return {error:'Données de connexion invalides'};
  }
  const {login,server,password,label = '',confirmDemoOnly} = body;
  if (confirmDemoOnly !== true) return {error:'Confirmez que ce compte est un compte DEMO'};
  if (typeof login !== 'string' || !ID_RE.test(login) || (BigInt(login) === 0n || BigInt(login) > 9223372036854775807n))
    return {error:'Numéro de compte MT5 invalide'};
  if (typeof server !== 'string' || !SERVER_RE.test(server))
    return {error:'Serveur MT5 invalide'};
  if (typeof password !== 'string' || password.length < 1 || password.length > 512 ||
      /[\u0000-\u001f]/.test(password))
    return {error:'Mot de passe MT5 invalide'};
  if (typeof label !== 'string' || label.length > 80 || /[\u0000-\u001f]/.test(label))
    return {error:'Nom du compte invalide'};
  return {account:{login:BigInt(login).toString(),server:server.trim(),password,label:label.trim()}};
}

function validUuid(value) {
  return typeof value === 'string' && UUID_RE.test(value);
}
function validWorkerId(value) {
  return typeof value === 'string' && WORKER_RE.test(value);
}
module.exports={validateDemoAccount,validUuid,validWorkerId};
