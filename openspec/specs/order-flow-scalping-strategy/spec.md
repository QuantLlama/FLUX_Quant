# Order Flow Scalping Strategy Specification

## 1. Overview
The `order-flow-scalping-strategy` capability defines an automated high-frequency execution engine. It SHALL monitor real-time order book imbalances and liquidity dynamics to execute rapid, low-latency trades.

## 2. Requirements

### 2.1 Market Entry Execution
* **REQ-1 (OFI Threshold):** The system SHALL calculate the Order Flow Imbalance (OFI) on a per-tick basis. If the OFI crosses a pre-configured threshold, the system SHALL signal a potential entry.
* **REQ-2 (Liquidity Sweep Confirmation):** An entry signal SHALL only be validated if a liquidity sweep of a recent swing high or swing low is confirmed within the last $N$ ticks.
* **REQ-3 (Fair Value Gap Creation):** The entry algorithm SHALL confirm the creation of a Fair Value Gap (FVG) in the direction of the sweep recovery before executing the entry.
* **REQ-4 (Order Placement):** Upon validation of REQ-1, REQ-2, and REQ-3, the system SHALL immediately submit a market order.

### 2.2 Market Exit Execution
* **REQ-5 (Take Profit):** The system SHALL route a Take Profit (TP) order targeting the opposite liquidity pool (swing point).
* **REQ-6 (Stop Loss):** The system SHALL place a hard Stop Loss (SL) order immediately upon entry execution.

### 2.3 Fallback and Edge Cases
* **REQ-7 (L2 Fallback):** If MT5 Layer 2 (L2) depth data is missing or unavailable, the system SHALL fallback to tick-volume classification to estimate order book imbalance.
* **REQ-8 (Slippage Filter):** The system SHALL reject market order submission if the projected slippage exceeds a maximum slippage threshold.

---

## 3. Scenarios

### Scenario 1: Standard Entry and TP Exit (Happy Path)
* **Given** the MT5 L2 depth data is active and the OFI threshold is set to $+2.5$
* **When** a liquidity sweep of the session low occurs, and a bullish FVG is created, and the OFI crosses $+2.7$
* **Then** the system SHALL execute a market BUY order, place a hard Stop Loss below the sweep candle low, and route a Take Profit order at the opposite liquidity pool.

### Scenario 2: MT5 L2 Missing Fallback (Edge Case)
* **Given** the MT5 L2 depth feed is disconnected or fails to return depth metrics
* **When** a liquidity sweep occurs and an FVG is created
* **Then** the system SHALL fallback to tick-volume classification to estimate order book imbalance
* **And** it SHALL proceed with trade validation and execution using the fallback metrics.

### Scenario 3: Maximum Slippage Threshold Breached (Edge Case)
* **Given** the projected execution slippage is $3.2$ pips, and the maximum slippage threshold is configured to $2.0$ pips
* **When** all entry signals (OFI, Sweep, FVG) are met
* **Then** the system SHALL prevent the market order submission and log a slippage breach error.

### Scenario 4: Stop Loss Triggered (Edge Case)
* **Given** an active BUY trade is open with a hard Stop Loss set at 1.1200
* **When** the market price falls to or below 1.1200
* **Then** the system SHALL immediately execute the Stop Loss market order to exit the trade.
