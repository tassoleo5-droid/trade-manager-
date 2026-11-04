# MyFlowFX / TradeFlow — migration sans MetaApi

## Situation
Le site Node/Express et PostgreSQL restent hébergés sur Railway. Le navigateur ne doit plus gérer lui-même l'automatisation : le moteur actuel, déclenché par `setInterval(poll, 3000)`, s'arrête à la fermeture de l'onglet. Le passage à une nouvelle infrastructure doit être validé sur compte de démonstration avant tout compte réel.

## Expérience utilisateur
1. L'utilisateur se connecte à MyFlowFX.
2. Dans « Comptes », il saisit le numéro de compte **MT5**, le **serveur broker** et le mot de passe de trading.
3. Le backend chiffre ces identifiants et transmet une demande de connexion au service MT5 via un canal authentifié. Ne jamais les conserver en localStorage ni dans les logs.
4. Un terminal MT5 isolé (par compte/utilisateur ou par worker de confiance avec isolation stricte) se connecte, vérifie l'identité du compte et retourne un état « Connecté » ou une erreur utile.
5. Les règles TP/BE sont enregistrées côté serveur. Un moteur durable applique les règles même si le site est fermé.
6. L'utilisateur active ou suspend les règles depuis le site et voit le statut réel du moteur.

## Infrastructure
- **Railway** : Express, authentification, API, PostgreSQL, interface MyFlowFX.
- **Service d'exécution Windows** : terminaux MetaTrader 5 et Python MetaTrader5 (ou Expert Advisor MQL5 + canal sécurisé), sur un VPS contrôlé. Le SDK Python officiel s'appuie sur un terminal installé ; il ne suffit pas d'ouvrir un socket depuis Railway.
- **Canal sécurisé** : HTTPS/mTLS ou messages signés avec credentials courts, réseau privé/VPN, auth distincte par service et journal d'audit.
- **Secrets** : chiffrement authentifié avec clef externe aux tables de données, rotation, contrôle d'accès par utilisateur, révocation et suppression. Ne jamais demander de mot de passe broker sur GitHub ou en conversation.
- **Safety** : workers isolés, verrous par compte/position, idempotence par action, confirmation broker après exécution, précision volume/pas de lot, stop/freeze levels, retries bornés, coupe-circuit et surveillance avec alertes.

## Plan de migration
- **P0** Sécuriser routes, authentification, limites de requêtes, validation, logs et secrets.
- **P0** Créer tables accounts, execution_jobs, position_rules, execution_events, et états persistés. Ne pas stocker l'état d'une exécution uniquement dans la mémoire du navigateur.
- **P0** Tester une connexion sur compte DEMO, sans ordres live, puis activation explicite pour un compte autorisé.
- **P1** Implémenter l'adaptateur MT5 Windows (connect/disconnect/positions/modify/partial-close/close).
- **P1** Déplacer le moteur dans le worker, avec idempotence, reprises après interruption, et historique des confirmations réelles.
- **P1** Ajouter statuts détaillés au dashboard et contrôle d'arrêt côté serveur.
- **P2** Retirer les écrans MetaApi après vérification sur DEMO, puis migration progressive des utilisateurs.

## Précautions
- Le « mot de passe investisseur » MT5 est en lecture seule : la gestion des positions nécessite les permissions de trading adéquates.
- Vérifier les conditions du broker/prop firm concernant les automatisations, accès VPS, multi-sessions et EA.
- Ne jamais présenter une requête envoyée comme un ordre exécuté : vérifier la réponse et le nouvel état de position.
- Ne jamais présenter des chiffres marketing simulés comme des performances observées.
- Les changements de cette branche ne doivent pas être déployés tant que JWT_SECRET (au moins 32 caractères) et METAAPI_TOKEN de transition ne sont pas définis dans l'environnement.
