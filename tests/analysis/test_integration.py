import pytest
import pandas as pd
from unittest.mock import patch

from analysis.report_engine import generate_market_report

@pytest.mark.integration
def test_full_analysis_scoring_pipeline():
    # Load the synthetic recorded CSV snapshot
    csv_path = "tests/data/sample_ohlcv.csv"
    df = pd.read_csv(csv_path, index_col="Date", parse_dates=True)
    
    # Assert that df is loaded properly and has enough periods (>= 50)
    assert not df.empty
    assert len(df) >= 50
    
    # We define patches for network/external API calls to ensure isolation
    # even though generate_market_report only takes df as input.
    with patch("yfinance.download") as mock_yf_download, \
         patch("yfinance.Ticker") as mock_yf_ticker, \
         patch("core.mt5_provider.fetch_mt5_bars") as mock_mt5_bars:
        
        # Run the full scoring engine
        report = generate_market_report(
            df=df,
            symbol="BTC/USDT",
            timeframe="1d",
            capital=10000.0,
            risk_percent=1.0,
            asset_type="Cripto",
        )
        
        # Assert yfinance and MT5 were not called during computation
        mock_yf_download.assert_not_called()
        mock_yf_ticker.assert_not_called()
        mock_mt5_bars.assert_not_called()
        
    # Verify the structure and content of the generated report
    assert isinstance(report, dict)
    assert report["symbol"] == "BTC/USDT"
    assert report["timeframe"] == "1d"
    assert "status" not in report or report["status"] != "error"
    
    # Check that required keys are present
    required_keys = ["symbol", "timeframe", "date", "price", "direction", "score_buy", "score_sell", "setup", "results"]
    for key in required_keys:
        assert key in report, f"Key '{key}' missing from market report"
        
    # Setup assertions
    setup = report["setup"]
    setup_keys = [
        "direccion", "entrada", "stop_loss", "take_profit_1", "take_profit_2",
        "rr_tp1", "rr_tp2", "riesgo_dinero", "tamano_posicion", "position_unit",
        "point_value", "market_type", "valor_nominal", "justificacion"
    ]
    for skey in setup_keys:
        assert skey in setup, f"Key '{skey}' missing from setup dictionary"
        
    # Results dictionary assertions (checking each of the 10 analysis engine components)
    results = report["results"]
    expected_engines = [
        "sr", "fibonacci", "gann", "imbalance", "volatility",
        "volume", "indicators", "market_structure", "quant", "mean_reversion"
    ]
    for engine in expected_engines:
        assert engine in results, f"Analysis engine result '{engine}' missing from results"
        
    # Check that scores are normalized to 0-100
    assert 0 <= report["score_buy"] <= 100
    assert 0 <= report["score_sell"] <= 100
