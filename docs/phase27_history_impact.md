# Phase 27 — GW10 history impact

**Classification:** retrospective sensitivity experiment; refreshed histories were observed after the frozen GW12 capture. This is not a verified pre-deadline forecast.

## Access and integrity

The earlier PostgreSQL timeout was transient: the project Docker database is now healthy on 127.0.0.1:5433, the port is reachable, and the configured credentials connect. The frozen snapshot exists in the expected database. No database reset or record update was made.

Snapshot `ceddd5ae-a154-411b-9581-31a484c87f5f` passed the frozen input hash check (`8029bd1b4525fd5fe5fb9835bfea1ea8e7a274289604afc3f188dfa62b87aa1d`). All six GW9 replays exactly match saved XI, bench, captain, fantasy xPts, and objective. The same 573 frozen players, prices, availability, fixtures, football-data evidence, risk settings, and optimizer constraints were used in both scenarios. The refreshed scenario appends exactly one official GW10 row per player to the original history. GW11 and GW12 are excluded. Official rows were retrieved at `2026-11-09T09:59:22.453463+00:00` with zero request failures.

The earlier Phase 26B dry run reported 318 eligible players because it used the entire refreshed history response. That response included seven additional pre-GW10 rows. Under the strict GW10-only intervention here, eligibility is **314 → 319**: 17 enter and 12 leave. Thus 314 → 318 cannot be explained as GW10 alone; it also reflects older missing-row recovery. The extra eligible player in the strict scenario is Mervan Müjdeci (1273), whose frozen history is empty and whose single GW10 minute gives a 0.655 participation proxy. The full refreshed response adds earlier rows and changes his proxy and eligibility.

## Six-model comparison

| Model | Eligible | XI overlap | Captain GW9 → GW10 | Formation GW9 → GW10 | Cost GW9 → GW10 | Fantasy xPts GW9 → GW10 | Objective GW9 → GW10 |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| baseline_5w | 314 → 319 | 7/11 | Mohamed Salah Hamed Mahrous Ghaly (12) → Mohamed Salah Hamed Mahrous Ghaly (12) | 3-4-3 → 3-4-3 | 85.0 → 84.5 | 75.73 → 72.62 | 75.2252 → 72.2022 |
| short_form_3w | 314 → 319 | 4/11 | Diaa Sabi'a (136) → Ernest Muçi (4) | 3-4-3 → 3-4-3 | 88.5 → 90.0 | 73.93 → 74.41 | 73.9714 → 74.1378 |
| stable_8w | 314 → 319 | 10/11 | Mohamed Salah Hamed Mahrous Ghaly (12) → Mohamed Salah Hamed Mahrous Ghaly (12) | 4-3-3 → 3-4-3 | 91.5 → 87.0 | 72.55 → 71.58 | 71.9428 → 71.0483 |
| uniform_xg | 314 → 319 | 4/11 | Mohamed Salah Hamed Mahrous Ghaly (12) → Ernest Muçi (4) | 3-4-3 → 3-4-3 | 87.5 → 91.0 | 76.72 → 81.29 | 76.2407 → 80.9450 |
| position_aware_xg | 314 → 319 | 4/11 | Mohamed Salah Hamed Mahrous Ghaly (12) → Ernest Muçi (4) | 3-4-3 → 3-4-3 | 90.0 → 91.5 | 77.42 → 80.87 | 76.9593 → 80.5443 |
| rest_days_control | 314 → 319 | 4/11 | Diaa Sabi'a (136) → Ernest Muçi (4) | 3-4-3 → 3-4-3 | 88.5 → 90.0 | 73.93 → 74.41 | 73.9714 → 74.1378 |

Objectives are comparable only within each row. They are model scores, not observed outcomes.

## Squad and prediction sensitivity

### baseline_5w

XI in: Andre Onana Onana (22), Stefan Savic (27), Claudio Winck Neto (94), Franco Daryl Tongya Heubang (346). XI out: Chibuike Godfrey Nwaiwu (37), Amar Gerxhaliu (53), Bahadır Han Güngördü (216), Alexandros Kyziridis (608).

Bench in: Amar Gerxhaliu (53), Ederson Santana de Moraes (166), Davinson Sanchez Mina (516). Bench out: Andre Onana Onana (22), Claudio Winck Neto (94), Abdülkerim Bardakcı (533).

Largest common-player xPts changes: Franco Daryl Tongya Heubang (346) +2.746, Stefan Savic (27) +2.128, Abdülkerim Bardakcı (533) -2.095, Tiago Maria Antunes Gouveia (812) +2.024, Bahadır Han Güngördü (216) -1.829.

### short_form_3w

XI in: Andre Onana Onana (22), Stefan Savic (27), Adem Arous (84), Franco Daryl Tongya Heubang (346), Eldor Shomurodov (404), Victor James Osimhen (507), Aleksey Batrakov (877). XI out: Mohamed Salah Hamed Mahrous Ghaly (12), Guram Giorbelidze (48), Adrian Dawid Benedyczak (75), Berkan İsmail Kutlu (212), Bahadır Han Güngördü (216), Chidozie Collins Awaziem (217), Franculino Gluda Dju (1471).

Bench in: Guram Giorbelidze (48), Cengiz Ünder (193), İrfan Can Eğribayat (195). Bench out: Amar Gerxhaliu (53), Ederson Santana de Moraes (166), Miguel Felipe Nunes Cardoso (746).

Largest common-player xPts changes: Franco Daryl Tongya Heubang (346) +3.617, Franculino Gluda Dju (1471) -3.196, Stefan Savic (27) +2.661, Bahadır Han Güngördü (216) -2.472, Abdülkerim Bardakcı (533) -2.466.

### stable_8w

XI in: Alexandros Kyziridis (608). XI out: Deian Cristian Sorescu (567).

Bench in: Cengiz Ünder (193), Davinson Sanchez Mina (516). Bench out: Mason Will John Greenwood (176), Alexandros Kyziridis (608).

Largest common-player xPts changes: Tiago Maria Antunes Gouveia (812) +1.361, Franculino Gluda Dju (1471) -1.347, Franco Daryl Tongya Heubang (346) +1.332, Abdülkerim Bardakcı (533) -1.330, Mason Will John Greenwood (176) -1.328.

### uniform_xg

XI in: Andre Onana Onana (22), Stefan Savic (27), Franco Daryl Tongya Heubang (346), Eldor Shomurodov (404), Victor James Osimhen (507), Davinson Sanchez Mina (516), Aleksey Batrakov (877). XI out: Mohamed Salah Hamed Mahrous Ghaly (12), Guram Giorbelidze (48), Adrian Dawid Benedyczak (75), Berkan İsmail Kutlu (212), Bahadır Han Güngördü (216), Chidozie Collins Awaziem (217), Franculino Gluda Dju (1471).

Bench in: Adem Arous (84), Cengiz Ünder (193), İrfan Can Eğribayat (195), Michael Amir Murillo Bermudez (277). Bench out: Amar Gerxhaliu (53), Ederson Santana de Moraes (166), Alexis Antunes Gomez (289), Davinson Sanchez Mina (516).

Largest common-player xPts changes: Franculino Gluda Dju (1471) -3.672, Franco Daryl Tongya Heubang (346) +3.486, Stefan Savic (27) +3.057, Abdülkerim Bardakcı (533) -2.835, Barış Alper Yılmaz (520) -2.618.

### position_aware_xg

XI in: Andre Onana Onana (22), Stefan Savic (27), Franco Daryl Tongya Heubang (346), Eldor Shomurodov (404), Victor James Osimhen (507), Davinson Sanchez Mina (516), Aleksey Batrakov (877). XI out: Mohamed Salah Hamed Mahrous Ghaly (12), Guram Giorbelidze (48), Adrian Dawid Benedyczak (75), Berkan İsmail Kutlu (212), Bahadır Han Güngördü (216), Chidozie Collins Awaziem (217), Franculino Gluda Dju (1471).

Bench in: Adem Arous (84), Cengiz Ünder (193), Michael Amir Murillo Bermudez (277). Bench out: Davinson Sanchez Mina (516), Abdülkerim Bardakcı (533), Miguel Felipe Nunes Cardoso (746).

Largest common-player xPts changes: Franco Daryl Tongya Heubang (346) +3.607, Franculino Gluda Dju (1471) -3.605, Stefan Savic (27) +3.038, Abdülkerim Bardakcı (533) -2.811, Barış Alper Yılmaz (520) -2.552.

### rest_days_control

XI in: Andre Onana Onana (22), Stefan Savic (27), Adem Arous (84), Franco Daryl Tongya Heubang (346), Eldor Shomurodov (404), Victor James Osimhen (507), Aleksey Batrakov (877). XI out: Mohamed Salah Hamed Mahrous Ghaly (12), Guram Giorbelidze (48), Adrian Dawid Benedyczak (75), Berkan İsmail Kutlu (212), Bahadır Han Güngördü (216), Chidozie Collins Awaziem (217), Franculino Gluda Dju (1471).

Bench in: Guram Giorbelidze (48), Cengiz Ünder (193), İrfan Can Eğribayat (195). Bench out: Amar Gerxhaliu (53), Ederson Santana de Moraes (166), Miguel Felipe Nunes Cardoso (746).

Largest common-player xPts changes: Franco Daryl Tongya Heubang (346) +3.617, Franculino Gluda Dju (1471) -3.196, Stefan Savic (27) +2.661, Bahadır Han Güngördü (216) -2.472, Abdülkerim Bardakcı (533) -2.466.

## Eligibility and participation

Newly eligible (17): Mervan Müjdeci (1273), Mehmet Ataberk Dadakdeniz (1546), Efe Sarıkaya (1570), Göktan Gürpüz (16), Yiğit Hamza Aydar (329), Arda Çağan Çelik (343), Dal Varesanovic (371), Zafer Görgen (376), Edin Visca (408), Bedirhan Özyurt (434), Yakup Kırtay (44), Igor Drapinski (461), Renato Sam-Na Nhaga (527), İlkay Gündoğan (530), Wilfried Stephane Singo (545), Rayan Lutin (617), Mehmet Umut Nayir (7).

Newly excluded (12): Tayfur Bingöl (109), Ernest Poku (1141), Amadou Cisse (154), İsmail Yüksek (175), Adil Demirbağ (222), Ege Yıldırım (292), Pedro Miguel Almeida Lopes Pereira (338), Abdurrahim Dursun (344), Ulrich Sidoine Meleke (557), Bekir Turaç Böke (712), Misjonne Juniffer Naigelino Hansen (844), Paolo Fernandes Cantin (977).

The 16 returning entrants and 12 exits crossed the unchanged 0.25 participation gate as the last-four-minute window advanced. Player 1273 had no frozen history and became eligible from a GW10 row alone. The JSON artifact lists old/new probabilities and last-four minutes for all 29 eligibility changes and all other probability changes of at least 0.10. Frozen availability and prices are identical in both scenarios.

## Osimhen (507)

GW1–GW9 minutes: 90, 90, 90, 33, 0, 0, 13, 90, 88. GW10 minutes: 61. Participation probability: 0.710 → 0.944. Official availability and price remain frozen.

| Model | xPts GW9 → GW10 | Forward rank GW9 → GW10 | Selection GW9 → GW10 | Forced GW10 XI objective loss |
| --- | ---: | ---: | --- | ---: |
| baseline_5w | 2.834 → 3.910 | 10 → 6 | out → out | -1.5060 |
| short_form_3w | 5.160 → 6.452 | 5 → 2 | out → XI | +0.0000 |
| stable_8w | 4.151 → 3.685 | 5 → 6 | out → out | -2.1550 |
| uniform_xg | 5.934 → 7.421 | 4 → 1 | out → XI | +0.0000 |
| position_aware_xg | 5.818 → 7.276 | 4 → 1 | out → XI | +0.0000 |
| rest_days_control | 5.160 → 6.452 | 5 → 2 | out → XI | +0.0000 |

## Limitations and recommendation

One additional week changes one of eleven XI slots in the least sensitive model and seven in four others. These shifts show sensitivity, not improved accuracy. GW10 was retrieved after the capture, and no independent pre-deadline timestamp establishes its availability at that time. The isolated GW10 scenario intentionally preserves missing older rows; it is a controlled intervention rather than a complete historical repair. Keep production weights and thresholds unchanged. Evaluate against finalized official outcomes before tuning.

## Verification

The replay completed with zero fetch failures and all 573 GW10 rows. Frozen input hash, six saved GW9 XIs, benches, captains, fantasy xPts, and objectives matched exactly. The optimizer returned solutions for both scenarios and all six models. No original snapshot or prediction was overwritten. Full player projections and lineups are in [phase27_history_impact.json](phase27_history_impact.json).
