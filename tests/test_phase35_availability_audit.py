"""Lagged appearance benchmark and classification accounting."""
from analysis.phase35_availability_audit import alternative, scores


def test_alternative_uses_only_prior_minutes():
    past=[{'minutesPlayed':0},{'minutesPlayed':90},{'minutesPlayed':0},{'minutesPlayed':90}]
    assert alternative(past)==.5
    target={'minutesPlayed':90}
    target['minutesPlayed']=0
    assert alternative(past)==.5


def test_classification_counts_reconcile():
    rows=[{'proxy':.8,'played':True},{'proxy':.7,'played':False},
          {'proxy':.2,'played':True},{'proxy':.1,'played':False}]
    result=scores(rows,'proxy',.5)
    assert (result['tp'],result['fp'],result['fn'],result['tn'])==(1,1,1,1)
    assert result['accuracy']==.5
