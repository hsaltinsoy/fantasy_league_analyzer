from analysis.availability import evaluate
from data_sources.tff_official import fetch_players as fetch_tff_players, TFFFeedError
from flask import Flask, jsonify, render_template, request
from data_sources.xgedge import fetch_players, PlayerFeedError
from data_sources.position_enrichment import enrich
import os
from data_sources.player_import import merge
from data_sources.live_sync import sync
from data_sources.free_sync import sync as free_sync, FeedError
from data_sources.api_football import APIError
from analysis.optimizer import optimize
from analysis.backtesting import evaluate_snapshot
from analysis.fixture_difficulty import calculate
from data_sources.player_csv import parse_players
from analysis.player_prediction import predict
from analysis.next_week_projection import project
from data_sources.football_data import parse_results, parse_fixtures, upcoming_from_results_csv


def create_app():
    app = Flask(__name__)

    @app.get('/api/players/tff')
    def tff_players():
        try:
            return jsonify(fetch_tff_players())
        except (TFFFeedError, OSError, RuntimeError) as exc:
            return jsonify(error=str(exc)), 502

    @app.get('/api/players/xgedge')
    def xgedge_players():
        try:
            data = fetch_players()
            if request.args.get('positions') == '1':
                enrichment = enrich(data['players'])
                data['position_enrichment'] = {k:v for k,v in enrichment.items() if k != 'players'}
            return jsonify(data)
        except (PlayerFeedError, ValueError) as exc:
            return jsonify(error=str(exc)), 502

    @app.get('/api/free/refresh')
    def free_refresh():
        try:
            return jsonify(free_sync())
        except (FeedError, ValueError) as exc:
            return jsonify(error=str(exc)), 502

    @app.post('/api/players/import')
    def import_players():
        stats = request.files.get('stats')
        prices = request.files.get('prices')
        if not stats:
            return jsonify(error='Upload a permitted player statistics CSV export'), 400
        try:
            stats_bytes = stats.read(2_000_001)
            if len(stats_bytes) > 2_000_000:
                return jsonify(error='Statistics CSV too large'), 413
            price_bytes = prices.read(500_001) if prices and prices.filename else None
            if price_bytes and len(price_bytes) > 500_000:
                return jsonify(error='Price CSV too large'), 413
            return jsonify(merge(stats_bytes.decode('utf-8-sig'), price_bytes.decode('utf-8-sig') if price_bytes else None))
        except (ValueError, UnicodeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get('/api/live/refresh')
    def live_refresh():
        try:
            season = int(os.getenv('API_FOOTBALL_SEASON', '2026'))
            with_players = request.args.get('players', '0') == '1'
            return jsonify(sync(season, include_players=with_players))
        except (APIError, ValueError, KeyError, TypeError) as exc:
            return jsonify(error=str(exc)), 502

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.post('/api/projections/next-week')
    def next_week_projections():
        payload = request.get_json(silent=True) or {}
        player_data = payload.get('players')
        fixture_data = payload.get('fixtures')
        team_matches = payload.get('team_matches')
        if not isinstance(player_data, list) or not isinstance(fixture_data, list) or not isinstance(team_matches, dict):
            return jsonify(error='players, fixtures ve team_matches gerekli; önce iki kaynağı güncelleyin.'), 400
        if len(player_data) > 1500 or len(fixture_data) > 60:
            return jsonify(error='Beklenmeyen veri boyutu'), 413
        try:
            result = project(player_data, fixture_data, team_matches)
            return jsonify(players=result, count=len(result), projected=sum(p['expected_points'] is not None for p in result),
                           missing_positions=sum(p['projection_status']=='position_missing' for p in result),
                           missing_fixtures=sum(p['projection_status']=='fixture_missing' for p in result),
                           warning='Deneysel, kısmi puan tahmini: yalnızca oynama, xG ve xA. Resmî TFF puanı değildir; kart, clean sheet, bonus ve kaleci kurtarışları dahil değil.')
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/availability/check')
    def check_availability():
        payload = request.get_json(silent=True) or {}
        players = payload.get('players')
        overrides = payload.get('overrides', [])
        if not isinstance(players, list) or not isinstance(overrides, list) or len(players) > 1500 or len(overrides) > 200:
            return jsonify(error='Geçersiz oyuncu veya durum listesi'), 400
        try:
            round_number = int(payload.get('round', 10))
            return jsonify(decisions={str(p['id']): evaluate(p, overrides, round_number) for p in players})
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/backtest/evaluate')
    def evaluate_backtest():
        payload = request.get_json(silent=True) or {}
        try:
            actual = payload.get('actual_players')
            if not isinstance(actual, list) or len(actual) > 1500:
                return jsonify(error='Geçersiz gerçekleşen oyuncu listesi'), 400
            result = evaluate_snapshot(payload.get('snapshot'), actual, payload.get('round'))
            return jsonify(result)
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/optimize')
    def run_optimization():
        payload = request.get_json(silent=True) or {}
        players = payload.get('players')
        if not isinstance(players, list):
            return jsonify(error='Provide a players array with real prices and projected points'), 400
        try:
            result = optimize(players, float(payload.get('budget', 100)))
            return jsonify(result), 200 if 'error' not in result else 422
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/fixtures/analyze')
    def analyze_fixtures():
        """Multipart upload: results CSV (Football-Data format) and fixtures CSV."""
        results = request.files.get('results')
        fixtures = request.files.get('fixtures')
        if not results:
            return jsonify(error='Upload a results CSV file'), 400
        try:
            if results.content_length and results.content_length > 2_000_000:
                return jsonify(error='Results file too large'), 413
            if fixtures.content_length and fixtures.content_length > 200_000:
                return jsonify(error='Fixtures file too large'), 413
            results_text = results.read(2_000_001).decode('utf-8-sig')
            matches = parse_results(results_text)
            upcoming = (parse_fixtures(fixtures.read(200_001).decode('utf-8-sig'))
                        if fixtures and fixtures.filename else upcoming_from_results_csv(results_text))
            if not upcoming:
                return jsonify(error='No upcoming fixtures found. Upload a separate fixture CSV, or provide a results CSV containing future scheduled matches'), 400
            if not matches:
                return jsonify(error='No completed matches found in results CSV'), 400
            return jsonify({'fixtures': calculate(matches, upcoming), 'matches_loaded': len(matches),
                            'warning': 'FDR is a provisional form-based heuristic, not a calibrated prediction. Team names are normalized using known aliases.'})
        except (UnicodeError, ValueError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/players/predict')
    def predict_players():
        file = request.files.get('players')
        if not file:
            return jsonify(error='Upload players CSV'), 400
        try:
            content = file.read(2_000_001)
            if len(content) > 2_000_000:
                return jsonify(error='Players CSV too large'), 413
            players = parse_players(content.decode('utf-8-sig'))
            fixture_data = request.form.get('fixture_analysis', '')
            import json
            fixtures = json.loads(fixture_data) if fixture_data else []
            if not isinstance(fixtures, list):
                raise ValueError('fixture_analysis must be a JSON array')
            return jsonify(players=predict(players, fixtures), count=len(players), warning='Baseline projections only; not official TFF fantasy points or validated FotMob statistics.')
        except (UnicodeError, ValueError, TypeError) as exc:
            return jsonify(error=str(exc)), 400

    return app
