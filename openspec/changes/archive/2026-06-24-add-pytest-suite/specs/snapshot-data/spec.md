# Snapshot Data Specification

## Purpose
Ensures integration tests run against reproducible, recorded CSV market data snapshots rather than live API calls.

## Requirements

### Requirement: Local Snapshots
The system MUST load data from local CSV snapshots for integration tests.

#### Scenario: Loading historical snapshot
- GIVEN a CSV snapshot located in `tests/data/`
- WHEN an integration test pipeline requests historical data
- THEN the system loads the DataFrame directly from the CSV without network requests

### Requirement: Network Isolation
The system MUST NOT make external network requests during tests.

#### Scenario: Preventing live API calls
- GIVEN an active test session
- WHEN a function attempts to call `yfinance` to fetch live data
- THEN the test environment blocks the network call and fails the test or uses mock data
