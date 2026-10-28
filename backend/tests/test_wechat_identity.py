import json
from urllib.error import URLError
import pytest
from identity.wechat import WeChatCodeExchange, WeChatConfig, WeChatExchangeError
from identity.bindings import VerifiedIdentity

CONFIG = WeChatConfig(app_id='fake-app', app_secret='fake-secret')


def test_success_returns_only_app_scoped_identity():
    calls = []
    def handler(params):
        calls.append(params)
        return json.dumps({'openid': 'fake-openid', 'session_key': 'fake-session'}).encode()
    identity = WeChatCodeExchange(CONFIG, exchange_http=handler).exchange('fake-one-time-code')
    assert identity == VerifiedIdentity('wechat', 'fake-app\0fake-openid')
    assert 'fake-session' not in repr(identity)
    assert len(calls) == 1 and calls[0]['grant_type'] == 'authorization_code'
    assert 'fake-secret' not in repr(CONFIG)


@pytest.mark.parametrize('body', [
    b'{"errcode":40029,"errmsg":"fake-secret"}',
    b'{"openid":"id"}',
    b'{"openid":"id","session_key":"key","errcode":true}',
    b'[]', b'bad-json', b'x' * 16385,
])
def test_bad_response_is_rejected_without_leaking_secrets(body):
    adapter = WeChatCodeExchange(CONFIG, exchange_http=lambda params: body)
    with pytest.raises(WeChatExchangeError) as error:
        adapter.exchange('fake-one-time-code')
    assert all(s not in str(error.value) for s in ('fake-secret', 'fake-one-time-code', 'fake-session'))


def test_timeout_is_not_retried_and_error_is_sanitized():
    calls = []
    def timeout(params):
        calls.append(1)
        raise URLError('fake-secret fake-one-time-code')
    with pytest.raises(WeChatExchangeError) as error:
        WeChatCodeExchange(CONFIG, exchange_http=timeout).exchange('fake-one-time-code')
    assert len(calls) == 1 and str(error.value) == 'provider unavailable'
    assert error.value.__suppress_context__


def test_invalid_code_does_not_call_provider():
    def unexpected(params):
        raise AssertionError('should not make network call')
    adapter = WeChatCodeExchange(CONFIG, exchange_http=unexpected)
    for code in ('', ' ', 'x' * 513):
        with pytest.raises(WeChatExchangeError):
            adapter.exchange(code)


def test_transport_limits_reads_and_disables_redirects(monkeypatch):
    from identity import wechat
    observed = {}
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit):
            observed['limit'] = limit
            return b'{}'
    class FakeOpener:
        def open(self, request, timeout):
            observed['request'] = request
            observed['timeout'] = timeout
            return FakeResponse()
    def fake_builder(*handlers):
        observed['handlers'] = handlers
        return FakeOpener()
    monkeypatch.setattr(wechat, 'build_opener', fake_builder)
    assert wechat._exchange_http({'secret': 'fake-secret'}) == b'{}'
    assert observed['limit'] == 16385 and observed['timeout'] == 5
    assert observed['request'].full_url.startswith('https://api.weixin.qq.com/sns/jscode2session?')
    assert any(isinstance(h, wechat._NoRedirect) for h in observed['handlers'])
    assert wechat._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid/') is None
