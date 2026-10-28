import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from coros_worker import run_sync
from models import SourceControl, User

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
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    response = {'content': [{'type': 'text', 'text': json.dumps(SAMPLE)}], 'isError': False}
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(response))) as run:
        assert run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))['inserted'] == 1
        assert run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))['inserted'] == 0
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
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='sensitive')):
        with pytest.raises(RuntimeError, match='COROS request failed'):
            run_sync(db_session, 1, helper, state)
    from models import Memory
    assert db_session.query(Memory).count() == 0


def test_checkpoint_catches_up_and_failure_does_not_advance(db_session, config):
    from datetime import date
    from models import SyncState
    helper, state, _ = config
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.add(SyncState(user_id=1, source='coros', last_success_date='2026-10-01'))
    db_session.commit()
    body = {'content': [{'type': 'text', 'text': json.dumps(SAMPLE)}], 'isError': False}
    ok = SimpleNamespace(returncode=0, stdout=json.dumps(body))
    with patch('coros_worker.subprocess.run', return_value=ok) as run:
        run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))
        arguments = json.loads(run.call_args.args[0][-1])
        assert arguments['startDate'] == '20261001'
        assert arguments['endDate'] == '20261027'
    assert db_session.query(SyncState).one().last_success_date == '2026-10-27'
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='secret')):
        with pytest.raises(RuntimeError):
            run_sync(db_session, 1, helper, state, today=date(2026, 10, 28))
    db_session.expire_all()
    assert db_session.query(SyncState).one().last_success_date == '2026-10-27'
    with patch('coros_worker.subprocess.run') as run:
        with pytest.raises(RuntimeError, match='exceeds 30 days'):
            run_sync(db_session, 1, helper, state, today=date(2026, 11, 26))
        run.assert_not_called()
    assert db_session.query(SyncState).one().last_success_date == '2026-10-27'


def test_failed_commit_rolls_back_records_and_checkpoint(db_session, config):
    from datetime import date
    from models import Memory, SyncState
    helper, state, _ = config
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    body = {'content': [{'type': 'text', 'text': json.dumps(SAMPLE)}], 'isError': False}
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(body))):
        from integrations.coros_sync import import_sport_records
        def fail_after_insert(*args, **kwargs):
            import_sport_records(*args, **kwargs)
            raise RuntimeError('simulated failure')
        with patch('integrations.coros_sync.import_sport_records', side_effect=fail_after_insert):
            with pytest.raises(RuntimeError, match='simulated failure'):
                run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))
    assert db_session.query(Memory).count() == 0
    assert db_session.query(SyncState).count() == 0


def test_out_of_range_result_never_advances_checkpoint(db_session, config):
    from models import Memory, SyncState
    from integrations.coros_records import CorosResponseError
    helper, state, _ = config
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    body = {'content': [{'type': 'text', 'text': json.dumps(SAMPLE)}], 'isError': False}
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(body))):
        with pytest.raises(CorosResponseError):
            run_sync(db_session, 1, helper, state, today=date(2026, 10, 10))
    assert db_session.query(Memory).count() == 0
    assert db_session.query(SyncState).count() == 0


def test_removed_token_is_restored_after_failed_refresh(db_session, config):
    helper, state, token = config
    token.write_text('original credential')
    token.chmod(0o600)
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    def failed_refresh(*args, **kwargs):
        token.unlink()
        return SimpleNamespace(returncode=1, stdout='secret')
    with patch('coros_worker.subprocess.run', side_effect=failed_refresh):
        with pytest.raises(RuntimeError):
            run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))
    assert token.read_text() == 'original credential'
    assert token.stat().st_mode & 0o777 == 0o600
    assert not list(state.glob('.token-recovery-*'))
    from models import SyncState, Memory
    assert db_session.query(SyncState).count() == 0
    assert db_session.query(Memory).count() == 0


def test_refreshed_token_is_never_overwritten_on_later_failure(db_session, config):
    helper, state, token = config
    token.write_text('old credential')
    token.chmod(0o600)
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    def refreshed_but_query_failed(*args, **kwargs):
        token.write_text('new credential')
        return SimpleNamespace(returncode=1, stdout='secret')
    with patch('coros_worker.subprocess.run', side_effect=refreshed_but_query_failed):
        with pytest.raises(RuntimeError):
            run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))
    assert token.read_text() == 'new credential'


def test_helper_timeout_restores_removed_token(db_session, config):
    import subprocess
    helper, state, token = config
    token.write_text('old credential')
    token.chmod(0o600)
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    def timeout_after_delete(*args, **kwargs):
        token.unlink()
        raise subprocess.TimeoutExpired(cmd='helper', timeout=60)
    with patch('coros_worker.subprocess.run', side_effect=timeout_after_delete):
        with pytest.raises(RuntimeError, match='timed out'):
            run_sync(db_session, 1, helper, state, today=date(2026, 10, 27))
    assert token.read_text() == 'old credential'


def test_failure_codes_never_include_exception_text():
    from coros_worker import failure_code
    from integrations.coros_records import CorosResponseError
    assert failure_code(RuntimeError('sync gap exceeds 30 days; manual recovery is required')) == 'recovery_required'
    assert failure_code(CorosResponseError('private data')) == 'invalid_or_incomplete_response'
    assert failure_code(RuntimeError('secret-token-or-private-data')) == 'internal_error'


def test_explicit_recovery_commits_each_window_and_resumes_after_failure(db_session, config):
    from models import Memory, SyncState
    helper, state, _ = config
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.add(SyncState(user_id=1, source='coros', last_success_date='2026-09-01'))
    db_session.commit()
    empty = {'content': [{'type': 'text', 'text': json.dumps('Sport Records (0 records)\n')}], 'isError': False}
    ok = SimpleNamespace(returncode=0, stdout=json.dumps(empty))
    failed = SimpleNamespace(returncode=1, stdout='private error')
    with patch('coros_worker.subprocess.run', side_effect=[ok, failed]) as run:
        with pytest.raises(RuntimeError):
            run_sync(db_session, 1, helper, state, today=date(2026, 10, 27), recover=True)
        ranges = [json.loads(call.args[0][-1]) for call in run.call_args_list]
    assert [(r['startDate'], r['endDate']) for r in ranges] == [('20260901', '20260930'), ('20261001', '20261027')]
    db_session.expire_all()
    assert db_session.query(SyncState).one().last_success_date == '2026-09-30'
    assert db_session.query(Memory).count() == 0
    body = {'content': [{'type': 'text', 'text': json.dumps(SAMPLE)}], 'isError': False}
    with patch('coros_worker.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(body))) as run:
        result = run_sync(db_session, 1, helper, state, today=date(2026, 10, 27), recover=True)
        args = json.loads(run.call_args.args[0][-1])
        assert (args['startDate'], args['endDate']) == ('20260930', '20261027')
    assert result['inserted'] == 1
    assert db_session.query(SyncState).one().last_success_date == '2026-10-27'


def test_command_line_sync_end_to_end_without_private_log_output(db_session, config):
    """Exercise the scheduler entry point against an isolated database and fake provider."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    from datetime import datetime, timezone
    from models import Memory, SyncState

    helper, state, token = config
    token.write_text('test-secret-never-log')
    token.chmod(0o600)
    db_session.add(User(id=1, username='runner', password_hash='unused'))
    db_session.add(SourceControl(user_id=1, source='coros', status='active', generation=0))
    db_session.commit()
    now = datetime.now(timezone.utc)
    stamp = int(now.timestamp())
    record = (f'Sport Records (1 records)\n1. Synthetic Run — {now.date()}\n'
              f'   Time Window: startTimestamp={stamp} | endTimestamp={stamp + 60}\n'
              '   LabelId: 777 | SportType: 100\n')
    result = {'content': [{'type': 'text', 'text': json.dumps(record)}], 'isError': False}
    helper.write_text('import sys\nprint(' + repr(json.dumps(result)) + ')\nprint("test-secret-never-log", file=sys.stderr)\n')
    env = dict(os.environ, DATABASE_URL=str(db_session.get_bind().url))
    worker = Path(__file__).resolve().parents[1] / 'coros_worker.py'
    cmd = [sys.executable, str(worker), '--user-id', '1', '--helper', str(helper), '--state-dir', str(state)]
    first = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=20)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)['inserted'] == 1
    assert 'test-secret-never-log' not in first.stdout + first.stderr
    second = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=20)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)['inserted'] == 0
    db_session.expire_all()
    assert db_session.query(Memory).count() == 1
    assert db_session.query(SyncState).count() == 1
    helper.write_text('import sys\nprint("test-secret-never-log", file=sys.stderr)\nsys.exit(1)\n')
    failed = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=20)
    assert failed.returncode == 1
    assert 'provider_or_authorization_error' in failed.stderr
    assert 'test-secret-never-log' not in failed.stdout + failed.stderr
