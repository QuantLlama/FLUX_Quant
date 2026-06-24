import pytest
import sys
from unittest.mock import patch, MagicMock
from core.order_executor import order_executor
from ui.shell import AnalysisShell

class MockMT5Position:
    def __init__(self, symbol: str, volume: float, profit: float):
        self.symbol = symbol
        self.volume = volume
        self.profit = profit

@pytest.mark.unit
def test_get_mt5_positions_success():
    # We patch sys.modules['MetaTrader5'] to avoid dependency issues during tests.
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True
    mock_mt5.positions_get.return_value = (
        MockMT5Position("EURUSD", 0.1, 15.5),
        MockMT5Position("GBPUSD", 0.2, -5.0),
    )
    
    with patch.dict(sys.modules, {"MetaTrader5": mock_mt5}):
        positions = order_executor.get_mt5_positions()
        
        assert len(positions) == 2
        assert positions[0] == {
            "platform": "MT5",
            "symbol": "EURUSD",
            "size": 0.1,
            "pnl": 15.5,
        }
        assert positions[1] == {
            "platform": "MT5",
            "symbol": "GBPUSD",
            "size": 0.2,
            "pnl": -5.0,
        }
        mock_mt5.initialize.assert_called_once()
        mock_mt5.positions_get.assert_called_once()

@pytest.mark.unit
def test_get_mt5_positions_init_failed():
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = False
    
    with patch.dict(sys.modules, {"MetaTrader5": mock_mt5}):
        positions = order_executor.get_mt5_positions()
        assert positions == []
        mock_mt5.initialize.assert_called_once()
        mock_mt5.positions_get.assert_not_called()

@pytest.mark.unit
def test_get_mt5_positions_empty():
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True
    mock_mt5.positions_get.return_value = ()
    
    with patch.dict(sys.modules, {"MetaTrader5": mock_mt5}):
        positions = order_executor.get_mt5_positions()
        assert positions == []

@pytest.mark.unit
def test_get_mt5_positions_exception():
    mock_mt5 = MagicMock()
    mock_mt5.initialize.side_effect = RuntimeError("MT5 error")
    
    with patch.dict(sys.modules, {"MetaTrader5": mock_mt5}):
        positions = order_executor.get_mt5_positions()
        assert positions == []

@pytest.mark.unit
def test_get_binance_positions_success():
    mock_exchange = MagicMock()
    mock_exchange.fetch_positions.return_value = [
        {"symbol": "BTCUSDT", "contracts": 0.5, "unrealizedPnl": 100.25},
        {"symbol": "ETHUSDT", "contracts": 0.0, "unrealizedPnl": 0.0},  # should be filtered out
        {"symbol": "SOLUSDT", "contracts": -2.5, "unrealizedPnl": -15.5},
    ]
    
    with patch("core.binance_trader._make_exchange", return_value=(mock_exchange, None)):
        positions = order_executor.get_binance_positions()
        
        assert len(positions) == 2
        assert positions[0] == {
            "platform": "Binance Futures",
            "symbol": "BTCUSDT",
            "size": 0.5,
            "pnl": 100.25,
        }
        assert positions[1] == {
            "platform": "Binance Futures",
            "symbol": "SOLUSDT",
            "size": -2.5,
            "pnl": -15.5,
        }
        mock_exchange.fetch_positions.assert_called_once()

@pytest.mark.unit
def test_get_binance_positions_init_failed():
    with patch("core.binance_trader._make_exchange", return_value=(None, "Connection Error")):
        positions = order_executor.get_binance_positions()
        assert positions == []

@pytest.mark.unit
def test_get_binance_positions_exception():
    mock_exchange = MagicMock()
    mock_exchange.fetch_positions.side_effect = RuntimeError("Binance API error")
    
    with patch("core.binance_trader._make_exchange", return_value=(mock_exchange, None)):
        positions = order_executor.get_binance_positions()
        assert positions == []

@pytest.mark.unit
def test_shell_order_positions_empty():
    shell = AnalysisShell()
    
    with patch.object(order_executor, "get_mt5_positions", return_value=[]), \
         patch.object(order_executor, "get_binance_positions", return_value=[]), \
         patch("ui.shell.console.print") as mock_print:
         
        shell.cmd_order(["positions"])
        
        # Verify the empty message is printed
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        assert "No hay posiciones abiertas." in args[0]

@pytest.mark.unit
def test_shell_order_positions_display():
    shell = AnalysisShell()
    
    mt5_mock_data = [
        {"platform": "MT5", "symbol": "EURUSD", "size": 0.1, "pnl": 15.5}
    ]
    binance_mock_data = [
        {"platform": "Binance Futures", "symbol": "BTCUSDT", "size": 0.5, "pnl": 100.25}
    ]
    
    with patch.object(order_executor, "get_mt5_positions", return_value=mt5_mock_data), \
         patch.object(order_executor, "get_binance_positions", return_value=binance_mock_data), \
         patch("ui.shell.console.print") as mock_print:
         
        shell.cmd_order(["positions"])
        
        # Verify a table is printed
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        table = args[0]
        
        # Check that it is indeed a rich Table
        from rich.table import Table
        assert isinstance(table, Table)
        assert table.title == "📈 Posiciones Abiertas"
        
        # Check columns
        columns = [col.header for col in table.columns]
        assert "Plataforma" in columns
        assert "Símbolo" in columns
        assert "Tamaño" in columns
        assert "PnL" in columns
