#!/usr/bin/env python3
"""Inspect environment configuration without printing secrets or connecting to services."""
import argparse
import base64
import binascii
import ipaddress
import os
import sys


def check(env, *, require_wechat=False, require_password_limits=False):
    issues = []
    jwt = env.get('JWT_SECRET_KEY', '')
    if len(jwt.strip()) < 32:
        issues.append('JWT_SECRET_KEY missing or too short')
    wechat = env.get('BAOBU_WECHAT_EXPERIMENTAL', '')
    password_limits = env.get('BAOBU_PASSWORD_RATE_LIMIT', '')
    if wechat not in ('', '1') or (require_wechat and wechat != '1'):
        issues.append('WeChat identity is disabled or its flag is invalid')
    if password_limits not in ('', '1') or (require_password_limits and password_limits != '1'):
        issues.append('Password rate limit is disabled or its flag is invalid')
    if wechat == '1' or password_limits == '1':
        try:
            key = base64.b64decode(env.get('BAOBU_IDENTITY_HMAC_KEY', ''), validate=True)
            if len(key) < 32:
                raise ValueError('short key')
        except (ValueError, binascii.Error):
            issues.append('Identity HMAC key missing or invalid')
        proxy = env.get('BAOBU_TRUSTED_PROXY_CIDRS', '')
        try:
            networks = [ipaddress.ip_network(part.strip(), strict=False) for part in proxy.split(',') if part.strip()]
            if not networks or any(net.prefixlen == 0 for net in networks):
                raise ValueError('invalid proxy')
        except ValueError:
            issues.append('Trusted proxy networks missing or invalid; verify actual proxy chain')
    if wechat == '1':
        for name in ('BAOBU_WECHAT_APP_ID', 'BAOBU_WECHAT_APP_SECRET'):
            value = env.get(name, '')
            if not value.strip() or len(value) > 256:
                issues.append(name + ' missing or invalid')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-wechat', action='store_true')
    parser.add_argument('--require-password-limits', action='store_true')
    args = parser.parse_args()
    issues = check(os.environ, require_wechat=args.require_wechat,
                   require_password_limits=args.require_password_limits)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print('Environment format checks passed.')
    print('WeChat identity: ' + ('enabled' if os.environ.get('BAOBU_WECHAT_EXPERIMENTAL') == '1' else 'disabled'))
    print('Password limits: ' + ('enabled' if os.environ.get('BAOBU_PASSWORD_RATE_LIMIT') == '1' else 'disabled'))
    print('Verify secret strength, HTTPS, actual proxy chain, logs, schema and provider connectivity separately.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
