# Phase 35 — player availability and expected-minutes audit

**Classification:** approximate retrospective GW6–11 evaluation. The six Phase 32 GW11 squads and saved prospective predictions remain unchanged.

## Current implementation

`participation()` uses the last four available rows: 0.65 × played-match share + 0.35 × min(1, mean minutes / 75), clamped to 0.05–1.00. A player enters the new-lineup candidate pool at 0.25. This is a heuristic score, **not a calibrated probability**. It reports recent average minutes and starts rate, but the production lineup model does not emit an explicit expected-minutes forecast or a separate zero-minute probability. `project()` multiplies form by min(1, recent mean minutes / 85), so recent minutes already affect xPts. The official status gate excludes blocked labels and discounts doubtful ones; historical deadline-time statuses were not archived.

The dashboard has a separate expected-minutes blend in `production_scoring.py`; it is not the six lineup models. No stored per-player minute forecast exists for those models, so expected-minutes MAE cannot be validly reported. Last-four mean minutes are a descriptive proxy, not a forecast. The `started` history field enters the audit but not the lineup eligibility formula.

## Historical participation metrics

3432 player-weeks across GW6–11, drawn from 572 current archived IDs. Actual participation is minutes > 0. Threshold 0.50 measures classifier performance; the 0.25 row measures the actual eligibility gate. Brier scores are descriptive because neither score was trained/calibrated as a probability.

| GW | Proxy accuracy | Proxy FP / FN | Proxy Brier | Alt accuracy | Alt FP / FN | Gate FP / FN |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 0.836 | 43 / 51 | 0.115 | 0.841 | 65 / 26 | 71 / 24 |
| 7 | 0.834 | 39 / 56 | 0.120 | 0.836 | 61 / 33 | 67 / 31 |
| 8 | 0.830 | 38 / 59 | 0.118 | 0.864 | 53 / 25 | 56 / 24 |
| 9 | 0.844 | 39 / 50 | 0.105 | 0.871 | 53 / 21 | 60 / 21 |
| 10 | 0.816 | 45 / 60 | 0.144 | 0.815 | 68 / 38 | 70 / 37 |
| 11 | 0.815 | 50 / 56 | 0.130 | 0.825 | 67 / 33 | 69 / 27 |

Across all weeks: proxy Brier 0.122, accuracy 0.829; fixed Laplace-smoothed last-four appearance frequency Brier 0.123, accuracy 0.842. This alternative is an untrained experimental benchmark, never integrated into production. Calibration-bin counts and observed rates are in JSON.

## Fantasy errors by realized minutes

| Minutes category | N | Mean predicted xPts | Mean actual | MAE |
| --- | ---: | ---: | ---: | ---: |
| zero | 1729 | 0.311 | 0.000 | 0.311 |
| under60 | 620 | 0.953 | 1.285 | 1.188 |
| 60plus | 1083 | 2.472 | 3.722 | 2.785 |

**Osimhen GW11:** prior minutes [13, 90, 88, 61]; proxy 0.944, 0.25 gate passed; unadjusted baseline form xPts 3.647; actual 0 minutes and 0 points. This unadjusted historical projection is not the Phase 32 fixture-adjusted lineup xPts. His GW11 absence is verified, but no timestamped pre-deadline injury, rotation or lineup notice was preserved, so its predictability is unknown.

### GW11 highest projected zero-minute players

| Player | xPts | Proxy | Prior four minutes | Actual minutes |
| --- | ---: | ---: | --- | ---: |
| Samuel Leo Beat Ballet (600) | 5.796 | 1.000 | [90, 90, 85, 90] | 0 |
| Victor James Osimhen (507) | 3.647 | 0.944 | [13, 90, 88, 61] | 0 |
| Franculino Gluda Dju (1471) | 3.395 | 0.778 | [71, 88, 90, 0] | 0 |
| Muhammed Şengezer (380) | 3.364 | 1.000 | [90, 90, 90, 90] | 0 |
| Deniz Türüç (205) | 3.157 | 1.000 | [90, 74, 84, 90] | 0 |
| Saba Kharebashvili (391) | 3.022 | 0.986 | [63, 45, 90, 90] | 0 |
| Abdülkerim Bardakcı (533) | 2.778 | 0.787 | [77, 90, 90, 0] | 0 |
| Gaïus Abraham Jered Makouta (435) | 2.596 | 0.977 | [90, 90, 45, 55] | 0 |
| Gökhan Sazdağı (235) | 2.590 | 1.000 | [73, 90, 90, 87] | 0 |
| Jonatan Noah Kemeseng Sonko Sundberg (301) | 2.399 | 1.000 | [90, 90, 90, 90] | 0 |

GW11 players below the 0.25 gate who nevertheless played 60+ minutes: 9 (top 20 retained in JSON). These are retrospective false exclusions; historical availability and eligibility at the deadline are unknown.

## Free-source evidence and limitations

| Source | Actual Turkish-league evidence | Timestamp / historical limit | Use |
| --- | --- | --- | --- |
| Official TFF Fantasy history and status | 573 GW11 player rows and live statuses observed in prior project audits | Histories retrieved after GW11; status has no archived deadline-time revisions | Minutes, starts, suspensions/status when timestamped prospectively |
| [TFF discipline decisions](https://www.tff.org/Default.aspx?pageID=238) | Public dated 2026 Süper Lig decisions are visible | Publication dates exist; player-ID linking and effective ban dates need validation | Prospective suspension flags only after publication |
| [Official TFF Fantasy rules](https://tfffantezilig.com/yardim) | League-specific lineup/auto-sub rules verified | Rules page is current, not historical lineup feed | Scoring and replacement eligibility |
| Club announcements / official match lineups | No measured 2026–27 coverage in this audit | Timing relative to fantasy deadline unverified | Research-only until a dated, licensed source and ID matching are validated |
No free source in this audit has verified historical pre-deadline injury, expected-minutes or lineup coverage for the full 573-player population. No paid API or unauthorized scraping was used. Public pages were inspected read-only; automated reuse terms were not established.

## Recommended next steps

1. Persist official player status, timestamped club notices and the current candidate pool before each deadline. Validate effective suspension dates and player-ID matches.
2. Save an explicit expected-minutes and zero-minute estimate with each future prediction, then calibrate them on genuinely prospective weeks.
3. Backtest any experimental appearance model across more weeks and with deadline-time status evidence before replacing the current gate. The simple Laplace benchmark here is diagnostic, not a production recommendation.
4. Separate injury, suspension, rest and tactical rotation only when a timestamped pre-deadline source identifies the reason. Do not infer a known absence from postmatch zero minutes.

## Data quality

Player histories were obtained after the evaluated weeks; publication timing and later corrections are unknown. Historical prices, clubs and availability are not point-in-time verified. Metrics use lagged numerical histories only and current archived identity labels. No model weights, frozen snapshots or saved predictions changed.
