try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import pandas as pd
from datetime import datetime
import pytz
from rich.console import Console

console = Console()

class MT5Connector:
    def __init__(self):
        self.connected = False
        self.timezone = pytz.timezone("Etc/UTC")

    def connect(self):
        """Initializes connection to MT5 terminal"""
        if not mt5:
            console.print("[red]MetaTrader5 no está disponible en este sistema (solo soportado en Windows).[/red]")
            return False
        if not mt5.initialize():
            console.print(f"[red]Error inicializando MT5: {mt5.last_error()}[/red]")
            return False
        
        self.connected = True
        console.print(f"[green]Conectado a MT5: {mt5.terminal_info().name}[/green]")
        return True

    def shutdown(self):
        if mt5 and self.connected:
            mt5.shutdown()
        self.connected = False

    def get_balance(self):
        """Returns account balance"""
        if not self.connected:
            return 0.0
        info = mt5.account_info()
        return info.balance if info else 0.0

    def get_equity(self):
        """Returns account equity"""
        if not self.connected:
            return 0.0
        info = mt5.account_info()
        return info.equity if info else 0.0

    def get_latest_candles(self, symbol, timeframe=None, n=100):
        """Fetches the last n candles for a symbol"""
        if not self.connected:
            if not self.connect():
                return None

        # Handle default timeframe
        if timeframe is None:
            timeframe = mt5.TIMEFRAME_M1 if mt5 else 1

        # Handle string timeframe mapping
        if isinstance(timeframe, str):
            tf_map = {}
            if mt5:
                tf_map = {
                    "1m": mt5.TIMEFRAME_M1,
                    "5m": mt5.TIMEFRAME_M5,
                    "15m": mt5.TIMEFRAME_M15,
                    "30m": mt5.TIMEFRAME_M30,
                    "1h": mt5.TIMEFRAME_H1,
                    "4h": mt5.TIMEFRAME_H4,
                    "1d": mt5.TIMEFRAME_D1,
                }
            timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_M1 if mt5 else 1)

        # Check if symbol exists in Market Watch
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            console.print(f"[red]Símbolo {symbol} no encontrado en MT5. Verifique el Market Watch.[/red]")
            return None
            
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                console.print(f"[red]No se pudo seleccionar el símbolo {symbol}[/red]")
                return None

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        
        if rates is None:
            console.print(f"[red]Error obteniendo datos para {symbol}[/red]")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Rename columns to match system requirements
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'tick_volume': 'Volume'
        }, inplace=True)
        
        return df[['time', 'Open', 'High', 'Low', 'Close', 'Volume']]

    def get_current_price(self, symbol):
        if not self.connected:
            if not self.connect():
                return None
                
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
            
        return tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2

    def get_positions(self, symbol=None):
        """Returns list of open positions, optionally filtered by symbol"""
        if not self.connected:
            return []
            
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
        if positions is None:
            return []
            
        return positions

    def place_order(self, symbol, order_type, volume, sl=None, tp=None):
        """Sends a market order to MT5"""
        if not self.connected:
            return None

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            console.print(f"[red]Símbolo {symbol} no encontrado[/red]")
            return None
            
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                console.print(f"[red]No se pudo seleccionar {symbol}[/red]")
                return None

        # Determine price and type
        if order_type == "BUY":
            mt5_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        elif order_type == "SELL":
            mt5_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:
            return None

        # Normalize SL/TP
        point = symbol_info.point
        digits = symbol_info.digits
        tick_size = symbol_info.trade_tick_size
        
        if tick_size == 0:
            tick_size = point # Fallback
        
        def round_to_tick(price, tick):
            return round(price / tick) * tick

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": mt5_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "QuantumGAN-AI",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if sl:
            request["sl"] = round(round_to_tick(float(sl), tick_size), digits)
        if tp:
            request["tp"] = round(round_to_tick(float(tp), tick_size), digits)

        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            console.print(f"[red]Error enviando orden: {result.comment}[/red]")
            # Try without SL/TP if stops are invalid, then modify? 
            # No, better to fix the rounding.
            return None
            
        console.print(f"[green]Orden {order_type} ejecutada: {result.order}[/green]")
        return result

    def close_position(self, ticket, symbol=None):
        """Closes a specific position by ticket. Symbol is optional (used for NT8 compatibility)."""
        if not self.connected:
            return False
            
        positions = mt5.positions_get(ticket=ticket)
        if positions is None or len(positions) == 0:
            return False
            
        position = positions[0]
        symbol = position.symbol
        lot = position.volume
        
        # Determine close type (Opposite of open)
        if position.type == mt5.ORDER_TYPE_BUY:
            type_order = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:
            type_order = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": type_order,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "QuantumGAN-Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            console.print(f"[red]Error cerrando posición: {result.comment}[/red]")
            return False
            
        console.print(f"[yellow]Posición {ticket} cerrada.[/yellow]")
        return True
