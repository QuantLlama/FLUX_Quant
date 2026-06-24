# Synthetic Fixtures Specification

## Purpose
Provides deterministic, algorithmically generated DataFrames for predictable testing of analysis functions across various market scenarios.

## Requirements

### Requirement: Market Trends
The system MUST generate deterministic synthetic market trend data.

#### Scenario: Bullish trend generation
- GIVEN the synthetic fixture factory
- WHEN the `bullish_trend` fixture is requested
- THEN it returns a DataFrame with strictly increasing price action over time

#### Scenario: Bearish trend generation
- GIVEN the synthetic fixture factory
- WHEN the `bearish_trend` fixture is requested
- THEN it returns a DataFrame with strictly decreasing price action over time

### Requirement: Edge Case Scenarios
The system MUST generate data for edge cases.

#### Scenario: Empty dataset
- GIVEN the synthetic fixture factory
- WHEN the `empty_series` fixture is requested
- THEN it returns an empty DataFrame with the correct OHLCV columns

#### Scenario: Short dataset
- GIVEN the synthetic fixture factory
- WHEN the `short_series` fixture is requested
- THEN it returns a DataFrame with exactly 5 rows
