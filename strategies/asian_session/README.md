# Asian Session Breakout — Estrategia para MES/MNQ

Estrategia de ruptura del rango asiático diseñada para futuros **MES** (Micro E-mini S&P 500) y **MNQ** (Micro E-mini Nasdaq-100).

## Concepto

El mercado asiático (sesión Tokyo 00:00–08:00 UTC) suele generar un rango de consolidación. Cuando el mercado estadounidense despierta, el precio frecuentemente **rompe** ese rango y continúa en la dirección de la ruptura. La estrategia captura esos movimientos iniciales.

## Componentes

| Módulo | Responsabilidad |
|--------|----------------|
| `range_calculator.py` | Calcula high/low/mid/VWAP/POC/VAH/VAL/ATR de la sesión asiática |
| `trade_guard.py` | Máximo 2 trades/día, cooldown de 30 min entre operaciones |
| `news_filter.py` | Bloquea entradas ±30 min alrededor de eventos económicos de alto impacto |
| `breakout_logic.py` | Evalúa si el precio rompió el rango, calcula confianza, SL y TP |
| `asian_breakout_strategy.py` | Orquestador que integra todos los componentes |
| `run.py` | CLI interactiva para operar en vivo |

## Flujo de Operación

```
00:00 UTC — Inicio sesión asiática (acumula barras 5m)
08:00 UTC — Fin sesión asiática → se calcula el rango
07:30-09:30 UTC — Ventana de entrada
  1. ¿Dentro de ventana? → sí
  2. ¿TradeGuard permite entrada? → sí (≤2 trades, sin cooldown)
  3. ¿NewsFilter bloquea? → no
  4. ¿Precio rompió rango asiático? → sí
  5. Calcular SL (1.5× ATR), TP1 (2R), TP2 (3R)
  6. Enviar orden MARKET
  7. Registrar trade en TradeGuard
```

## Parámetros (config.toml)

```toml
[asian_session]
enabled = true
symbols = ["MES=F", "MNQ=F"]
session_start_utc = "00:00"
session_end_utc = "08:00"
entry_window_start_utc = "07:30"
entry_window_end_utc = "09:30"
max_trades_per_day = 2
min_atr_percentile = 60
atr_sl_multiplier = 1.5
rr_target_1 = 2.0
rr_target_2 = 3.0
cooldown_minutes = 30
data_timeframe = "5m"
entry_timeframe = "1m"
news_filter_enabled = true
news_block_minutes = 30
```

## Ejecución

```bash
# Modo paper (por defecto)
python strategies/asian_session/run.py

# Modo live (requiere config.toml: trading.mode = "live")
python strategies/asian_session/run.py
```

## Tests

```bash
pytest tests/test_asian_session_range.py \
       tests/test_trade_guard.py \
       tests/test_news_filter.py \
       tests/test_breakout_logic.py \
       tests/test_asian_breakout_strategy.py \
       tests/test_asian_session_run.py \
       -v
```

## Brokers Soportados

- **MT5** — MES/MNQ futures (recomendado)
- **NinjaTrader 8** — via file exchange
- **Binance Futures** — crypto solo

## Notas

- La estrategia respeta el modo paper/live global (`trading.mode` en `config.toml`)
- Los datos se obtienen via MT5 (preferido) con fallback a Yahoo Finance
- Rithmic/CQG/IBKR no están soportados
