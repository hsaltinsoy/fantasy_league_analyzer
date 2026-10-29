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
from analysis.chips import scenarios, last_round_players
from analysis.fixture_difficulty import calculate
from data_sources.player_csv import parse_players
from analysis.player_prediction import predict
from analysis.next_week_projection import project
from data_sources.football_data import parse_results, parse_fixtures, upcoming_from_results_csv


def create_app():
    app = Flask(__name__)

    def json_object():
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    @app.get('/lineup')
    def lineup_page():
        return render_template('lineup.html')

    @app.get('/benchmark')
    def benchmark_page():
        from analysis.live_benchmark import report
        from app.benchmark_view import comparison_view, risk_chart_view
        from data_sources.club_metadata import load_clubs
        import json
        from pathlib import Path
        result=report()
        comparison=comparison_view(result,request.args.get('left'),request.args.get('right'),load_clubs())
        chart=risk_chart_view(result,comparison['left']['saved']['snapshot_id'],
                              (comparison['left']['id'],comparison['right']['id'])) if comparison else None
        player_report_path=Path('historical_data/player_level_phase11/player_level_report.json')
        player_accuracy=json.loads(player_report_path.read_text(encoding='utf-8')) if player_report_path.exists() else None
        recovered_path=Path('historical_data/recovered')
        coverage_path=recovered_path/'coverage_report.json'
        model_path=recovered_path/'model_evaluation.json'
        combined_path=recovered_path/'model_evaluation_combined.json'
        recovered_coverage=json.loads(coverage_path.read_text(encoding='utf-8')) if coverage_path.exists() else None
        recovered_models=json.loads(model_path.read_text(encoding='utf-8')) if model_path.exists() else None
        recovered_combined=json.loads(combined_path.read_text(encoding='utf-8')) if combined_path.exists() else None
        ranking_reports={source: json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
                         for source, path in (
                             ('official', recovered_path/'player_ranking_official.json'),
                             ('combined', recovered_path/'player_ranking_combined.json'))}
        player_chart_max=(max((item['baselines'][name]['unconditional']['mae'] or 0)
                              for item in player_accuracy['by_gameweek']
                              for name in ('recent_3_average','season_to_date_average'))
                          if player_accuracy else None)
        return render_template('benchmark.html', report=result, comparison=comparison, chart=chart,
                               player_accuracy=player_accuracy, player_chart_max=player_chart_max,
                               recovered_coverage=recovered_coverage, recovered_models=recovered_models,
                               recovered_combined=recovered_combined, ranking_reports=ranking_reports)

    @app.post('/api/benchmark/evaluate')
    def benchmark_evaluate():
        from analysis.benchmark_evaluation import evaluate_gameweek
        payload=json_object()
        snapshot_id=payload.get('snapshot_id')
        if not isinstance(snapshot_id,str) or not snapshot_id:
            return jsonify(error='Existing snapshot ID required'),400
        try:
            run=evaluate_gameweek(snapshot_id)
            return jsonify(id=run['id'],status=run['status'],snapshot_id=run['snapshot_id'],
                           complete_predictions=run['payload']['complete_predictions'],
                           total_predictions=run['payload']['total_predictions'],
                           fixture_issues=run['payload']['fixture_issues'],
                           player_issues=run['payload']['player_issues'])
        except (ValueError, KeyError, OSError, RuntimeError, TFFFeedError) as exc:
            app.logger.exception('Benchmark evaluation failed')
            return jsonify(error=str(exc)),502

    @app.post('/api/benchmark/direct-risk')
    def benchmark_direct_risk():
        from analysis.live_benchmark import save_direct_risk
        payload=json_object()
        snapshot_id=payload.get('snapshot_id')
        if not isinstance(snapshot_id,str) or not snapshot_id:
            return jsonify(error='Existing snapshot ID required'),400
        try:
            return jsonify(save_direct_risk(snapshot_id=snapshot_id))
        except (ValueError,KeyError,OSError,RuntimeError) as exc:
            app.logger.exception('Direct-risk benchmark failed')
            return jsonify(error=str(exc)),400

    @app.get('/api/benchmark/report')
    def benchmark_report():
        from analysis.live_benchmark import report
        return jsonify(report())

    @app.get('/api/benchmark/player-accuracy')
    def benchmark_player_accuracy():
        import json
        from pathlib import Path
        path=Path('historical_data/player_level_phase11/player_level_report.json')
        if not path.exists():
            return jsonify(error='Player-level report has not been generated'),404
        return jsonify(json.loads(path.read_text(encoding='utf-8')))

    @app.get('/api/benchmark/recovered-history')
    def benchmark_recovered_history():
        import json
        from pathlib import Path
        path=Path('historical_data/recovered/coverage_report.json')
        return (jsonify(json.loads(path.read_text(encoding='utf-8'))),200) if path.exists() else \
               (jsonify(error='Historical recovery report unavailable'),404)

    @app.get('/api/benchmark/recovered-models')
    def benchmark_recovered_models():
        import json
        from pathlib import Path
        source=request.args.get('source','official')
        if source not in ('official','combined'):
            return jsonify(error='Unknown recovered source policy'),400
        filename='model_evaluation.json' if source=='official' else 'model_evaluation_combined.json'
        path=Path('historical_data/recovered')/filename
        return (jsonify(json.loads(path.read_text(encoding='utf-8'))),200) if path.exists() else \
               (jsonify(error='Recovered-model report unavailable'),404)

    @app.get('/api/benchmark/player-ranking')
    def benchmark_player_ranking():
        import json
        from pathlib import Path
        source=request.args.get('source','official')
        if source not in ('official','combined'):
            return jsonify(error='Unknown ranking source policy'),400
        path=Path('historical_data/recovered')/f'player_ranking_{source}.json'
        return (jsonify(json.loads(path.read_text(encoding='utf-8'))),200) if path.exists() else \
               (jsonify(error='Player-ranking report unavailable'),404)

    @app.post('/api/benchmark/generate')
    def benchmark_generate():
        from analysis.live_benchmark import generate
        try:
            return jsonify(generate(cached=json_object().get('cached') is True))
        except (ValueError, KeyError, OSError, RuntimeError) as exc:
            app.logger.exception('Benchmark generation failed')
            return jsonify(error=str(exc)), 400

    @app.get('/api/lineup/latest')
    def lineup_latest():
        import json
        from pathlib import Path
        try:
            week=int(request.args.get('week','10'))
            if not 2 <= week <= 34: raise ValueError('Invalid week')
            path=Path('historical_data')/f'next_week_gw{week}.json'
            if not path.exists():
                return jsonify(error='Henüz kayıtlı kadro yok. Önce Kadroyu oluştur düğmesine basın.'),404
            data=json.loads(path.read_text(encoding='utf-8'))
            if 'clubs' not in data:
                from data_sources.club_metadata import load_clubs
                data['clubs']=load_clubs()
            return jsonify(data)
        except ValueError as exc:
            return jsonify(error=str(exc)),400

    @app.get('/api/lineup/generate')
    def lineup_generate():
        import json
        from pathlib import Path
        from analysis.predict_next_week import predict
        from analysis.multiweek_backtest import load_history, MODELS
        from analysis.verified_fixtures_v34 import load_verified
        from analysis.team_of_week_v36 import load as load_tow
        from analysis.prediction_tracking import save_snapshot, save_prediction
        from data_sources.identity import load_crosswalk, crosswalk_version
        from data_sources.fixture_validation import validate_week
        try:
            week=int(request.args.get('week','10'))
            model=request.args.get('model','short_form_3w')
            weight=float(request.args.get('tow_weight','0'))
            live=request.args.get('live','1')=='1'
            risk_profile=request.args.get('risk_profile','balanced')
            experimental_covariance=request.args.get('experimental_covariance','0')=='1'
            if not 2 <= week <= 34 or model not in MODELS or weight not in (0,.05,.1) or risk_profile not in ("aggressive","balanced","cautious"):
                return jsonify(error='Geçersiz parametre'),400
            store=Path('historical_data')
            if live:
                players=fetch_tff_players()['players']
            else:
                players=json.loads((store/'players.json').read_text(encoding='utf-8'))
            records=load_history()
            fixtures=load_verified(store/'tff_fixtures_verified_v5.json',[week])
            tow=load_tow(store/'team_of_week_verified.json')
            result=predict(week,players,records,fixtures,tow,model,tow_weight=weight,risk_profile=risk_profile,experimental_covariance=experimental_covariance)
            fixture_file=json.loads((store/'tff_fixtures_verified_v5.json').read_text(encoding='utf-8'))
            week_entry=fixture_file['weeks'][str(week)]
            crosswalk=load_crosswalk()
            fixture_quality=validate_week(week_entry,players)
            data_quality={'total_tff_players':len(players),'matched_players':0,
                          'ambiguous_matches':0,'unmatched_players':len(players),
                          'missing_statistics':len(players),
                          'crosswalk_version':crosswalk_version(crosswalk),**fixture_quality}
            result['data_quality']=data_quality
            snapshot=save_snapshot(week,players,week_entry['matches'],
                [{'player_id':p['id'],'rows':[r for r in rows if int(r['gameweekOrder'])<week]}
                 for p,rows in records],
                {'players':'tfffantezilig.com' if live else 'historical_data/players.json',
                 'fixtures':fixture_file.get('source_endpoint'),'histories':'historical_data/player_<id>.json'},
                classification='live' if live else 'historical_reconstruction',
                data_quality=data_quality)
            tracking=save_prediction(snapshot['id'],result,model_version='v3.9')
            result['prediction_tracking']=tracking
            from data_sources.club_metadata import load_clubs
            clubs=load_clubs(live=live)
            result['clubs']=clubs
            # Captain alternatives come from the same risk-adjusted captain objective as the optimizer.
            # Do not overwrite with raw xPts (which can give a misleading ranking).
            if not live:
                result['warning']+=' Kayıtlı oyuncu verisi kullanıldı; güncel olmayabilir.'
            (store/f'next_week_gw{week}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            return jsonify(result)
        except Exception as exc:
            app.logger.exception('Lineup generation failed')
            return jsonify(error=f'Kadro oluşturulamadı: {exc}'),500

    @app.get('/api/predictions/<prediction_id>')
    def saved_prediction(prediction_id):
        from analysis.prediction_tracking import get_prediction
        result=get_prediction(prediction_id)
        return (jsonify(result),200) if result else (jsonify(error='Prediction not found'),404)

    @app.get('/api/snapshots/<snapshot_id>')
    def saved_snapshot(snapshot_id):
        from analysis.prediction_tracking import get_snapshot
        result=get_snapshot(snapshot_id)
        return (jsonify(result),200) if result else (jsonify(error='Snapshot not found'),404)

    @app.post('/api/identity/resolve')
    def resolve_identity():
        from data_sources.identity import load_crosswalk, resolve_players
        from data_sources.fixture_validation import validate_week
        from data_sources.team_names import normalize_team
        from data_sources.club_metadata import load_clubs
        from pathlib import Path
        import json
        payload=json_object()
        tff=payload.get('tff_players')
        external=payload.get('external_players')
        if not isinstance(tff,list) or not isinstance(external,list) or len(tff)>2000 or len(external)>2000:
            return jsonify(error='Player lists required'),400
        try:
            clubs=load_clubs()
            tff=[{**p,'club_name':clubs.get(str(p.get('club_id')),{}).get('name')}
                 for p in tff]
            resolved,report=resolve_players(tff,external,load_crosswalk())
            week=int(payload.get('week',10))
            store=Path('historical_data')
            fixture_file=json.loads((store/'tff_fixtures_verified_v5.json').read_text(encoding='utf-8'))
            entry=fixture_file['weeks'][str(week)]
            report.update(validate_week(entry,tff))
            official_clubs={str(m[k]) for m in entry['matches'] for k in ('homeClubId','awayClubId')}
            free_fixtures=payload.get('fixtures') or []
            by_name={}
            for fixture in free_fixtures:
                by_name.setdefault(normalize_team(fixture.get('team')),[]).append(fixture)
            mappings={}
            for club_id in official_clubs:
                club_name=clubs.get(club_id,{}).get('name')
                candidates=by_name.get(normalize_team(club_name),[]) if club_name else []
                if len(candidates)==1:
                    mappings[club_id]={'team':normalize_team(club_name),'fixture':candidates[0],
                                       'evidence':'official_club_id_and_fixture_participation'}
            report['invalid_club_mappings']+=len(official_clubs-set(mappings))
            if len(mappings)<len(official_clubs):
                report['warnings'].append('Some official fixture clubs lack a unique external fixture mapping')
            enriched=[]
            for player in resolved:
                external_row=player['external_statistics']
                if external_row is not None:
                    enriched.append({**external_row,'official_id':player['id'],
                                     'official_position':player['position'],
                                     'official_club_id':player.get('club_id'),
                                     'identity_confidence':player['identity_confidence']})
            matched_external={id(p['external_statistics']) for p in resolved if p['external_statistics'] is not None}
            enriched.extend(p for p in external if id(p) not in matched_external)
            return jsonify(players=resolved,enriched=enriched,club_mappings=mappings,report=report)
        except (ValueError,KeyError,OSError,TypeError) as exc:
            return jsonify(error=str(exc)),400

    @app.post('/api/predictions/<prediction_id>/evaluate')
    def evaluate_saved_prediction(prediction_id):
        from analysis.prediction_tracking import evaluate_prediction
        payload=json_object()
        try:
            return jsonify(evaluate_prediction(prediction_id,payload.get('actual_points')))
        except ValueError as exc:
            return jsonify(error=str(exc)),400

    @app.post('/api/lineup/compare')
    def compare_lineup():
        import json
        from pathlib import Path
        payload=json_object()
        try:
            week=int(payload.get('week',10))
            ids=payload.get('player_ids',[])
            if not isinstance(ids,list) or len(ids)!=11 or any(isinstance(i,bool) or not str(i).isdigit() for i in ids):
                return jsonify(error='İlk 11 için 11 adet oyuncu ID girin.'),400
            ids=[int(i) for i in ids]
            if len(set(ids))!=11:return jsonify(error='Oyuncu ID değerleri tekrarlanmamalı.'),400
            path=Path('historical_data')/f'next_week_gw{week}.json'
            if not path.exists():return jsonify(error='Önce bu haftanın model kadrosunu oluşturun.'),404
            model=json.loads(path.read_text(encoding='utf-8'))
            selected={int(p['id']) for p in model['starting_xi']}
            player_file=Path('historical_data/players.json')
            players={int(p['id']):p for p in json.loads(player_file.read_text(encoding='utf-8'))}
            unknown=[i for i in ids if i not in players]
            if unknown:return jsonify(error=f'Kayıtlı oyuncu listesinde ID bulunamadı: {unknown}'),400
            return jsonify(overlap=len(selected.intersection(ids)),
                same=[players[i]['name'] for i in ids if i in selected],
                yours_only=[players[i]['name'] for i in ids if i not in selected],
                model_only=[p['name'] for p in model['starting_xi'] if int(p['id']) not in ids],
                warning='Sadece oyuncu örtüşmesi karşılaştırılır; senin kadron için yeni xPts hesaplanmaz. Oyuncu isimleri kayıtlı listeden alınır.')
        except (ValueError,TypeError,KeyError,OSError) as exc:
            return jsonify(error=str(exc)),400

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
        from app.dashboard_view import dashboard_data
        from analysis.live_benchmark import report
        from pathlib import Path
        import json
        view=dashboard_data()
        benchmark=report()
        recovered=Path('historical_data/recovered')
        def read(name):
            path=recovered/name
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        return render_template('index.html', dashboard=view, benchmark=benchmark,
                               phase11=json.loads(Path('historical_data/player_level_phase11/player_level_report.json').read_text(encoding='utf-8')) if Path('historical_data/player_level_phase11/player_level_report.json').exists() else None,
                               player_accuracy=read('model_evaluation.json'),
                               player_ranking=read('player_ranking_official.json'),
                               recovery=read('coverage_report.json'))

    @app.get('/tools')
    def legacy_tools():
        return render_template('legacy_tools.html')

    @app.post('/api/projections/next-week')
    def next_week_projections():
        payload = json_object()
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

    @app.post('/api/dashboard/score')
    def dashboard_score():
        from analysis.production_scoring import dashboard_player_points
        payload=json_object()
        rows=payload.get('rows')
        if not isinstance(rows,list) or len(rows)>1500:
            return jsonify(error='Scoring rows required'),400
        try:
            rounds=int(payload.get('completed_rounds',9))
            if not 1<=rounds<=34: raise ValueError('Invalid completed round count')
            return jsonify(points=[dashboard_player_points(r['player'],r.get('prediction'),
                r.get('fixture'),r.get('decision'),rounds) for r in rows])
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            return jsonify(error=str(exc)),400

    @app.post('/api/dashboard/track')
    def track_dashboard_prediction():
        from analysis.prediction_tracking import save_snapshot, save_prediction
        payload=json_object()
        try:
            week=int(payload.get('week',10))
            solution=payload['solution']
            players=payload['players']
            fixtures=payload['fixtures']
            if not 2<=week<=34 or not isinstance(players,list) or not players or not isinstance(fixtures,list):
                raise ValueError('Invalid dashboard inputs')
            xi=[{**p,'captain':p['id']==solution['captain']['id']} for p in solution['starting_xi']]
            ids={p['id'] for p in xi}
            bench=[p for p in solution['squad'] if p['id'] not in ids]
            result={'model':'dashboard_blend_v1','risk_profile':solution.get('risk_profile','balanced'),
                    'expected_points':solution['expected_points'],
                    'risk_adjusted_objective':solution.get('risk_adjusted_objective'),
                    'starting_xi':xi,'bench':bench,'formation':solution['formation'],
                    'squad_cost':solution['squad_cost']}
            snapshot=save_snapshot(week,players,fixtures,[],
                {'players':'browser-supplied current TFF/xgEdge data',
                 'fixtures':'browser-supplied free fixture feed'},
                classification='live',
                data_quality=payload.get('data_quality'))
            return jsonify(save_prediction(snapshot['id'],result,model_version='v3.9-dashboard'))
        except (ValueError,TypeError,KeyError) as exc:
            return jsonify(error=str(exc)),400

    @app.post('/api/availability/check')
    def check_availability():
        payload = json_object()
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
        payload = json_object()
        try:
            actual = payload.get('actual_players')
            if not isinstance(actual, list) or len(actual) > 1500:
                return jsonify(error='Geçersiz gerçekleşen oyuncu listesi'), 400
            result = evaluate_snapshot(payload.get('snapshot'), actual, payload.get('round'))
            return jsonify(result)
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/chips/scenarios')
    def chip_scenarios():
        payload = json_object()
        solution = payload.get('solution')
        if not isinstance(solution, dict):
            return jsonify(error='Geçerli kadro gerekli'), 400
        try:
            return jsonify(scenarios(solution))
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get('/api/history/latest-round')
    def latest_round_history():
        try:
            feed = fetch_tff_players()
            return jsonify(last_round_players(feed['players']))
        except (TFFFeedError, OSError, RuntimeError) as exc:
            return jsonify(error=str(exc)), 502

    @app.post('/api/optimize')
    def run_optimization():
        payload = json_object()
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
            if fixtures and fixtures.content_length and fixtures.content_length > 200_000:
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
