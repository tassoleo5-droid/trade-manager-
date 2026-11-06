//+------------------------------------------------------------------+
//| MyFlowFXDemoBreakEven.mq5                                       |
//| Démo uniquement : déplace le stop-loss au prix d'entrée à +R.   |
//| N'ouvre ni ne ferme aucune position.                            |
//+------------------------------------------------------------------+
#property strict
#property version   "1.0"

#include <Trade/Trade.mqh>

input bool   EnableBreakEven = false;  // Activation explicite requise
input double BreakEvenR      = 1.0;    // Seuil de déclenchement en R

CTrade trade;

// Le conseiller reste verrouillé sur les comptes démo.
bool IsDemoAccount()
{
   return AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO;
}

bool IsInitialStop(const ENUM_POSITION_TYPE type,
                   const double entry,
                   const double stop,
                   const double point)
{
   const double tolerance = point * 0.5;

   if(type == POSITION_TYPE_BUY)
      return stop < entry - tolerance;

   if(type == POSITION_TYPE_SELL)
      return stop > entry + tolerance;

   return false;
}

bool IsAtBreakEven(const ENUM_POSITION_TYPE type,
                   const double entry,
                   const double stop,
                   const double point)
{
   const double tolerance = point * 0.5;

   if(type == POSITION_TYPE_BUY)
      return stop >= entry - tolerance;

   if(type == POSITION_TYPE_SELL)
      return stop <= entry + tolerance;

   return false;
}

bool IsBrokerDistanceValid(const ENUM_POSITION_TYPE type,
                           const string symbol,
                           const double entry,
                           const MqlTick &tick,
                           const double point)
{
   const long stopsLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   const double minimumDistance = (double)stopsLevel * point;

   if(type == POSITION_TYPE_BUY)
      return tick.bid - entry >= minimumDistance;

   if(type == POSITION_TYPE_SELL)
      return entry - tick.ask >= minimumDistance;

   return false;
}

void ManagePosition(const ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return;

   const string symbol = PositionGetString(POSITION_SYMBOL);
   if(symbol != _Symbol)
      return;

   const ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   if(type != POSITION_TYPE_BUY && type != POSITION_TYPE_SELL)
      return;

   const double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   const double stop  = PositionGetDouble(POSITION_SL);
   const double tp    = PositionGetDouble(POSITION_TP);
   const int digits   = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   const double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

   // Sans SL initial, le risque R n'est pas calculable. On ne modifie rien.
   if(point <= 0.0 || !IsInitialStop(type, entry, stop, point))
   {
      if(IsAtBreakEven(type, entry, stop, point))
         return;
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
      return;

   const double risk = MathAbs(entry - stop);
   const double progress = type == POSITION_TYPE_BUY
      ? (tick.bid - entry) / risk
      : (entry - tick.ask) / risk;

   if(progress < BreakEvenR)
      return;

   if(!IsBrokerDistanceValid(type, symbol, entry, tick, point))
   {
      PrintFormat("BREAK_EVEN_TICK: %I64u - seuil atteint, attente distance broker", ticket);
      return;
   }

   const double breakEven = NormalizeDouble(entry, digits);
   if(trade.PositionModify(ticket, breakEven, tp))
      PrintFormat("BREAK_EVEN_TICK: %I64u - SL placé au break-even %.5f", ticket, breakEven);
   else
      PrintFormat("BREAK_EVEN_TICK: %I64u - modification refusée (%u)",
                  ticket, trade.ResultRetcode());
}

int OnInit()
{
   Print("MyFlowFX break-even tick prêt. Démo uniquement; aucune ouverture/clôture.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(!EnableBreakEven)
      return;

   if(!IsDemoAccount())
   {
      static bool warningShown = false;
      if(!warningShown)
      {
         Print("MyFlowFX break-even arrêté : compte non-démo.");
         warningShown = true;
      }
      return;
   }

   // On ne traite que les positions du symbole du graphique courant.
   // Installer ce même EA sur chaque paire Forex à surveiller.
   for(int index = PositionsTotal() - 1; index >= 0; index--)
   {
      const ulong ticket = PositionGetTicket(index);
      if(ticket != 0)
         ManagePosition(ticket);
   }
}
