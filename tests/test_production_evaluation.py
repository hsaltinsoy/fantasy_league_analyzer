from analysis.production_scoring import dashboard_player_points, lineup_player_points
from analysis.production_evaluation import evaluate_saved, report


def test_dashboard_parity_fixed_case():
    player={'position':'MID','minutes':540,'points_per_match':3,'total_points':27,'form':5}
    prediction={'expected_points':4,'expected_minutes':60}
    fixture={'opponent':'A','fdr':2}
    # JS: base=3.4, exposure=1, minutes factor=.8; blend=3.224;
    # fixture 1.08, availability .5 => 1.74096 => 1.74.
    assert dashboard_player_points(player,prediction,fixture,{'factor':.5})==1.74


def test_lineup_score_uses_only_supplied_past():
    player={'position':'MID'}
    past=[{'points':3,'minutesPlayed':90} for _ in range(3)]
    assert lineup_player_points(player,past,'short_form_3w')==lineup_player_points(player,list(past),'short_form_3w')


def test_saved_prediction_missing_actuals_and_captain():
    prediction={'id':'p','gameweek':10,'model':'short_form_3w','status':'deadline_unknown',
                'risk_adjusted_objective':20,
                'payload':{'starting_xi':[{'id':i,'xpts':2,'captain':i==1,'price':4,'team':'A'} for i in range(1,12)],
                           'formation':'4-4-2','cost':80}}
    snapshot={'players':[{'id':i,'price':4,'club_id':'A'} for i in range(1,12)],
              'histories':[{'player_id':i,'rows':[{'gameweekOrder':9,'points':2}]} for i in range(1,12)]}
    assert evaluate_saved(prediction,snapshot,{})['status']=='not_evaluable'
    row=evaluate_saved(prediction,snapshot,{str(i):3 for i in range(1,12)})
    assert row['actual_points']==36
    assert row['starting_xi_actual_points']==33
    assert row['captain_contribution']==3
    assert row['predicted_points']==24
    snapshot['histories'][0]['rows'].append({'gameweekOrder':10,'points':100})
    assert evaluate_saved(prediction,snapshot,{str(i):3 for i in range(1,12)})['reason']=='future_statistics_in_snapshot'
    snapshot['histories'][0]['rows'].pop()
    snapshot['players'][0]['club_id']='B'
    assert evaluate_saved(prediction,snapshot,{str(i):3 for i in range(1,12)})['reason']=='player_transfer_or_club_mismatch'
    snapshot['players'][0]['club_id']='A'
    snapshot['players'][0]['price']=None
    assert evaluate_saved(prediction,snapshot,{str(i):3 for i in range(1,12)})['reason']=='missing_snapshot_price'
    snapshot['players'][0]['price']=4
    snapshot['fixtures']=[{'homeClubId':'A','awayClubId':'B'}]
    assert evaluate_saved(prediction,snapshot,{str(i):3 for i in range(1,12)})['reason']=='incorrect_fixture_mapping'


def test_no_saved_predictions_is_not_evaluable(tmp_path):
    assert report(tmp_path/'absent.sqlite3')['classification']=='not_evaluable'
