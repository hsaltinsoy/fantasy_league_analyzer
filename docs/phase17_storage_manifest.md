# Phase 17 per-file storage inventory

Top-level JSON entries are a shape count, not necessarily a player or match count. No file contents are included. See `phase17_storage_audit.md` for migration risks.

| Path | Format | Bytes | Count | Class | Consumers/writers | Destination |
|---|---|---:|---|---|---|---|
| data_sources/examples/fantasy_prices_template.csv | .csv | 59 | 1 data rows | source-controlled example | documentation; tests | none |
| data_sources/examples/fixtures_template.csv | .csv | 15 | 0 data rows | source-controlled example | documentation; tests | none |
| data_sources/examples/player_stats_import_template.csv | .csv | 68 | 1 data rows | source-controlled example | documentation; tests | none |
| data_sources/examples/players_template.csv | .csv | 83 | 0 data rows | source-controlled example | documentation; tests | none |
| examples/fantasy_prices_template.csv | .csv | 59 | 1 data rows | source-controlled example | documentation; tests | none |
| examples/fixtures_template.csv | .csv | 15 | 0 data rows | source-controlled example | documentation; tests | none |
| examples/player_stats_import_template.csv | .csv | 68 | 1 data rows | source-controlled example | documentation; tests | none |
| examples/players_template.csv | .csv | 83 | 0 data rows | source-controlled example | documentation; tests | none |
| fixture_snapshot_v32.example.json | .json | 396 | 1 top-level entries | source-controlled example | documentation; tests | none |
| historical_data/club_id_mapping_candidates.json | .json | 2097 | 2 top-level entries | reference/cache | club metadata; fixture validation | teams / identity mappings / source_payloads |
| historical_data/club_metadata.json | .json | 2714 | 18 top-level entries | reference/cache | club metadata; fixture validation | teams / identity mappings / source_payloads |
| historical_data/direct_risk_gw10.json | .json | 23953 | 11 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/download_report.json | .json | 120 | 4 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/experimental_phase15/ridge_combined.json | .json | 16312 | 12 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/experimental_phase15/ridge_official.json | .json | 7322 | 12 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/fixtures_reconstructed_gw5_gw9.json | .json | 8482 | 3 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| historical_data/next_week_gw10.json | .json | 12830 | 26 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| historical_data/next_week_gw9.json | .json | 11246 | 25 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| historical_data/player_10.json | .json | 4937 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_100.json | .json | 4086 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1009.json | .json | 4667 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_101.json | .json | 4085 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_102.json | .json | 4378 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_103.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_104.json | .json | 5380 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1042.json | .json | 3643 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_106.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_107.json | .json | 4099 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1075.json | .json | 4073 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_108.json | .json | 5060 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_109.json | .json | 4440 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_11.json | .json | 5219 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_110.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1108.json | .json | 4138 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1109.json | .json | 4326 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_111.json | .json | 5101 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_112.json | .json | 4521 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_113.json | .json | 5150 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_114.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1141.json | .json | 3853 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_116.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_117.json | .json | 4987 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1174.json | .json | 3452 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_118.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_119.json | .json | 4910 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_12.json | .json | 6129 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_120.json | .json | 5413 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1207.json | .json | 3595 | 7 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1208.json | .json | 3922 | 7 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1209.json | .json | 3500 | 7 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_121.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_122.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_124.json | .json | 4166 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1240.json | .json | 3312 | 7 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_125.json | .json | 4974 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_126.json | .json | 4833 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_127.json | .json | 4357 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_128.json | .json | 4178 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_130.json | .json | 5863 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1306.json | .json | 4009 | 7 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1307.json | .json | 3915 | 7 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_131.json | .json | 5419 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_132.json | .json | 4931 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_134.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_135.json | .json | 5113 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_136.json | .json | 5918 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_137.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1372.json | .json | 3187 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1373.json | .json | 2975 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_139.json | .json | 5371 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_14.json | .json | 5119 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_140.json | .json | 4193 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1405.json | .json | 3178 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1406.json | .json | 3455 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_141.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_142.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_143.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1438.json | .json | 2610 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_144.json | .json | 4978 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_145.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1471.json | .json | 3590 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_148.json | .json | 5679 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_149.json | .json | 5355 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_15.json | .json | 5426 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_150.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1504.json | .json | 2978 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_151.json | .json | 5612 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_152.json | .json | 5371 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_153.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1537.json | .json | 3182 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1538.json | .json | 2942 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1539.json | .json | 3239 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_154.json | .json | 4552 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1540.json | .json | 2606 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1541.json | .json | 2589 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1542.json | .json | 3304 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1543.json | .json | 3423 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1544.json | .json | 3081 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1545.json | .json | 3390 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1546.json | .json | 2600 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1547.json | .json | 2594 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_155.json | .json | 4574 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_156.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_157.json | .json | 5340 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1570.json | .json | 2600 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1571.json | .json | 2687 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1572.json | .json | 2590 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1573.json | .json | 3226 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_159.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_16.json | .json | 4187 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_160.json | .json | 3906 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_1603.json | .json | 3079 | 6 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_161.json | .json | 5971 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_162.json | .json | 5602 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_163.json | .json | 4478 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_165.json | .json | 4077 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_166.json | .json | 6042 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_167.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_168.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_169.json | .json | 5453 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_17.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_170.json | .json | 5517 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_171.json | .json | 5400 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_172.json | .json | 5956 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_173.json | .json | 4133 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_174.json | .json | 4920 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_175.json | .json | 4652 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_176.json | .json | 5807 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_177.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_178.json | .json | 5689 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_179.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_18.json | .json | 4737 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_180.json | .json | 5501 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_181.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_182.json | .json | 5480 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_184.json | .json | 4382 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_185.json | .json | 5146 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_186.json | .json | 5291 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_187.json | .json | 4592 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_188.json | .json | 4321 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_189.json | .json | 4192 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_19.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_190.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_192.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_193.json | .json | 5422 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_194.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_195.json | .json | 6111 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_196.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_197.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_198.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_199.json | .json | 5655 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_2.json | .json | 4340 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_20.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_200.json | .json | 4083 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_201.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_202.json | .json | 5458 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_204.json | .json | 4095 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_205.json | .json | 5659 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_206.json | .json | 4823 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_207.json | .json | 4585 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_208.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_209.json | .json | 4088 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_21.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_210.json | .json | 4938 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_211.json | .json | 4956 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_212.json | .json | 5678 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_213.json | .json | 5160 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_214.json | .json | 5092 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_215.json | .json | 4806 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_216.json | .json | 5654 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_217.json | .json | 5248 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_218.json | .json | 4004 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_219.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_22.json | .json | 6223 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_220.json | .json | 5273 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_221.json | .json | 5330 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_222.json | .json | 5207 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_225.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_226.json | .json | 4341 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_228.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_229.json | .json | 4761 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_23.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_230.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_231.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_232.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_234.json | .json | 5724 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_235.json | .json | 5672 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_236.json | .json | 4186 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_237.json | .json | 5316 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_239.json | .json | 5157 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_240.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_241.json | .json | 4347 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_242.json | .json | 4267 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_243.json | .json | 4193 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_244.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_246.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_247.json | .json | 5421 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_248.json | .json | 4900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_249.json | .json | 4891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_25.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_250.json | .json | 4285 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_252.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_253.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_254.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_255.json | .json | 3885 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_257.json | .json | 4097 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_258.json | .json | 4188 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_259.json | .json | 5338 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_26.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_260.json | .json | 4344 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_261.json | .json | 5508 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_262.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_263.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_264.json | .json | 5245 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_266.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_267.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_268.json | .json | 3994 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_269.json | .json | 4756 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_27.json | .json | 5461 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_270.json | .json | 4704 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_271.json | .json | 4700 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_272.json | .json | 4479 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_273.json | .json | 5481 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_274.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_275.json | .json | 4813 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_277.json | .json | 5483 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_278.json | .json | 5097 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_279.json | .json | 5343 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_28.json | .json | 5204 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_280.json | .json | 5660 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_281.json | .json | 5371 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_282.json | .json | 5231 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_283.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_284.json | .json | 3890 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_285.json | .json | 5051 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_286.json | .json | 4252 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_288.json | .json | 5527 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_289.json | .json | 5146 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_29.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_290.json | .json | 4606 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_291.json | .json | 5428 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_292.json | .json | 4985 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_293.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_294.json | .json | 4373 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_295.json | .json | 5538 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_296.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_297.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_298.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_299.json | .json | 5825 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_3.json | .json | 4182 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_30.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_300.json | .json | 5147 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_301.json | .json | 4468 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_302.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_303.json | .json | 4914 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_304.json | .json | 5133 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_305.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_306.json | .json | 4075 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_307.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_308.json | .json | 4945 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_309.json | .json | 5121 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_310.json | .json | 5125 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_311.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_312.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_313.json | .json | 4933 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_314.json | .json | 4901 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_317.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_318.json | .json | 3999 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_319.json | .json | 4881 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_32.json | .json | 4881 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_321.json | .json | 3999 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_322.json | .json | 4174 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_323.json | .json | 4275 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_326.json | .json | 5425 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_327.json | .json | 4101 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_328.json | .json | 3904 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_329.json | .json | 3993 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_33.json | .json | 4380 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_330.json | .json | 5111 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_332.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_335.json | .json | 3995 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_336.json | .json | 5092 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_338.json | .json | 4952 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_339.json | .json | 5383 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_34.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_341.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_342.json | .json | 4975 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_343.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_344.json | .json | 5123 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_345.json | .json | 4949 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_346.json | .json | 5144 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_347.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_348.json | .json | 4332 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_35.json | .json | 4935 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_351.json | .json | 4973 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_352.json | .json | 5330 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_353.json | .json | 5118 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_354.json | .json | 4236 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_355.json | .json | 4936 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_356.json | .json | 5670 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_358.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_359.json | .json | 4686 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_36.json | .json | 4671 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_360.json | .json | 4278 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_362.json | .json | 5873 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_363.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_364.json | .json | 5251 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_365.json | .json | 5531 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_366.json | .json | 4077 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_367.json | .json | 5200 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_37.json | .json | 5587 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_370.json | .json | 4447 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_371.json | .json | 4528 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_372.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_373.json | .json | 4997 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_375.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_376.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_377.json | .json | 4439 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_378.json | .json | 4728 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_379.json | .json | 5433 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_38.json | .json | 4004 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_380.json | .json | 5433 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_381.json | .json | 4840 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_382.json | .json | 4802 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_383.json | .json | 3887 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_384.json | .json | 4820 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_385.json | .json | 4861 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_386.json | .json | 4324 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_387.json | .json | 5076 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_388.json | .json | 5405 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_389.json | .json | 4753 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_390.json | .json | 5385 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_391.json | .json | 4911 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_392.json | .json | 3887 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_393.json | .json | 3887 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_394.json | .json | 4371 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_395.json | .json | 4524 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_396.json | .json | 4742 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_397.json | .json | 4445 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_398.json | .json | 4920 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_399.json | .json | 3887 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_4.json | .json | 5453 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_40.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_400.json | .json | 4889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_401.json | .json | 4372 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_402.json | .json | 5028 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_404.json | .json | 5652 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_406.json | .json | 3887 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_407.json | .json | 5283 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_408.json | .json | 3989 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_409.json | .json | 4544 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_41.json | .json | 5649 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_410.json | .json | 4094 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_411.json | .json | 3887 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_412.json | .json | 4644 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_413.json | .json | 5595 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_414.json | .json | 3882 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_415.json | .json | 4724 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_416.json | .json | 4369 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_417.json | .json | 4671 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_418.json | .json | 3882 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_419.json | .json | 6141 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_42.json | .json | 3987 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_420.json | .json | 4181 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_421.json | .json | 4717 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_423.json | .json | 4423 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_425.json | .json | 4159 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_426.json | .json | 5073 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_427.json | .json | 5732 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_428.json | .json | 4426 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_429.json | .json | 5391 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_43.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_430.json | .json | 4666 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_431.json | .json | 4560 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_434.json | .json | 4171 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_435.json | .json | 5333 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_436.json | .json | 5657 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_437.json | .json | 5005 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_438.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_439.json | .json | 4785 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_44.json | .json | 4648 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_441.json | .json | 4236 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_442.json | .json | 4069 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_443.json | .json | 4643 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_445.json | .json | 4407 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_446.json | .json | 4410 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_447.json | .json | 4197 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_448.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_449.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_45.json | .json | 4645 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_451.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_453.json | .json | 4547 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_454.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_455.json | .json | 4689 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_456.json | .json | 4416 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_457.json | .json | 5664 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_458.json | .json | 3985 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_459.json | .json | 3969 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_46.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_460.json | .json | 4223 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_461.json | .json | 4211 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_462.json | .json | 4791 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_463.json | .json | 4754 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_464.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_466.json | .json | 4741 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_467.json | .json | 5028 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_468.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_47.json | .json | 5590 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_470.json | .json | 5696 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_471.json | .json | 4245 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_472.json | .json | 5530 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_473.json | .json | 3875 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_474.json | .json | 4876 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_475.json | .json | 4919 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_476.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_477.json | .json | 4854 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_478.json | .json | 4283 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_479.json | .json | 4764 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_48.json | .json | 5492 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_481.json | .json | 4846 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_482.json | .json | 5121 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_483.json | .json | 4831 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_484.json | .json | 4373 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_485.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_486.json | .json | 4672 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_487.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_489.json | .json | 4816 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_49.json | .json | 4258 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_491.json | .json | 5002 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_492.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_493.json | .json | 5444 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_495.json | .json | 4789 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_496.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_498.json | .json | 4090 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_5.json | .json | 3895 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_50.json | .json | 3991 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_500.json | .json | 4279 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_501.json | .json | 3992 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_502.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_503.json | .json | 4469 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_504.json | .json | 3987 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_505.json | .json | 5140 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_506.json | .json | 4080 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_507.json | .json | 5502 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_508.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_509.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_51.json | .json | 5501 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_511.json | .json | 5432 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_514.json | .json | 4946 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_515.json | .json | 4382 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_516.json | .json | 5976 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_517.json | .json | 4206 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_52.json | .json | 5242 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_520.json | .json | 5350 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_521.json | .json | 4377 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_522.json | .json | 4007 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_523.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_525.json | .json | 4868 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_527.json | .json | 4102 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_529.json | .json | 5254 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_53.json | .json | 5655 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_530.json | .json | 4105 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_531.json | .json | 5144 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_532.json | .json | 5413 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_533.json | .json | 5744 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_535.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_536.json | .json | 4637 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_537.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_538.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_539.json | .json | 5334 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_54.json | .json | 3992 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_540.json | .json | 3902 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_541.json | .json | 4801 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_542.json | .json | 5669 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_545.json | .json | 4193 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_549.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_550.json | .json | 5697 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_552.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_553.json | .json | 4560 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_554.json | .json | 5901 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_555.json | .json | 4880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_556.json | .json | 4422 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_557.json | .json | 4815 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_559.json | .json | 4836 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_56.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_560.json | .json | 4646 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_561.json | .json | 4911 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_562.json | .json | 4062 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_564.json | .json | 4972 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_565.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_566.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_567.json | .json | 5752 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_568.json | .json | 5062 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_57.json | .json | 4094 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_570.json | .json | 4356 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_571.json | .json | 4291 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_572.json | .json | 5461 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_573.json | .json | 5422 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_575.json | .json | 4087 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_576.json | .json | 4196 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_577.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_578.json | .json | 4871 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_579.json | .json | 3893 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_58.json | .json | 5057 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_580.json | .json | 3976 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_581.json | .json | 3882 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_582.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_583.json | .json | 4746 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_584.json | .json | 3889 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_585.json | .json | 4537 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_586.json | .json | 4424 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_587.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_589.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_59.json | .json | 5142 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_590.json | .json | 4965 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_591.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_592.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_593.json | .json | 5219 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_595.json | .json | 4623 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_596.json | .json | 3882 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_597.json | .json | 5411 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_599.json | .json | 5058 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_6.json | .json | 4102 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_600.json | .json | 5295 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_601.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_607.json | .json | 3882 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_608.json | .json | 5747 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_609.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_610.json | .json | 3891 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_611.json | .json | 5270 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_612.json | .json | 3882 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_613.json | .json | 4961 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_614.json | .json | 3880 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_615.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_617.json | .json | 4462 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_621.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_622.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_623.json | .json | 4458 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_624.json | .json | 4638 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_626.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_627.json | .json | 4202 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_629.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_63.json | .json | 5367 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_632.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_635.json | .json | 4360 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_636.json | .json | 3900 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_64.json | .json | 4254 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_646.json | .json | 3883 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_67.json | .json | 4480 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_679.json | .json | 4681 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_7.json | .json | 3996 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_70.json | .json | 3886 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_71.json | .json | 5140 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_712.json | .json | 3936 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_72.json | .json | 5121 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_73.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_74.json | .json | 4073 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_745.json | .json | 4737 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_746.json | .json | 4944 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_75.json | .json | 5786 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_76.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_77.json | .json | 5196 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_778.json | .json | 4605 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_78.json | .json | 4888 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_80.json | .json | 5786 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_81.json | .json | 5201 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_811.json | .json | 4850 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_812.json | .json | 4540 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_813.json | .json | 3630 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_82.json | .json | 4744 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_83.json | .json | 3987 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_84.json | .json | 5314 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_844.json | .json | 4098 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_85.json | .json | 4377 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_86.json | .json | 4795 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_877.json | .json | 4515 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_88.json | .json | 4768 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_89.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_9.json | .json | 4093 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_90.json | .json | 4406 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_910.json | .json | 3912 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_92.json | .json | 4592 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_93.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_94.json | .json | 5782 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_943.json | .json | 4549 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_95.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_97.json | .json | 5159 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_976.json | .json | 4394 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_977.json | .json | 4059 | 8 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_98.json | .json | 3892 | 9 top-level entries | historical player data | historical backtests; forecast feature builders | player_gameweek_stats / source_payloads |
| historical_data/player_level_phase11/player_level_comparison.csv | .csv | 14603 | 112 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/player_level_phase11/player_level_cumulative.csv | .csv | 1821 | 14 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/player_level_phase11/player_level_report.json | .json | 51378 | 13 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/players.json | .json | 255721 | 572 top-level entries | persistent current player data | Flask /lineup; live_benchmark; official ingestion | players / player_state |
| historical_data/prediction_tracking.capture.lock | .lock | 2 | not counted | temporary lock | prospective_monitor | none |
| historical_data/prediction_tracking.sqlite3 | .sqlite3 | 25092096 | not counted | persistent application data | prediction_tracking; Flask; benchmark; prospective_monitor | snapshots / predictions / evaluation_runs |
| historical_data/production_evaluation.json | .json | 624 | 6 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/recovered/PLAYER_RANKING_README.md | .md | 1414 | not counted | documentation | developers | none |
| historical_data/recovered/README.md | .md | 3950 | not counted | documentation | developers | none |
| historical_data/recovered/coverage_report.json | .json | 9022 | 16 top-level entries | evidence manifest or generated coverage | historical_recovery; Flask benchmark | collection_runs / historical_reports |
| historical_data/recovered/derived/position_evidence_af1004d70a84af17.json | .json | 213948 | 5 top-level entries | derived historical evidence | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/derived/position_evidence_ccdea34fbef84b42.json | .json | 213948 | 5 top-level entries | derived historical evidence | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/derived/position_evidence_f8c662bf7abcd081.json | .json | 38696 | 5 top-level entries | derived historical evidence | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/derived/transfer_events_bd683eab04aea2ba.json | .json | 1585 | 2 top-level entries | derived historical evidence | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/model_cumulative_combined_matched.csv | .csv | 985 | 14 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/recovered/model_cumulative_matched.csv | .csv | 958 | 14 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/recovered/model_evaluation.csv | .csv | 11840 | 112 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/recovered/model_evaluation.json | .json | 82298 | 10 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/recovered/model_evaluation_combined.csv | .csv | 12036 | 112 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/recovered/model_evaluation_combined.json | .json | 82787 | 10 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/recovered/official_collection_manifest.json | .json | 6194 | 5 top-level entries | evidence manifest or generated coverage | historical_recovery; Flask benchmark | collection_runs / historical_reports |
| historical_data/recovered/official_collection_manifest_13c6c910367aec22.json | .json | 5759 | 5 top-level entries | evidence manifest or generated coverage | historical_recovery; Flask benchmark | collection_runs / historical_reports |
| historical_data/recovered/player_ranking_combined.csv | .csv | 3855 | 62 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/recovered/player_ranking_combined.json | .json | 43246 | 9 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/recovered/player_ranking_official.csv | .csv | 3731 | 62 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/recovered/player_ranking_official.json | .json | 43137 | 9 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/recovered/raw/official/clubs_current_0adcf6f91561b723.json | .json | 12781 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw1_a0e2a2ab67c2082f.json | .json | 3885 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw2_7023d2739e0973b0.json | .json | 4530 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw2_91dc0e09d5ddd9f2.json | .json | 4530 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw3_3865365c693dba26.json | .json | 4257 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw4_6a93c056fac8d6ad.json | .json | 4223 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw5_750f4e915f0f51c5.json | .json | 4013 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw6_f6acccd0ef61629d.json | .json | 4454 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw7_f4622c253778aa5c.json | .json | 3947 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw8_23a54a28f2feb7cd.json | .json | 4050 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/dream_team_gw9_d4c7f9c066083503.json | .json | 3941 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/fixtures_current_f1a55af945efd710.json | .json | 65666 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/official/player_stats_current_8bdc8e51d9cd10fc.json | .json | 442856 | 4 top-level entries | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/raw/third_party/oyuncu_veritabani_f1368196.xlsx | .xlsx | 28984 | not counted | immutable historical evidence | historical_recovery; recovered_history; ranking evaluation | source_payloads / collection_runs |
| historical_data/recovered/snapshots/gw1_0f84bf1bc9bca1a2.json | .json | 394681 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw1_b73149e525c9b75c.json | .json | 324419 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw1_c55687e6ba2a7d30.json | .json | 394681 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw2_42dda06fffa484b7.json | .json | 407968 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw2_b1b67a03fe240eda.json | .json | 339307 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw2_ef21e57e0edca347.json | .json | 407968 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw3_955fcc639f3665d1.json | .json | 344496 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw3_d907de77b4019380.json | .json | 412089 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw3_dfcd03b3e2042c8f.json | .json | 412089 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw4_4ac3bcd09b2fcd99.json | .json | 359954 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw4_9e4d65f1a03a610b.json | .json | 426302 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw4_d21a662faffd9024.json | .json | 426302 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw5_4b07c56639812f28.json | .json | 427404 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw5_876a6c1914743790.json | .json | 427404 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw5_cfaeb5fca9e3265e.json | .json | 362123 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw6_5bc7a3c0015a2f6b.json | .json | 363474 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw6_6d94123face2d5f4.json | .json | 427687 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw6_7eae19af6163420e.json | .json | 427687 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw7_1a2ad73884fd1faf.json | .json | 375561 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw7_2cc815f5a6a47d92.json | .json | 438885 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw7_fe3d72da720d55ad.json | .json | 438885 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw8_34a0699a069eab04.json | .json | 439632 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw8_e11805c3fcdc1249.json | .json | 439632 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw8_fcf0e01a1d1381bd.json | .json | 376841 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw9_77d12f871a55f148.json | .json | 439835 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw9_7c32a2c0aa7cdb8d.json | .json | 439835 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/recovered/snapshots/gw9_82cd82838f21e149.json | .json | 377756 | 9 top-level entries | retrospective reconstruction | historical_recovery; historical evaluation | source_payloads / player_state |
| historical_data/team_of_week_verified.json | .json | 17394 | 5 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/tff_fixtures_verified_v5.json | .json | 77554 | 7 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| historical_data/v33_audit/audit.json | .json | 5183 | 6 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/v33_audit/paired_ablation.csv | .csv | 863 | 16 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/walkforward_backtest_v34.csv | .csv | 397 | 4 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/walkforward_backtest_v34.json | .json | 62267 | 8 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/walkforward_backtest_v35.csv | .csv | 511 | 4 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/walkforward_backtest_v35.json | .json | 68552 | 8 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/walkforward_backtest_v36.csv | .csv | 562 | 4 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/walkforward_backtest_v36.json | .json | 63663 | 10 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/walkforward_phase10/comparison.csv | .csv | 9239 | 81 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| historical_data/walkforward_phase10/comparison.json | .json | 25923 | 10 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| historical_data/walkforward_phase10/cumulative.csv | .csv | 422 | 9 data rows | historical evidence or generated export | historical evaluation; exports | historical_reports / source_payloads |
| tff_club_mapping_discovery.json | .json | 1676 | 6 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| tff_club_mapping_v2.json | .json | 1077 | 7 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
| tff_fixture_diagnostic_v4.json | .json | 184742 | 4 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| tff_fixture_ids_gw5_gw9.json | .json | 665 | 6 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| tff_fixture_matches_capture.json | .json | 660 | 5 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| tff_fixtures_verified_v5.json | .json | 77554 | 7 top-level entries | fixture evidence or generated lineup | Flask; dashboard; fixture ingestion | fixtures / historical_reports / predictions |
| tff_team_of_week_api_discovery.json | .json | 28863 | 3 top-level entries | generated report or reference data | Flask benchmark; analysis scripts | historical_reports / source_payloads |
