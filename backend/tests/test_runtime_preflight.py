import base64
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'deploy/check_runtime.py'
spec = importlib.util.spec_from_file_location('runtime_check', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def example():
    return {'JWT_SECRET_KEY': 'x' * 32, 'BAOBU_WECHAT_EXPERIMENTAL': '1',
            'BAOBU_PASSWORD_RATE_LIMIT': '1', 'BAOBU_TRUSTED_PROXY_CIDRS': '127.0.0.1/32',
            'BAOBU_WECHAT_APP_ID': 'fake-app', 'BAOBU_WECHAT_APP_SECRET': 'fake-secret',
            'BAOBU_IDENTITY_HMAC_KEY': base64.b64encode(b'fake-key-only-' * 3).decode()}


def test_complete_synthetic_configuration():
    assert module.check(example(), require_wechat=True, require_password_limits=True) == []


def test_required_flags_and_missing_secrets_fail():
    assert module.check({}, require_wechat=True, require_password_limits=True)
    values = example()
    values['BAOBU_WECHAT_EXPERIMENTAL'] = 'true'
    assert module.check(values, require_wechat=True)
    values = example()
    values['BAOBU_IDENTITY_HMAC_KEY'] = 'bad'
    assert module.check(values)
    values = example()
    values['BAOBU_WECHAT_APP_SECRET'] = ' '
    assert module.check(values)


def test_invalid_and_wildcard_proxy_fail():
    for proxy in ('', '0.0.0.0/0', '::/0', 'bad'):
        values = example()
        values['BAOBU_TRUSTED_PROXY_CIDRS'] = proxy
        assert any('proxy' in issue for issue in module.check(values))


def test_cli_never_prints_secret_values():
    values = example()
    values['BAOBU_WECHAT_APP_SECRET'] = 'fake-sensitive-value' * 30
    result = subprocess.run([sys.executable, str(SCRIPT), '--require-wechat'], env={**os.environ, **values},
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert 'fake-sensitive-value' not in result.stdout + result.stderr
