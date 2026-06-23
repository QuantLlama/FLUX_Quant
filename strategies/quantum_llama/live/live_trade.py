import time
import json
import os
import torch
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from live.connector import MT5Connector
from live.nt8_connector import NinjaTraderConnector
import argparse
from qutils.config_manager import load_symbol_map
from models.generator import Generator
from data.loader import preprocess_data
import joblib
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from analysis.market_filter import MarketFilter

console = Console()

def load_model_and_scaler(ticker, timeframe="1h"):
    # Paths
    # Sanitize ticker for filename
    safe_ticker = ticker.replace("=", "").replace("-", "")
    models_dir = "outputs/models"
    model_prefix = f"{models_dir}/{safe_ticker}_{timeframe}"
    
    model_path = f"{model_prefix}_generator.pth"
    scaler_path = f"{model_prefix}_scaler.pkl"
    config_path = f"{model_prefix}_config.json"
    
    # Fallback to old path if specific model not found (for backward compatibility)
    if not os.path.exists(model_path):
        console.print(f"[yellow]Modelo específico no encontrado: {model_path}. Intentando fallback...[/yellow]")
        model_path = "outputs/generator.pth"
        scaler_path = "outputs/scaler.pkl"
        config_path = "outputs/model_config.json"

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        raise FileNotFoundError(f"No se encontraron los archivos del modelo para {ticker} ({timeframe}). Ejecute un entrenamiento primero.")
        
    scaler = joblib.load(scaler_path)
    
    # Load Model Config
    hidden_dim = 128
    num_layers = 2
    trade_timeframe = "1m" # Default if config missing
    seq_length = 60
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                model_conf = json.load(f)
                hidden_dim = model_conf.get("hidden_dim", 128)
                num_layers = model_conf.get("num_layers", 2)
                # If timeframe was passed as argument, use it. Otherwise use config.
                if timeframe:
                    trade_timeframe = timeframe
                else:
                    trade_timeframe = model_conf.get("trade_timeframe", "1m")
                seq_length = model_conf.get("seq_length", 60)
        except Exception as e:
            console.print(f"[yellow]Advertencia: No se pudo cargar config ({e}). Usando valores por defecto.[/yellow]")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    INPUT_DIM = 7 # Log_Ret_Close, Log_Ret_High, Log_Ret_Low, Log_Vol, RSI, ADX, ATR
    
    model = Generator(INPUT_DIM, hidden_dim, num_layers, INPUT_DIM).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()
    
    return model, scaler, device, trade_timeframe, seq_length

def run_live_trading(sys_ticker, asset_type, platform="mt5", timeframe=None, initial_volume=1.0):
    # 1. Load Configuration
    symbol_map = load_symbol_map(platform)  # Load platform-specific mapping
    
    if asset_type not in symbol_map or sys_ticker not in symbol_map[asset_type]:
        console.print(f"[red]No hay mapeo configurado para {sys_ticker} en {platform.upper()}. Vaya a Configuración.[/red]")
        return

    platform_symbol = symbol_map[asset_type][sys_ticker]
    console.print(f"[green]Iniciando Trading en Vivo para {sys_ticker} ({platform.upper()}: {platform_symbol})[/green]")

    # 2. Load AI Model
    try:
        # Use provided timeframe or default to 1h
        tf_to_load = timeframe if timeframe else "1h"
        model, scaler, device, trade_timeframe, seq_length = load_model_and_scaler(sys_ticker, timeframe=tf_to_load)
        console.print(f"[green]Modelo cargado. Timeframe: {trade_timeframe}, SeqLength: {seq_length}[/green]")
    except Exception as e:
        console.print(f"[red]Error cargando modelo: {e}[/red]")
        return

    # 3. Connect to Platform
    if platform == "mt5":
        connector = MT5Connector()
    elif platform == "nt8":
        connector = NinjaTraderConnector()
    elif platform == "binance":
        from live.binance_connector import BinanceConnector
        connector = BinanceConnector()
    else:
        console.print(f"[red]Plataforma no soportada: {platform}[/red]")
        return

    if not connector.connect():
        return
        
    # Initialize Market Filter
    market_filter = MarketFilter()
    last_trade_time = 0
    COOLDOWN_SECONDS = 300 # 5 Minutes cooldown

    # 4. Live Loop
    console.print(f"[bold yellow]Esperando nueva vela ({trade_timeframe})... (Ctrl+C para detener)[/bold yellow]")
    
    # State variables for daily limits
    current_date = datetime.now().date()
    daily_trades = 0
    current_date = datetime.now().date()
    daily_trades = 0
    initial_balance = connector.get_balance()
    
    # Consecutive Signal Logic (v2)
    last_raw_signal = "HOLD"
    consecutive_signals = 0
    
    try:
        while True:
            # 1. Reload Config
            config_path = "config/live_config.json"
            config = {
                "automation_enabled": False,
                "volume": initial_volume,
                "max_daily_loss": 500.0,
                "daily_profit_target": 100.0,
                "max_trades_per_day": 5,
                "start_hour": "09:30",
                "end_hour": "16:00",
                "min_adx": 15, # Lowered from 20
                "rsi_upper": 70,
                "rsi_lower": 30,
                "require_candle_confirmation": True,
                "consecutive_signals": 1,
                "use_ema_filter": False # Disabled by default to avoid being too strict
            }
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config.update(json.load(f)) # Update defaults with file
                except:
                    pass
            
            # 2. Fetch Account Info
            current_balance = connector.get_balance()
            current_equity = connector.get_equity()
            
            # Reset daily stats if new day
            now = datetime.now()
            if now.date() != current_date:
                current_date = now.date()
                daily_trades = 0
                initial_balance = current_balance
            
            daily_pnl = current_equity - initial_balance
            
            # 3. Check Constraints
            time_str = now.strftime("%H:%M")
            is_time_valid = config["start_hour"] <= time_str <= config["end_hour"]
            is_loss_valid = daily_pnl > -float(config["max_daily_loss"])
            is_profit_target_reached = daily_pnl >= float(config.get("daily_profit_target", 100.0))
            is_trades_valid = daily_trades < int(config["max_trades_per_day"])
            
            # Cooldown Check
            on_cooldown = (time.time() - last_trade_time) < COOLDOWN_SECONDS
            
            can_trade = config["automation_enabled"] and is_time_valid and is_loss_valid and is_trades_valid and not is_profit_target_reached and not on_cooldown

            # Fetch data (need enough for RSI + Sequence)
            # Use dynamic trade_timeframe and seq_length
            # Increased buffer to 100 to account for EMA(50) dropna
            df = connector.get_latest_candles(platform_symbol, timeframe=trade_timeframe, n=seq_length + 100)
            
            if df is not None and not df.empty:
                # Feature Engineering (RSI + ADX + ATR via MarketFilter)
                df = market_filter.calculate_indicators(df)
                df = df.dropna()
                
                if len(df) >= seq_length + 1: # Need +1 for returns
                    # --- Feature Engineering (Match loader.py) ---
                    # Calculate Log Returns
                    df['Log_Ret_Close'] = np.log(df['Close'] / df['Close'].shift(1))
                    df['Log_Ret_High']  = np.log(df['High'] / df['High'].shift(1))
                    df['Log_Ret_Low']   = np.log(df['Low'] / df['Low'].shift(1))
                    df['Log_Vol']       = np.log1p(df['Volume'])
                    
                    # Check if columns exist (MarketFilter adds them)
                    if 'RSI' not in df.columns: df['RSI'] = 50.0
                    if 'ADX' not in df.columns: df['ADX'] = 20.0
                    if 'ATR' not in df.columns: df['ATR'] = 0.0
                    
                    # Drop NaNs
                    df_features = df.dropna()
                    
                    if len(df_features) < seq_length:
                        console.print("[yellow]Not enough data after feature engineering[/yellow]")
                        time.sleep(5)
                        continue
                         
                    # Select features: ['Log_Ret_Close', 'Log_Ret_High', 'Log_Ret_Low', 'Log_Vol', 'RSI', 'ADX', 'ATR']
                    last_sequence = df_features.tail(seq_length)[['Log_Ret_Close', 'Log_Ret_High', 'Log_Ret_Low', 'Log_Vol', 'RSI', 'ADX', 'ATR']].values
                    
                    # Scale
                    last_sequence_scaled = scaler.transform(last_sequence)
                    
                    # Tensor
                    input_tensor = torch.FloatTensor(last_sequence_scaled).unsqueeze(0).to(device)
                    
                    # Predict
                    with torch.no_grad():
                        prediction_seq = model(input_tensor)
                        prediction_scaled = prediction_seq[:, -1, :].cpu().numpy() # Shape (1, 7)
                        
                    # Inverse Scale Prediction
                    # We need to inverse transform to get the real Log Return
                    # Create dummy array with correct shape
                    dummy_pred = np.zeros((1, scaler.n_features_in_))
                    dummy_pred[:, 0] = prediction_scaled[:, 0] # Index 0 is Log_Ret_Close
                    
                    prediction_real_features = scaler.inverse_transform(dummy_pred)
                    predicted_log_return = prediction_real_features[0, 0]
                    
                    current_price = df['Close'].iloc[-1]
                    
                    # Convert Log Return to Price Target
                    # Target = Current * exp(Log_Return)
                    prediction_real = current_price * np.exp(predicted_log_return)
                    
                    # Calculate Volatility for SL/TP (ATR based or fallback)
                    if 'ATR' in df.columns:
                        volatility = df['ATR'].iloc[-1]
                    else:
                        volatility = df['Close'].tail(20).std()
                        if pd.isna(volatility) or volatility == 0:
                            volatility = current_price * 0.001
                    
                    # Dynamic Signal Threshold
                    signal = "HOLD"
                    # Threshold can be based on return magnitude or price diff
                    # Let's use a small threshold for return
                    threshold_return = 0.0001 # 0.01% change
                    
                    if predicted_log_return > threshold_return:
                        signal = "BUY"
                    elif predicted_log_return < -threshold_return:
                        signal = "SELL"
                        
                    # --- CONSECUTIVE SIGNAL FILTER (v2) ---
                    required_consecutive = config.get("consecutive_signals", 1)
                    if required_consecutive > 1:
                        if signal == last_raw_signal and signal != "HOLD":
                            consecutive_signals += 1
                        else:
                            consecutive_signals = 1
                            last_raw_signal = signal
                            
                        if consecutive_signals < required_consecutive:
                            # console.print(f"[dim]Waiting for confirmation ({consecutive_signals}/{required_consecutive})[/dim]")
                            signal = "HOLD"
                    else:
                        consecutive_signals = 1 # Reset if feature disabled
                        
                    # --- VALIDATION ---
                    validation_msg = "OK"
                    if signal != "HOLD":
                        is_valid, validation_msg = market_filter.check_conditions(df, signal, config)
                        if not is_valid:
                            # console.print(f"[dim]Señal {signal} filtrada: {validation_msg}[/dim]")
                            signal = "HOLD" # Override signal
                        
                    # --- EXECUTION LOGIC ---
                    positions = connector.get_positions(platform_symbol)
                    has_position = len(positions) > 0
                    
                    sl_price = 0.0
                    tp_price = 0.0
                    entry_price = 0.0
                    
                    if has_position:
                        # Check if we need to close (Opposite signal)
                        pos = positions[0] # Assume 1 position max
                        pos_type = "BUY" if pos.type == 0 else "SELL" # 0 is BUY in MT5
                        entry_price = pos.price_open
                        
                        # Only close if automation is enabled OR manually managed? 
                        # Let's say automation controls closing too.
                        if config["automation_enabled"]:
                            if (pos_type == "BUY" and signal == "SELL") or (pos_type == "SELL" and signal == "BUY"):
                                console.print(f"[yellow]Señal opuesta detectada ({signal}). Cerrando posición {pos_type}...[/yellow]")
                                if connector.close_position(pos.ticket, symbol=platform_symbol):
                                    has_position = False # Now flat
                                    last_trade_time = time.time() # Start cooldown
                            else:
                                sl_price = pos.sl
                                tp_price = pos.tp
                        else:
                             sl_price = pos.sl
                             tp_price = pos.tp
                            
                    if not has_position and signal != "HOLD":
                        if can_trade:
                            # Execute New Trade
                            # Calculate SL/TP using ATR
                            sl_points = volatility * 2.0 
                            tp_points = volatility * 3.0 
                            
                            if signal == "BUY":
                                sl_price = current_price - sl_points
                                tp_price = current_price + tp_points
                            else:
                                sl_price = current_price + sl_points
                                tp_price = current_price - tp_points
                                
                            console.print(f"[bold green]Ejecutando {signal} | SL: {sl_price:.2f} | TP: {tp_price:.2f}[/bold green]")
                            
                            # Use configured volume
                            volume = float(config["volume"])
                            if connector.place_order(platform_symbol, signal, volume, sl=sl_price, tp=tp_price):
                                daily_trades += 1
                                last_trade_time = time.time() # Start cooldown
                        else:
                            reason = []
                            if not config['automation_enabled']: reason.append("Auto Off")
                            if not is_time_valid: reason.append("Time")
                            if not is_trades_valid: reason.append("Max Trades")
                            if on_cooldown: reason.append(f"Cooldown ({int(COOLDOWN_SECONDS - (time.time() - last_trade_time))}s)")
                            
                            console.print(f"[dim]Señal {signal} ignorada ({', '.join(reason)})[/dim]")

                    # Get Account Info from Platform (NT8/MT5)
                    if hasattr(connector, 'get_account_info'):
                        account_info = connector.get_account_info()
                        if account_info:
                            current_balance = account_info['balance']
                            current_equity = account_info['equity']
                            # Track real daily PnL from platform (Realized + Unrealized)
                            daily_pnl = account_info['profit']

                    # Update Status JSON for Dashboard
                    status = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "ticker": sys_ticker,
                        "platform_symbol": platform_symbol,
                        "current_price": float(current_price),
                        "prediction": float(prediction_real),
                        "signal": signal,
                        "has_position": has_position,
                        "entry_price": float(entry_price),
                        "sl_price": round(float(sl_price), 2),
                        "tp_price": round(float(tp_price), 2),
                        "last_candles": df.tail(50).to_dict(orient='records'),
                        "account": {
                            "balance": float(current_balance),
                            "equity": float(current_equity),
                            "daily_pnl": float(daily_pnl),
                            "daily_trades": daily_trades
                        },
                        "strategy": {
                            "timeframe": trade_timeframe,
                            "seq_length": seq_length
                        },
                        "config": config,
                        "validation": validation_msg
                    }
                    
                    with open("live_status.json", "w") as f:
                        json.dump(status, f, default=str)
                        
                    console.print(f"P: {current_price:.2f} | S: {signal} | PnL: {daily_pnl:.2f} | Valid: {validation_msg}")
                    
            time.sleep(2) # Poll every 2 seconds
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Deteniendo Trading en Vivo...[/yellow]")
    finally:
        connector.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='QuantumGAN Live Trading')
    parser.add_argument('--ticker', type=str, default="MNQ=F", help='Ticker del sistema (ej: MNQ=F)')
    parser.add_argument('--asset_type', type=str, default="Futures", help='Tipo de activo (Futures, Crypto, Stocks)')
    parser.add_argument('--platform', type=str, default="mt5", choices=['mt5', 'nt8'], help='Plataforma de trading (mt5, nt8)')
    
    parser.add_argument('--timeframe', type=str, default=None, help='Timeframe del modelo (ej: 1h, 5m)')
    
    args = parser.parse_args()
    
    run_live_trading(args.ticker, args.asset_type, args.platform, args.timeframe)
