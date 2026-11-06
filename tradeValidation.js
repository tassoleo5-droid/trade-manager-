'use strict';
const ACTIONS = new Set(['POSITION_MODIFY', 'POSITION_CLOSE', 'POSITION_PARTIAL_CLOSE']);
const FIELDS = {
  POSITION_MODIFY: ['actionType','positionId','stopLoss','takeProfit'],
  POSITION_CLOSE: ['actionType','positionId'],
  POSITION_PARTIAL_CLOSE: ['actionType','positionId','volume']
};
function validateTradeRequest(req) {
  if (!req || typeof req !== 'object' || Array.isArray(req)) return {error:'Requête invalide'};
  const { method, path, body } = req;
  if (method === 'GET' && path === '/positions' && body == null) return {method:'GET',path:'/positions'};
  if (method !== 'POST' || path !== '/trade' || !body || typeof body !== 'object' || Array.isArray(body)) return {error:'Opération non autorisée'};
  const {actionType,positionId}=body;
  if (!ACTIONS.has(actionType)) return {error:'Action non autorisée'};
  if (!(typeof positionId==='number' && Number.isSafeInteger(positionId) && positionId>0) &&
      !(typeof positionId==='string' && /^[0-9]{1,24}$/.test(positionId))) return {error:'Identifiant de position invalide'};
  if (Object.keys(body).some(x=>!FIELDS[actionType].includes(x))) return {error:'Champ non autorisé'};
  const clean={actionType,positionId};
  if (actionType==='POSITION_MODIFY') {
    if (body.stopLoss===undefined && body.takeProfit===undefined) return {error:'SL ou TP requis'};
    for(const k of ['stopLoss','takeProfit']) if(body[k]!==undefined) {
      if(typeof body[k]!=='number'||!Number.isFinite(body[k])||body[k]<=0) return {error:k+' invalide'};
      clean[k]=body[k];
    }
  }
  if (actionType==='POSITION_PARTIAL_CLOSE') {
    if(typeof body.volume!=='number'||!Number.isFinite(body.volume)||body.volume<=0) return {error:'Volume invalide'};
    clean.volume=body.volume;
  }
  return {method:'POST',path:'/trade',body:clean};
}
module.exports={validateTradeRequest};
