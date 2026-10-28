"""WeChat Mini Program code exchange adapter; not exposed as an HTTP endpoint.

AppSecret stays on the server. Returned session_key is discarded. Never log
requests, responses, codes or credentials. A timeout can leave a one-time code's
consumption status unknown, so requests are not retried automatically.
"""
from dataclasses import dataclass, field
import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

from identity.bindings import VerifiedIdentity

_ENDPOINT = 'https://api.weixin.qq.com/sns/jscode2session'
_MAX_RESPONSE = 16384


class WeChatExchangeError(Exception):
    """Sanitized error: no upstream body, URL, identity or credential."""


@dataclass(frozen=True)
class WeChatConfig:
    app_id: str = field(repr=False)
    app_secret: str = field(repr=False)

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip() or len(value) > 256
               for value in (self.app_id, self.app_secret)):
            raise ValueError('WeChat configuration is invalid')


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _exchange_http(params: dict[str, str]) -> bytes:
    # No HTTP library request logging: the provider requires secrets in the URL.
    # Disable environment proxies and redirects to avoid forwarding credentials.
    url = _ENDPOINT + '?' + urlencode(params)
    opener = build_opener(ProxyHandler({}), HTTPSHandler(), _NoRedirect())
    with opener.open(Request(url, headers={'Accept': 'application/json'}), timeout=5) as response:
        if response.status != 200:
            raise WeChatExchangeError('provider unavailable')
        return response.read(_MAX_RESPONSE + 1)


class WeChatCodeExchange:
    def __init__(self, config: WeChatConfig, *, exchange_http=None):
        self._config = config
        self._exchange_http = exchange_http or _exchange_http

    def exchange(self, code: str) -> VerifiedIdentity:
        if not isinstance(code, str) or not code.strip() or len(code) > 512:
            raise WeChatExchangeError('invalid login code')
        try:
            body = self._exchange_http({'appid': self._config.app_id,
                'secret': self._config.app_secret, 'js_code': code, 'grant_type': 'authorization_code'})
            if not isinstance(body, bytes) or len(body) > _MAX_RESPONSE:
                raise WeChatExchangeError('invalid provider response')
            data = json.loads(body)
            if not isinstance(data, dict):
                raise WeChatExchangeError('invalid provider response')
            errcode = data.get('errcode', 0)
            if isinstance(errcode, bool) or not isinstance(errcode, int) or errcode != 0:
                raise WeChatExchangeError('provider rejected login')
            subject, session_key = data.get('openid'), data.get('session_key')
            if (not isinstance(subject, str) or not subject.strip() or len(subject.encode('utf-8')) > 256
                    or not isinstance(session_key, str) or not session_key.strip() or len(session_key) > 512):
                raise WeChatExchangeError('invalid provider response')
            return VerifiedIdentity(provider='wechat', subject=self._config.app_id + '\0' + subject)
        except WeChatExchangeError:
            raise
        except (URLError, OSError, ValueError, UnicodeError):
            raise WeChatExchangeError('provider unavailable') from None
