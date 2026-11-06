# MyFlowFX — break-even à chaque tick (démo)

`MyFlowFXDemoBreakEven.mq5` est un Expert Advisor MT5 local conçu uniquement pour les comptes **démo**.

Il ne peut jamais :
- ouvrir une position ;
- fermer une position ou faire de clôture partielle ;
- modifier un take-profit.

Il peut uniquement déplacer le stop-loss d'une position existante au prix d'entrée lorsque le profit atteint le seuil configuré en R.

## Installation sur le VPS Windows

1. Dans MT5, ouvre **Fichier → Ouvrir le dossier des données**.
2. Ouvre le dossier `MQL5/Experts`.
3. Place le fichier `MyFlowFXDemoBreakEven.mq5` dans ce dossier.
4. Dans MT5, appuie sur **F4** pour ouvrir MetaEditor, ouvre ce fichier, puis appuie sur **F7** pour le compiler.
5. Retourne dans MT5, ouvre un graphique de la paire à surveiller, par exemple AUDUSD.
6. Dans le navigateur de MT5, sous **Experts**, glisse **MyFlowFXDemoBreakEven** sur le graphique.
7. Dans les paramètres de l'EA :
   - coche **EnableBreakEven** ;
   - règle **BreakEvenR** (par exemple `1.0` pour +1R) ;
   - autorise l'algo-trading seulement pour ce compte démo.

## Important

Un EA MT5 reçoit les ticks uniquement du graphique sur lequel il est installé. Pour gérer plusieurs paires Forex, attache le même EA à un graphique de chaque paire souhaitée.

Le worker Python/MyFlowFX reste utile pour le tableau de bord et la télémétrie. Cet EA local est celui qui permet au break-even de réagir dès le tick suivant, sans attendre la prochaine boucle de surveillance.
