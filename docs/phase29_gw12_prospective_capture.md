# Phase 29 — GW12 final prospective capture

**Status:** six-model append-only batch captured before the official deadline, replayed offline, and bound to a third-party signed timestamp. The tracking database retains its conservative `locally_recorded_pre_deadline_not_verified` status; the separate RFC 3161 receipt provides independently checkable proof of artifact existence before the deadline.

## Deadline and source checks

- Official GW12 deadline: **2026-11-21T09:30:00Z**; snapshot created **2026-11-09T10:57:00.473909+00:00**; [FreeTSA](https://freetsa.org/index_en.php) signed timestamp: **2026-11-09 10:57:56 UTC**.
- Official fixtures observed **2026-11-09T10:54:40.195030+00:00**: 9 scheduled fixtures, none started. GW11 official feed marked all fixtures finished and all points and bonuses added.
- Current official player feed observed **2026-11-09T10:54:41.988809+00:00**: 573 players, valid positive prices and current availability fields. Fixtures and player pool passed the repository quality checks without warnings.
- Official histories retrieved **2026-11-09T10:56:38.469663+00:00**: 573/573 GW11 rows, zero request failures, no GW12 rows in inputs. Freshness status **fresh**.
- Frozen Football-Data evidence: 81 match rows, digest `eeb973aae8711c8f51a68dac5a6476f7d749efa4881ff5e7d667d84ef4a9bab9`. The archive was imported 2026-10-31 16:20:08 UTC, and its latest match date is 2026-10-26. All 18 fixture clubs have features, and the 81 rows have xG values. **GW10–GW11 external matches are missing**, so xG features lag current official history. The query admits only completed matches dated before capture from imports recorded before capture.

## Immutable capture identifiers

- New snapshot ID: `914af52a-997c-4b32-84b9-41e1be804637`
- Six-model batch ID: `6753db4b00a70e77fdc9f40b4ede059a54c59890cbbb58922bbf53711b5d7ee9`
- Frozen replay input hash: `e31896eccfa96f9acb521bcbf1b1f22552ed59d984222135f6a1743bd06ef936`
- Stored snapshot payload hash: `88e79718ec34d779330c9d25e908b99ebfb42cc3997865ffcaac87bb0fc34ab4`
- Original GW12 snapshot preserved: `ceddd5ae-a154-411b-9581-31a484c87f5f`
- Model configuration: 0.5 fixture weight, 0.20 captain risk, 0.15 extra minutes-risk adjustment, balanced optimizer profile, unchanged 0.25 eligibility threshold and 100 budget. Uniform and position-aware xG use the frozen 0.4 adjustment; rest-days control has zero rest weight.

## Six saved predictions

| Model | Prediction ID | Formation | Captain | Cost | Fantasy xPts | Risk objective | Osimhen XI | Replay |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| baseline_5w | `501369a1-e15d-47ae-a036-424ac2fb90e4` | 3-4-3 | Mohamed Salah Hamed Mahrous Ghaly | 93.5 | 76.08 | 75.9839 | no | pass |
| short_form_3w | `0d5f44e8-dbbb-49a5-83f3-d5f5ac299178` | 3-5-2 | Mohamed Salah Hamed Mahrous Ghaly | 93.5 | 77.88 | 77.7945 | no | pass |
| stable_8w | `26557cb6-aa63-4a7b-a260-89a76123a4f9` | 3-4-3 | Mohamed Salah Hamed Mahrous Ghaly | 90.5 | 74.38 | 74.2209 | no | pass |
| uniform_xg | `e8d9d8c8-2b74-4b69-918e-875579573d5a` | 3-5-2 | Mohamed Salah Hamed Mahrous Ghaly | 94.5 | 83.53 | 83.4147 | no | pass |
| position_aware_xg | `d94c0c6d-77fd-4684-982f-e6a03217aea6` | 3-5-2 | Mohamed Salah Hamed Mahrous Ghaly | 93.5 | 82.89 | 82.7869 | no | pass |
| rest_days_control | `107f2e01-cee1-460b-803a-a89c73e2747a` | 3-5-2 | Mohamed Salah Hamed Mahrous Ghaly | 93.5 | 77.88 | 77.7945 | no | pass |

Objectives are comparable only within a model configuration; they are not accuracy measures. The saved batch contains the full player objects and projections in [phase29_gw12_capture.json](phase29_gw12_capture.json).

## Starting XI and bench

### baseline_5w

XI: Serhat Öztaşdelen (130), Claudio Winck Neto (94), Wagner Fabricio Cardoso de Pina (28), Stefan Savic (27), Mohamed Salah Hamed Mahrous Ghaly (12), Leandro Trossard (273), Diaa Sabi'a (136), Berkan İsmail Kutlu (212), Gift Emmanuel Orban (148), Dusan Vlahovic (593), Adrian Dawid Benedyczak (75).

Bench: Ederson Santana de Moraes (166), Adem Arous (84), Rıdvan Yılmaz (259), Aleksey Batrakov (877).

### short_form_3w

XI: Serhat Öztaşdelen (130), Wagner Fabricio Cardoso de Pina (28), Claudio Winck Neto (94), Stefan Savic (27), Leandro Trossard (273), Mohamed Salah Hamed Mahrous Ghaly (12), Diaa Sabi'a (136), Aleksey Batrakov (877), Berkan İsmail Kutlu (212), Gift Emmanuel Orban (148), Dusan Vlahovic (593).

Bench: Ederson Santana de Moraes (166), Rıdvan Yılmaz (259), Adem Arous (84), Adrian Dawid Benedyczak (75).

### stable_8w

XI: Andre Onana Onana (22), Claudio Winck Neto (94), Wagner Fabricio Cardoso de Pina (28), Guram Giorbelidze (48), Mohamed Salah Hamed Mahrous Ghaly (12), Diaa Sabi'a (136), Berkan İsmail Kutlu (212), Alexandros Kyziridis (608), Gift Emmanuel Orban (148), Eldor Shomurodov (404), Adrian Dawid Benedyczak (75).

Bench: Ederson Santana de Moraes (166), Milan Skriniar (172), Michael Amir Murillo Bermudez (277), Leandro Trossard (273).

### uniform_xg

XI: Ederson Santana de Moraes (166), Wagner Fabricio Cardoso de Pina (28), Stefan Savic (27), Claudio Winck Neto (94), Mohamed Salah Hamed Mahrous Ghaly (12), Leandro Trossard (273), Aleksey Batrakov (877), Diaa Sabi'a (136), Oğuz Aydın (178), Gift Emmanuel Orban (148), Dusan Vlahovic (593).

Bench: Serhat Öztaşdelen (130), Rıdvan Yılmaz (259), Adem Arous (84), Adrian Dawid Benedyczak (75).

### position_aware_xg

XI: Andreas Gianniotis (80), Wagner Fabricio Cardoso de Pina (28), Claudio Winck Neto (94), Stefan Savic (27), Mohamed Salah Hamed Mahrous Ghaly (12), Leandro Trossard (273), Aleksey Batrakov (877), Diaa Sabi'a (136), Berkan İsmail Kutlu (212), Gift Emmanuel Orban (148), Dusan Vlahovic (593).

Bench: Ederson Santana de Moraes (166), Rıdvan Yılmaz (259), Adem Arous (84), Jesus Andres Ramirez Diaz (237).

### rest_days_control

XI: Serhat Öztaşdelen (130), Wagner Fabricio Cardoso de Pina (28), Claudio Winck Neto (94), Stefan Savic (27), Leandro Trossard (273), Mohamed Salah Hamed Mahrous Ghaly (12), Diaa Sabi'a (136), Aleksey Batrakov (877), Berkan İsmail Kutlu (212), Gift Emmanuel Orban (148), Dusan Vlahovic (593).

Bench: Ederson Santana de Moraes (166), Rıdvan Yılmaz (259), Adem Arous (84), Adrian Dawid Benedyczak (75).

## Data-update sensitivity versus the original GW9-history batch

The original and new batches differ in historical weeks **and** observation time for current player prices, availability, and fixtures. The Football-Data archive is the same 81-match source, but the new snapshot is a fresh capture. This is a data-update sensitivity analysis, not an isolated causal estimate for GW10–GW11 and not an accuracy evaluation.

| Model | XI overlap | XI entered | XI left | Captain change | Formation | Cost old → new |
| --- | ---: | --- | --- | --- | --- | ---: |
| baseline_5w | 5/11 | 27, 28, 94, 130, 273, 593 | 37, 48, 53, 216, 404, 608 | Mohamed Salah Hamed Mahrous Ghaly (12) → Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 → 3-4-3 | 85.0 → 93.5 |
| short_form_3w | 5/11 | 27, 28, 130, 273, 593, 877 | 4, 48, 75, 216, 217, 1471 | Diaa Sabi'a (136) → Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 → 3-5-2 | 88.5 → 93.5 |
| stable_8w | 9/11 | 28, 608 | 37, 567 | Mohamed Salah Hamed Mahrous Ghaly (12) → Mohamed Salah Hamed Mahrous Ghaly | 4-3-3 → 3-4-3 | 91.5 → 90.5 |
| uniform_xg | 4/11 | 27, 28, 166, 178, 273, 593, 877 | 4, 48, 75, 212, 216, 217, 1471 | Mohamed Salah Hamed Mahrous Ghaly (12) → Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 → 3-5-2 | 87.5 → 94.5 |
| position_aware_xg | 5/11 | 27, 28, 80, 273, 593, 877 | 4, 48, 75, 216, 217, 1471 | Mohamed Salah Hamed Mahrous Ghaly (12) → Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 → 3-5-2 | 90.0 → 93.5 |
| rest_days_control | 5/11 | 27, 28, 130, 273, 593, 877 | 4, 48, 75, 216, 217, 1471 | Diaa Sabi'a (136) → Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 → 3-5-2 | 88.5 → 93.5 |

Osimhen (507) is absent from every new XI. He was also absent from every original XI. This is optimizer selection, not an eligibility finding.

Largest changes among players selected in the new squad and present in the old projection pool (new xPts minus original xPts):

| Model | Largest selected-player changes |
| --- | --- |
| baseline_5w | Leandro Trossard (273) +4.058; Aleksey Batrakov (877) +3.319; Dusan Vlahovic (593) +2.567 |
| short_form_3w | Leandro Trossard (273) +4.587; Wagner Fabricio Cardoso de Pina (28) +3.099; Aleksey Batrakov (877) +2.870 |
| stable_8w | Wagner Fabricio Cardoso de Pina (28) +2.119; Leandro Trossard (273) +1.802; Alexandros Kyziridis (608) +1.200 |
| uniform_xg | Leandro Trossard (273) +4.686; Wagner Fabricio Cardoso de Pina (28) +3.560; Aleksey Batrakov (877) +3.301 |
| position_aware_xg | Leandro Trossard (273) +4.609; Wagner Fabricio Cardoso de Pina (28) +3.538; Aleksey Batrakov (877) +3.217 |
| rest_days_control | Leandro Trossard (273) +4.587; Wagner Fabricio Cardoso de Pina (28) +3.099; Aleksey Batrakov (877) +2.870 |

## Independent timestamp and replay integrity

FreeTSA issued [an RFC 3161 response](phase29_capture.tsr) for the SHA-256 digest of [the capture artifact](phase29_gw12_capture.json): `1f582c935c617c409278799f24f4ab30d5fc785fa316a66e234aff0e757b3c91`. The signed token reports `20261109105756Z`, and its message imprint exactly matches the artifact bytes. The embedded signer certificate matches [FreeTSA’s published TSA certificate](phase29_freetsa_tsa.crt), whose file SHA-256 matches the fingerprint published on its [site](https://freetsa.org/index_en.php). Full certificate-chain and request verification with `openssl ts -verify -in docs/phase29_capture.tsr -queryfile docs/phase29_capture.tsq -CAfile docs/phase29_freetsa_ca.pem -untrusted docs/phase29_freetsa_tsa.crt` returned **Verification: OK**. The [request](phase29_capture.tsq), [response](phase29_capture.tsr), [signed token](phase29_capture_token.p7s), and [CA certificate](phase29_freetsa_ca.pem) are retained.

The offline replay loaded the stored snapshot, rebuilt all six variants, and matched each saved XI, bench, captain, formation, fantasy xPts, cost, and objective. The original snapshot payload hash was checked unchanged. Generated timestamps and player ordering outside lineup membership are not claimed byte-identical.

## Tests and limits

Focused tests for the six-model batch, capture integrity, history freshness and experimental adjustments passed **12/12**. A signed timestamp proves the capture artifact existed before the deadline; it does not independently prove the earlier source APIs contained these exact values at their locally logged retrieval times. The official deadline came from the official fixture API, and source observations remain local timestamps. The xG archive lacks GW10–GW11 matches. No production weights, optimizer rules, original prediction, or original snapshot were changed. No commit or push was made.
