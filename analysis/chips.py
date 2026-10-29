"""Transparent single-round chip scenarios, not a season-long recommendation."""
def scenarios(solution):
    xi=solution['starting_xi']; squad=solution['squad']; captain=solution['captain']
    base=sum(float(p['xpts']) for p in xi)+float(captain['xpts'])
    bench=[p for p in squad if str(p['id']) not in {str(x['id']) for x in xi}]
    c=float(captain['xpts'])
    return [
        {'card':'Kart yok','projected_total':round(base,2),'increment':0,'basis':'İlk 11 + 2x kaptan'},
        {'card':'Tripleks Kaptan','projected_total':round(base+c,2),'increment':round(c,2),'basis':'Kaptan 3x; normal 2x üzerine 1x'},
        {'card':'Dört Dörtlük Kaptan','projected_total':round(base+2*c,2),'increment':round(2*c,2),'basis':'Kaptan 4x; normal 2x üzerine 2x'},
        {'card':'Tüm Takım Sahaya','projected_total':round(base+sum(float(p['xpts']) for p in bench),2),'increment':round(sum(float(p['xpts']) for p in bench),2),'basis':'4 yedeğin tahmini puanı da eklenir; otomatik yedek kuralları hesaba katılmaz'},
        {'card':'Hücum','projected_total':None,'increment':None,'basis':'Özel formasyon ve ek bütçeyle yeniden optimizasyon gerekli'},
        {'card':'Limitsiz Bütçe','projected_total':None,'increment':None,'basis':'Bütçe sınırı olmadan yeniden optimizasyon gerekli'},
    ]


def last_round_players(players, round_number=None):
    rows=[]
    for p in players:
        try:
            pts=float(p.get('round_points'))
        except (TypeError,ValueError):
            continue
        if not (-30<=pts<=100):continue
        rows.append({'id':p.get('id'),'name':p.get('name'),'position':p.get('position'), 'team':p.get('team'), 'round_points':pts})
    rows.sort(key=lambda p:p['round_points'],reverse=True)
    return {'players':rows[:30], 'count':len(rows), 'round':round_number,
            'warning':'TFF roundPoints son yayınlanan haftayı gösterir; hafta numarası API tarafından doğrulanmadı. Bu liste haftanın en yüksek puanlı OYUNCULARIDIR, menajer liderlik tablosu değildir. Maç öncesi tahmin kaydı olmadan backtest sayılmaz.'}
