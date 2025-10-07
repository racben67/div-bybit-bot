import time
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks
import math
import os
from datetime import datetime, timedelta
from collections import deque

# --- Importation des clés et connexion à l'API ---
from keys import API_KEY, API_SECRET
from pybit.unified_trading import HTTP

# --- ========================================================== ---
# ---               PARAMÈTRES DU BOT DE TRADING                 ---
# --- ========================================================== ---
session = HTTP(
    demo=True,  # IMPORTANT: True pour le compte démo
    api_key=API_KEY,
    api_secret=API_SECRET,
)

TICKER = 'ETHUSDT'
INTERVAL = 1  # Timeframe 1 minute
CAPITAL_PER_TRADE = 100  # Capital alloué pour chaque trade ($)
RR_RATIO = 3.0  # Ratio Risque/Récompense (1/3)

# Paramètres de l'indicateur
PPO_FAST = 12
PPO_SLOW = 26
PPO_SMOOTH = 2
PEAK_DISTANCE = 5
# --- ========================================================== ---

def format_uptime(seconds):
    """Convertit les secondes en un format lisible (Jours, Heures, Min, Sec)."""
    if seconds is None: return "N/A"
    delta = timedelta(seconds=seconds)
    d = delta.days
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{d}j {h}h {m}m {s}s"

def get_symbol_info(ticker):
    """Récupère les informations du symbole pour connaître la précision des ordres."""
    try:
        info = session.get_instruments_info(category="linear", symbol=ticker)
        return info['result']['list'][0]
    except Exception as e:
        print(f"Erreur lors de la récupération des infos du symbole: {e}")
        return None

def get_bybit_data(ticker, interval, limit=200):
    """Récupère les dernières bougies."""
    try:
        klines = session.get_kline(
            category="linear", symbol=ticker, interval=interval, limit=limit
        )['result']['list']
        df = pd.DataFrame(klines, columns=['start', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['start'] = pd.to_datetime(df['start'].astype(float), unit='ms')
        df.set_index('start', inplace=True)
        df = df.astype(float).sort_index()
        return df
    except Exception as e:
        return None

def check_for_divergence_signal(df):
    """Analyse la dernière bougie clôturée pour un signal de divergence."""
    df.ta.ppo(fast=PPO_FAST, slow=PPO_SLOW, signal=9, append=True)
    df['PPO_smooth'] = ta.sma(df[f'PPO_{PPO_FAST}_{PPO_SLOW}_9'], length=PPO_SMOOTH)
    df.dropna(inplace=True)
    if len(df) < PEAK_DISTANCE * 2: return None, None
    
    last_ppo_value = df['PPO_smooth'].iloc[-1]
    
    price_peaks_idx, _ = find_peaks(df['high'], distance=PEAK_DISTANCE)
    price_troughs_idx, _ = find_peaks(-df['low'], distance=PEAK_DISTANCE)
    osc_peaks_idx, _ = find_peaks(df['PPO_smooth'], distance=PEAK_DISTANCE)
    osc_troughs_idx, _ = find_peaks(-df['PPO_smooth'], distance=PEAK_DISTANCE)

    last_candle_index = len(df) - 2

    # Divergence Baissière
    if len(osc_peaks_idx) > 1 and osc_peaks_idx[-1] == last_candle_index:
        if df['PPO_smooth'].iloc[osc_peaks_idx[-1]] < df['PPO_smooth'].iloc[osc_peaks_idx[-2]]:
            if df['high'].iloc[osc_peaks_idx[-1]] > df['high'].iloc[osc_peaks_idx[-2]]:
                return {"type": "Sell", "price": df['high'].iloc[last_candle_index]}, last_ppo_value

    # Divergence Haussière
    if len(osc_troughs_idx) > 1 and osc_troughs_idx[-1] == last_candle_index:
        if df['PPO_smooth'].iloc[osc_troughs_idx[-1]] > df['PPO_smooth'].iloc[osc_troughs_idx[-2]]:
            if df['low'].iloc[last_candle_index] < df['low'].iloc[osc_troughs_idx[-2]]:
                return {"type": "Buy", "price": df['low'].iloc[last_candle_index]}, last_ppo_value
                
    return None, last_ppo_value

def run_bot():
    """Boucle principale du bot de trading."""
    start_time = time.time()
    symbol_info = get_symbol_info(TICKER)
    if not symbol_info: return
    
    qty_step = float(symbol_info['lotSizeFilter']['qtyStep'])
    last_checked_timestamp = None
    trade_history = deque(maxlen=10)
    last_known_position_size = 0.0
    log_messages = deque(maxlen=5)

    while True:
        try:
            # --- NETTOYAGE ET AFFICHAGE DU TABLEAU DE BORD ---
            os.system('cls' if os.name == 'nt' else 'clear')
            print("="*60)
            print(f"🤖 BOT DE TRADING PPO DIVERGENCE | {TICKER} | {INTERVAL}M")
            print("="*60)
            
            uptime = format_uptime(time.time() - start_time)
            print(f"🕒 Uptime: {uptime}")

            position_info = session.get_positions(category="linear", symbol=TICKER)['result']['list'][0]
            current_position_size = float(position_info['size'])
            
            # --- DÉTECTION DE CLÔTURE DE TRADE ---
            if last_known_position_size > 0 and current_position_size == 0:
                pnl_info = session.get_closed_pnl(category="linear", symbol=TICKER, limit=1)['result']['list'][0]
                trade_pnl = float(pnl_info['closedPnl'])
                trade_side = pnl_info['side']
                exit_price = float(pnl_info['avgExitPrice'])
                timestamp = datetime.fromtimestamp(int(pnl_info['updatedTime']) / 1000).strftime('%H:%M:%S')
                result_emoji = "✅" if trade_pnl > 0 else "❌"
                trade_history.append(f"{result_emoji} {timestamp} | {trade_side:<4} | PNL: {trade_pnl:6.2f}$ @ {exit_price:.2f}")
                log_messages.append(f"-> Trade {trade_side} clôturé. PNL: {trade_pnl:.2f}$")

            last_known_position_size = current_position_size
            in_position = current_position_size > 0
            
            # --- AFFICHAGE STATUT ACTUEL ---
            if in_position:
                print(f"📊 Statut: En Position {position_info['side']}")
                print(f"   - Taille: {position_info['size']} {TICKER}")
                print(f"   - Prix d'entrée: {float(position_info['avgPrice']):.2f}$")
                print(f"   - PNL non réalisé: {float(position_info['unrealisedPnl']):.2f}$")
            else:
                print("📊 Statut: En attente d'un signal...")

            # --- AFFICHAGE HISTORIQUE DES TRADES ---
            print("\n--- 🔟 Derniers Trades ---")
            if not trade_history:
                print("Aucun trade enregistré.")
            else:
                for trade in reversed(trade_history):
                    print(trade)

            # --- AFFICHAGE DES LOGS ---
            print("\n--- 📝 Logs d'activité ---")
            for msg in log_messages:
                print(msg)

            # --- LOGIQUE DE TRADING ---
            if not in_position:
                data = get_bybit_data(TICKER, INTERVAL)
                if data is None: 
                    log_messages.append("! Erreur de récupération des données.")
                    time.sleep(20)
                    continue

                latest_candle_timestamp = data.index[-1]
                if latest_candle_timestamp != last_checked_timestamp:
                    log_messages.append(f"-> Nouvelle bougie détectée. Analyse...")
                    last_checked_timestamp = latest_candle_timestamp
                    
                    signal, last_ppo = check_for_divergence_signal(data)
                    log_messages.append(f"   - PPO actuel: {last_ppo:.4f}")
                    
                    if signal:
                        entry_price = float(data['close'].iloc[-1])
                        side = signal['type']
                        stop_loss = float(signal['price'])
                        risk = (entry_price - stop_loss) if side == "Buy" else (stop_loss - entry_price)
                        
                        if risk > 0:
                            take_profit = entry_price + risk * RR_RATIO if side == "Buy" else entry_price - risk * RR_RATIO
                            qty = math.floor((CAPITAL_PER_TRADE / entry_price) / qty_step) * qty_step

                            log_msg = f"🚨 SIGNAL {side} TROUVÉ ! Passage d'ordre..."
                            log_messages.append(log_msg)
                            print("\n" + log_msg) # Pour visibilité immédiate

                            session.place_order(
                                category="linear", symbol=TICKER, side=side, orderType="Market",
                                qty=str(qty), takeProfit=str(round(take_profit, 2)),
                                stopLoss=str(round(stop_loss, 2))
                            )
                            log_messages.append("✅ Ordre placé avec succès.")
                        else:
                            log_messages.append("⚠️ Risque invalide, ordre annulé.")
                    else:
                        log_messages.append("   - Aucun signal trouvé.")

            time.sleep(20)

        except Exception as e:
            print(f"🔥 Erreur critique dans la boucle principale: {e}")
            log_messages.append(f"🔥 Erreur: {e}")
            time.sleep(20)
        except KeyboardInterrupt:
            print("\nArrêt du bot demandé par l'utilisateur.")
            break

if __name__ == '__main__':
    run_bot()
