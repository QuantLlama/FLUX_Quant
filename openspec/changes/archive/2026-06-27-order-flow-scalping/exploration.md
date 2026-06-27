# Exploration: order-flow-scalping

## Current State
The system has two main parts: the interactive REPL shell in `ui/shell.py` and the `strategies/quantum_llama/` folder which holds the Quantum Llama strategy (a PyTorch LSTM and statistical model pipeline for predictions). Currently, there is a dedicated ICT/Smart Money Concepts analysis layer in `analysis/imbalance.py` that detects Fair Value Gaps (FVGs), Order Blocks, and Liquidity Pools using historical OHLCV data. 

However:
1. There is no active **Order Flow Imbalance (OFI)** detection, which requires actual Bid/Ask or Taker Buy/Sell volume dynamics. While `core/binance_provider.py` downloads `Taker_Buy_Volume` and `Taker_Sell_Volume`, this data is not currently utilized for calculating Order Flow Imbalances or order-book micro-structural indicators.
2. There is no real-time execution strategy that automates scalping entries, exits, sweeps detection, and gaps matching.
3. The current execution model is primarily based on signals from `core/order_builder.py` translating general predictions into single orders, rather than executing low-timeframe high-frequency institutional scalping setups.

## Affected Areas
- `strategies/` — A new strategy file or sub-module needs to be introduced to run the institutional scalping loop.
- `analysis/imbalance.py` — Needs enhancements to add Order Flow Imbalance (OFI) calculations using Bid/Ask volume delta (or Taker Buy/Sell volume as a proxy), and precise Liquidity Sweeps detection (monitoring price crossing equal highs/lows and reversing).
- `core/data_provider.py` / `core/binance_provider.py` — Ensure that Taker Buy/Sell volumes are correctly preserved and exposed to the analysis layer when fetching crypto data, and support comparable volume profile ticks if MetaTrader 5 is used.
- `core/order_builder.py` — Update or extend the order builder to accommodate rapid scalping execution models with tight stop-losses, multiple TPs, and institutional execution mechanics.
- `ui/shell.py` — Add new commands to run and inspect the institutional scalping strategy.

## Approaches

### Approach 1: Create a dedicated new strategy under `strategies/order_flow_scalping.py` (Recommended)
This approach models the scalping strategy as its own self-contained module, separate from the PyTorch-based Quantum Llama strategy. It directly consumes data from `core/data_provider.py`, calculates OFI, sweeps, and FVGs using `analysis/imbalance.py`, and implements a state machine for live paper/live execution.
- **Pros**:
  - Modular design: Keeps Quantum Llama clean and focused on deep learning.
  - Easier testing and isolation of scalping-specific logic (tick data requirements, fast order handling).
  - Clean separation of concerns.
- **Cons**:
  - Requires writing separate orchestration boilerplate (equivalent to run/train scripts).
- **Effort**: Medium (approx. 3-4 days including backtesting harness integration).

### Approach 2: Integrate into the existing `strategies/quantum_llama/` pipeline
This approach expands Quantum Llama by incorporating OFI, Liquidity Sweeps, and FVGs as features for the LSTM / Random Forest model, letting the machine learning model execute the final scalping decisions.
- **Pros**:
  - Leverages the existing dashboard and backtesting engine directly.
- **Cons**:
  - Dilutes the pure ML nature of Quantum Llama.
  - Institutional scalping usually relies on rule-based trigger patterns (e.g., FVG fill + Liquidity sweep + OFI confluence) rather than broad sequence-to-sequence neural network predictions.
- **Effort**: High.

## Recommendation
We recommend **Approach 1** (creating a dedicated `strategies/order_flow_scalping.py` or `strategies/order_flow_scalping/` directory). The rule-based triggers and microsecond-level timing of OFI / Sweeps are best structured inside an independent event-driven or fast loop strategy module, which can call functions in `analysis/imbalance.py` to get indicator states.

## Risks
- **Data Granularity Risk**: Real OFI requires L2 Order Book depth or tick-level trades. yfinance does not provide this. MetaTrader 5 supports ticks but is environment-dependent. Binance supports Taker Buy/Sell volumes in Klines, but only for crypto. Futures scalping on MT5 will require fallback approximation methods (using tick volume deltas).
- **Latency Risk**: Scalping requires fast execution. The MT5 or Binance REST/WebSocket endpoints might introduce execution latency that degrades the performance of a high-frequency strategy.

## Ready for Proposal
Yes
