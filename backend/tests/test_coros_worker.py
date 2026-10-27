import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from coros_worker import run_sync
from models import User

SAMPLE = '''Sport Records (1 records)
1. Outdoor Run — 2026-10-26
   Time Window: startTimestamp=1793011716 | endTimestamp=1793015517
   LabelId: 123 | SportType: 100
'''


@pytest.fixture
def config(tmp_path):
    state = tmp_path / 'credentials'
    state.mkdir(mode=0o700)
    token = state / 'token.json'
    token.write_text('{}')
    token.chmod(0o600)
    helper = tmp_path / 'helper.py'
    helper.write_text('# helper placeholder')
    return helper, state, token


def test_worker_calls_read_only_tool_and_deduplicates(db_session, config):
    helper, state, _ = config
    db_session.add(User(id=1, username='runner', password_hash='not-a-password'))
    db_session.commit()
    response = {'content': [{'type': 'text', 'text': json.dumps(SAMPLE)}], 'isError': False}
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(response))) as run:
        assert run_sync(db_session, 1, helper, state)['inserted'] == 1
        assert run_sync(db_session, 1, helper, state)['inserted'] == 0
        args = run.call_args.args[0]
        assert args[args.index('--tool') + 1] == 'querySportRecords'
        assert 'refresh_token' not in json.dumps(args)


def test_worker_rejects_insecure_credentials_and_unknown_user(db_session, config):
    helper, state, token = config
    token.chmod(0o644)
    with pytest.raises(ValueError):
        run_sync(db_session, 1, helper, state)
    token.chmod(0o600)
    with pytest.raises(ValueError):
        run_sync(db_session, 999, helper, state)


def test_worker_failure_never_imports(db_session, config):
    helper, state, _ = config
    db_session.add(User(id=1, username='runner', password_hash='not-a-password'))
    db_session.commit()
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='sensitive')):
        with pytest.raises(RuntimeError, match='COROS request failed'):
            run_sync(db_session, 1, helper, state)
    from models import Memory
    assert db_session.query(Memory).count() == 0
