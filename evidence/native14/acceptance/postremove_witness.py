"""Hard harness gate for an actual SDK-replayed post-removal prompt measurement."""
def validate(rows, calls):
    assert calls == len(rows) == 1, 'Missing/duplicate actual prompt measurement'
    row = rows[0]
    assert row.get('event') == 'postremove_current_prompt_measured', 'Measurement hook failed'
    assert row.get('historicalDelmSkill') is True, 'Expected preserved historical catalogue not witnessed'
    assert row.get('currentDelmSkill') is False, 'DeLM still in effective current SDK prompt'
    assert row.get('currentDelmWaitTool') is False, 'DeLM wait tool still active after removal'
    return dict(verdict='PASS', measurementCount=1, modelCalls=calls, liveModelCalls=0, **row)
