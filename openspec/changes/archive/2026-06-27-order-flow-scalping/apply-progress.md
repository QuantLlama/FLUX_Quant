### Apply Progress: Order-Flow Scalping Strategy

- **Status**: Completed tasks implemented using strict TDD cycle.
- **Completed Tasks**:
  - T1.1 Strategy Scaffold: manifest.json created and validated.
  - T1.2 Shared Indicators: calculate_l2_ofi & calculate_tick_volume_ofi functions exposed in `analysis/imbalance.py`.
  - T1.3 Unit Test Suite: Created unit tests for indicators in `tests/test_imbalance_ofi.py`.
  - T2.1 Strategy Entry Points: `strategies/order_flow_scalping/__init__.py` exposed.
  - T2.2/2.3/2.4 Strategy Core, Decisions & Execution: `strategies/order_flow_scalping/run.py` implemented with real-time queue, sweep tracking, and risk parameters.
  - T3.1 Integration Test Suite: Verified entire strategy flow in `tests/test_order_flow_scalping.py`.

### TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| T1.1 | N/A (JSON) | N/A | N/A | N/A | N/A | N/A | N/A |
| T1.2 | `tests/test_imbalance_ofi.py` | Unit | ✅ 4 passed | ✅ Written | ✅ Passed | ✅ 4 cases | ✅ Clean |
| T2.1 | `tests/test_order_flow_scalping.py` | Unit | N/A | ✅ Written | ✅ Passed | ➖ Single | ✅ Clean |
| T2.2 | `tests/test_order_flow_scalping.py` | Unit | N/A | ✅ Written | ✅ Passed | ✅ 2 cases | ✅ Clean |
| T2.3 | `tests/test_order_flow_scalping.py` | Unit | N/A | ✅ Written | ✅ Passed | ✅ 3 cases | ✅ Clean |
| T2.4 | `tests/test_order_flow_scalping.py` | Integration | N/A | ✅ Written | ✅ Passed | ✅ 2 cases | ✅ Clean |
