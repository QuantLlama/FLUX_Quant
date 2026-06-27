# Tasks: Order-Flow Scalping Strategy

## 1. Phase 1: Shared Indicators & Helper Functions
### T1.1: Create Strategy Scaffold
- [x] **File**: `strategies/order_flow_scalping/manifest.json` (New)
- **Description**: Add manifest json containing name, description, and configurable parameters for shell discovery.
- **Verification**: Run `python -m json.tool strategies/order_flow_scalping/manifest.json` to verify JSON syntax.

### T1.2: Implement L2 OFI & Fallback Classifiers in `analysis/imbalance.py`
- [x] **File**: `analysis/imbalance.py` (Modified)
- **Description**: Expose calculation functions `calculate_l2_ofi(bids, asks)` and `calculate_tick_volume_ofi(ticks_df)` in the analysis library.
- **Verification**: Ensure the signatures match tick-level parameters. Run unit tests to verify mathematical correctness.

### T1.3: Unit Test Suite for Indicators
- [x] **File**: `tests/test_imbalance_ofi.py` (New)
- **Description**: Add unit tests focusing on OFI calculation and fallback tick volume classifier using static dataframes.
- **Verification**: Run `pytest tests/test_imbalance_ofi.py`.

---

## 2. Phase 2: Strategy Core Logic & State Machine
### T2.1: Implement Strategy Scaffold and Entry Points
- [x] **File**: `strategies/order_flow_scalping/__init__.py` (New)
- **Description**: Expose the `OrderFlowScalpingStrategy` class, inheriting from the base strategy class.
- **Verification**: Import via python interactive shell: `from strategies.order_flow_scalping import OrderFlowScalpingStrategy`.

### T2.2: Real-time Ingestion & Queue Pipeline
- [x] **File**: `strategies/order_flow_scalping/run.py` (New)
- **Description**: Implement asynchronous queue readers for L2 (Binance WebSocket depth updates) and tick pollers (MT5 Gateway).
- **Verification**: Write mock queues feeding depth updates to check thread stability.

### T2.3: Decision Engine (Sweeps, FVG, & OFI Thresholding)
- [x] **File**: `strategies/order_flow_scalping/run.py` (New)
- **Description**: Track swing high/low pivots, FVG mitigation state, and rolling OFI Z-scores. Trigger entry signals when all alignment parameters match.
- **Verification**: Check state transition bounds against sample historical sweeps.

### T2.4: Execution & Risk Management Integration
- [x] **File**: `strategies/order_flow_scalping/run.py` (New)
- **Description**: Implement protective SL execution behind the sweeping wick ($0.5 \times ATR$ buffer) and split dynamic TP targeting opposite liquidity pools.
- **Verification**: Verify target and trailing stops inside mock strategy loop.

---

## 3. Phase 3: Integration & System Testing
### T3.1: Integration Test Suite
- [x] **File**: `tests/test_order_flow_scalping.py` (New)
- **Description**: End-to-end integration tests using Mock execution connector and simulated order book feeds.
- **Verification**: Run `pytest tests/test_order_flow_scalping.py`.

### T3.2: Verify Latency and Fallbacks
- [x] **File**: `tests/test_order_flow_scalping.py` (Modified/New)
- **Description**: Add assertions verifying fallback from L2 to tick volume and print round-trip performance benchmarks.
- **Verification**: Latency metrics log below 50ms inside runner telemetry.

---

## Review Workload Forecast
- **Estimated changed lines**: 250-350
- **400-line budget risk**: Low/Medium
- **Chained PRs recommended**: No
- **Delivery strategy**: ask-on-risk
- **Decision needed before apply**: No
- **Suggested work-unit PR split**: Not needed
