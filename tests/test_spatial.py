from backend.app.services.spatial import spatial_score

def test_spatial_rejects_too_wide():
    score,_=spatial_score(250,90,240,120,10)
    assert score==0

def test_spatial_rewards_good_fit():
    score,_=spatial_score(180,80,240,120,10)
    assert score>0.8
