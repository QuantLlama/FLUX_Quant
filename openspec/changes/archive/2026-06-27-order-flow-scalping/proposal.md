# Proposal: Order-Flow Scalping Strategy

## Intent
Implement an automated order-flow scalping engine exploiting micro-inefficiencies via Order Flow Imbalance (OFI) calculations on liquid futures and crypto instruments.

## Scope
- **In Scope**:
  - Live tick/Level-2 ingestion from Binance (BTC-USDT) and MT5 (MES, MNQ, GC/ORO, CL/CRUDO).
  - OFI metric logic using L2 order book delta or tick-volume classification fallback.
  - Latency-optimized market order execution upon trigger threshold crossing.
  - Risk engine: Fixed SL (sweep high/low protection) and dynamic TP/trailing exit based on opposite liquidity pool depletion.
- **Out of Scope**:
  - Advanced portfolio optimization or multi-asset allocation.
  - Non-scalping execution types (e.g., swing grids).

## Capabilities
- `order-flow-scalping-strategy`: Latency-sensitive real-time processing and immediate execution execution loop.

## Approach
Connect to Binance and MT5 APIs, calculate real-time OFI delta from L2 books (falling back to tick-volume classification if L2 is absent), execute immediate market entries on threshold signals, and manage exits via fixed protective SL and dynamic TP based on order-flow pool exhaustion.

## Affected Areas
- Live data ingestion handlers (Binance/MT5 connector layers).
- Execution/broker router wrappers.
- Strategy decision engine and risk management/SL-TP tracking modules.

## Risks & Mitigation
- **Latency/Slippage**: Can turn profitable scalps into losses. Mitigated by execution-path optimization and maximum slippage filters.
- **Data Gap**: Missing L2 books. Mitigated by automated fallback to tick-volume classification.

## Rollback Plan
Revert code changes in execution and risk modules to previous stable strategy commits. Disable strategy flag via configuration without code redeployment.

## Dependencies
- Binance API connectivity (websockets for L2 depth).
- MT5 Terminal/Gateway API.

## Success Criteria
- Round-trip execution latency under 50ms.
- OFI fallback correctly switches to tick-volume.
- Strict adherence to SL/TP constraints.
