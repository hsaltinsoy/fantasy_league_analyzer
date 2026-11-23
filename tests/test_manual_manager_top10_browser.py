"""Browser regression for the confirmation button state; no TFF access."""
import json
from threading import Thread

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import create_app
from analysis.manual_manager_collector import catalogue, read_records


def test_attack_confirmation_enables_save_and_failed_save_keeps_preview():
    app = create_app()
    app.config['TESTING'] = True
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.route('**/api/manager-collector/players', lambda route: route.fulfill(
                    status=200, content_type='application/json', body=json.dumps({'players': []})))
                page.route('**/api/manager-collector/dashboard?*', lambda route: route.fulfill(
                    status=200, content_type='application/json', body=json.dumps({
                        'tiers': {'10': {'manager_weeks': 0, 'players': [], 'captains': []}},
                        'pre_deadline_count': 0, 'retrospective_count': 0, 'weekly_comparisons': []})))

                def preview(route):
                    submitted = route.request.post_data_json['managers']
                    confirmed = submitted[0]['attack_rules_unverified_confirmed']
                    record = {'rank_at_capture': 1, 'manager_key': 'abcdef12', 'gameweek': 12,
                              'formation': '2-3-5', 'manager_card': 'attack',
                              'rules_status': 'rules_unverified', 'validation_status': 'rules_unverified',
                              'observation_kind': 'timing_unverified',
                              'feature_eligible': False, 'position_counts': {'GK': 2, 'DEF': 3, 'MID': 5, 'FWD': 5},
                              'captain_id': 1, 'vice_captain_id': 2,
                              'starting_xi_ids': list(range(1, 12)), 'bench_ids': [12, 13, 14, 15],
                              'weekly_points_displayed': None}
                    results = [{'manager': 1, 'status': 'valid' if confirmed else 'needs_confirmation',
                                'record': record, 'message': None if confirmed else 'Confirm Attack Card squad'}]
                    results += [{'manager': i, 'status': 'valid', 'record': record} for i in range(2, 11)]
                    route.fulfill(status=200, content_type='application/json', body=json.dumps({
                        'managers': results, 'records': [record] * 10, 'can_save': bool(confirmed)}))

                page.route('**/api/manager-collector/top10/preview', preview)
                save_payloads = []
                def fail_save(route):
                    save_payloads.append(route.request.post_data_json)
                    route.fulfill(status=400, content_type='application/json', body=json.dumps({'error': 'Duplicate manager-week'}))
                page.route('**/api/manager-collector/top10/save', fail_save)
                page.goto(base + '/manager-collector/top10')
                assert page.locator('#save').is_disabled()
                page.locator('#preview').click()
                page.get_by_text('Confirm Attack Card squad', exact=True).wait_for()
                assert page.locator('#save').is_disabled()
                page.locator('.preview-attack-confirm').first.check()
                page.get_by_text('All ten validated and confirmed').wait_for()
                assert page.locator('#save').is_enabled()
                assert page.locator('.manager').first.locator('.attack-confirm').is_checked()
                before = page.locator('#preview-all').inner_text()
                page.locator('#save').click()
                page.get_by_text('Duplicate manager-week').wait_for()
                assert page.locator('#preview-all').inner_text() == before
                assert page.locator('#save').is_enabled()
                assert save_payloads[0]['managers'][0]['attack_rules_unverified_confirmed'] is True
                assert save_payloads[0]['manual_confirmed_manager_keys'] == [save_payloads[0]['managers'][0]['manager_key']]
            finally:
                browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_real_page_and_real_backend_save_attack_squad(tmp_path):
    app = create_app()
    app.config.update(TESTING=True, MANAGER_COLLECTOR_STORE=tmp_path / 'real.json')
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        players = catalogue()
        groups = {pos: [p['label'] for p in players.values() if p['position'] == pos][:n]
                  for pos, n in [('GK', 2), ('DEF', 5), ('MID', 5), ('FWD', 5)]}
        standard_xi = groups['GK'][:1] + groups['DEF'][:3] + groups['MID'][:4] + groups['FWD'][:3]
        standard_bench = groups['GK'][1:2] + groups['DEF'][3:5] + groups['MID'][4:5]
        attack_xi = groups['GK'][:1] + groups['DEF'][:3] + groups['MID'][:2] + groups['FWD'][:5]
        attack_bench = groups['GK'][1:2] + groups['MID'][2:5]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/manager-collector/top10')
                page.locator('#week').fill('12')
                page.locator('#basis').fill('11')
                for index in range(10):
                    card = page.locator('.manager').nth(index)
                    card.evaluate('(element) => { element.open = true }')
                    card.locator('.captured').fill('2026-11-10T12:00')
                    is_attack = index == 0
                    xi, bench = (attack_xi, attack_bench) if is_attack else (standard_xi, standard_bench)
                    card.locator('.formation').fill('3-2-5' if is_attack else '3-4-3')
                    card.locator('.card').select_option('attack' if is_attack else 'none')
                    for slot, name in enumerate(xi):
                        card.locator('.starter-name').nth(slot).fill(name)
                    for slot, name in enumerate(bench):
                        card.locator('.bench-name').nth(slot).fill(name)
                    card.locator('.captain-name').fill(xi[-1])
                    card.locator('.vice-name').fill(xi[-2])
                page.locator('#preview').click()
                page.locator('.preview-attack-confirm').wait_for()
                assert page.locator('#save').is_disabled()
                page.locator('.preview-attack-confirm').check()
                page.get_by_text('All ten validated and confirmed').wait_for()
                assert page.locator('#save').is_enabled()
                page.locator('#save').click()
                page.get_by_text('Saved 10 confirmed records.').wait_for()
                saved = read_records(tmp_path / 'real.json')
                assert len(saved) == 10
                assert saved[0]['validation_status'] == 'rules_unverified'
                assert saved[0]['manual_confirmation'] is True
                assert saved[0]['position_counts'] == {'GK': 2, 'DEF': 3, 'MID': 5, 'FWD': 5}
            finally:
                browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
