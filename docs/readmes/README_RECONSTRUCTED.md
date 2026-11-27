# v3.2 reconstructed fixture exploratory mode

These GW5-9 fixtures were reconstructed retrospectively. Club IDs are inferred from player rosters, NOT independently verified. This is **NOT** a point-in-time backtest. No fake capture timestamps are used.

Run from project root after supplying your own historical_data player history:

```bash
python -m analysis.walkforward_v32 --fixture-snapshot historical_data/fixtures_reconstructed_gw5_gw9.json --allow-reconstructed --weeks 5 6 7 8 9
```

Without `--allow-reconstructed`, the loader refuses retrospective data. The source data is intended for exploratory testing only. The historical_data fixture files alone are insufficient to run the backtest; historical per-week player records are also needed.
