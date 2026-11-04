'use strict';

const DEFAULT_RULES = Object.freeze({
  enabled: false,
  beThreshold: 1,
  tpCount: 3,
  tpPercents: [50,25,25]
});

function validateRules(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return {error:'Paramètres invalides'};
  if (Object.keys(input).some(k=>!['enabled','beThreshold','tpCount','tpPercents'].includes(k)))
    return {error:'Paramètre inconnu'};
  if (typeof input.enabled !== 'boolean') return {error:'enabled invalide'};
  // Safety: enabling an engine requires a separate verified worker and explicit activation protocol.
  if (input.enabled) return {error:"L'activation du moteur nécessite une connexion MT5 vérifiée"};
  if (typeof input.beThreshold !== 'number'||!Number.isFinite(input.beThreshold)||
      input.beThreshold < 0.1||input.beThreshold > 10) return {error:'Seuil BE invalide (0.1 à 10R)'};
  if (![1,2,3].includes(input.tpCount)) return {error:'Nombre de TP invalide'};
  if (!Array.isArray(input.tpPercents)||input.tpPercents.length!==input.tpCount ||
      input.tpPercents.some(x=>typeof x!=='number'||!Number.isInteger(x)||x<=0||x>100))
    return {error:'Pourcentages TP invalides'};
  if (input.tpPercents.reduce((a,b)=>a+b,0)!==100)
    return {error:'Les TP doivent totaliser 100%'};
  return {rules:{enabled:false,beThreshold:input.beThreshold,tpCount:input.tpCount,tpPercents:[...input.tpPercents]}};
}
module.exports={DEFAULT_RULES,validateRules};
