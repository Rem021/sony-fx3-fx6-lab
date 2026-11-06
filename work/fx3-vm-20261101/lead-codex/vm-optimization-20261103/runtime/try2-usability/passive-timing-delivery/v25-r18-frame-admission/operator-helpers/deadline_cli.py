#!/usr/bin/env python3
"""Explicit current-tab operations only; no navigation, HTTP, keys or confirmation."""
import argparse
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def browser(session, args, source=None):
    p = subprocess.run(['agent-browser', '--session', session, *args], input=source,
                       text=True, capture_output=True, timeout=15)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return p.stdout


def operate(session, url, launch_id, action, nonce=None):
    if not re.fullmatch(r'fx3-deadline-[a-zA-Z0-9_-]+', session):
        raise ValueError('Use an explicitly owned fx3-deadline-* session, never default/CDP attachment')
    tabs = json.loads(browser(session, ['tab', '--json']))['data']['tabs']
    if len(tabs) != 1 or tabs[0]['url'] != url:
        raise ValueError('Exactly one dedicated tab with the exact current URL is required')
    config = {'expectedURL': url, 'expectedLaunchId': launch_id}
    if action == 'install':
        code = (HERE / 'deadline.js').read_text() + '(' + json.dumps(config) + ')'
    else:
        # Recheck caller identity before invoking the captured document's API.
        code = '''(() => {
          const c=CONFIG;
          if(location.href!==c.expectedURL||lastStatus.launch_request_id!==c.expectedLaunchId)
            throw Error('caller page identity mismatch');
          const a=window.__fx3InteractionDeadlineV1;
          if(!a)throw Error('helper not installed in this document');
          return a[ACTION](NONCE);
        })()'''.replace('CONFIG', json.dumps(config)).replace('ACTION', json.dumps(action)).replace('NONCE', json.dumps(nonce))
    result = json.loads(browser(session, ['eval', '--stdin'], code))
    if action == 'arm' and (not result.get('current') or result['current']['nonce'] != nonce
                            or result['current']['state'] != 'armed'):
        raise RuntimeError('Arm was refused; inspect retained alarm: ' + json.dumps(result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['install', 'arm', 'cancel', 'status', 'dispose'])
    p.add_argument('--session', required=True)
    p.add_argument('--url', required=True, help='Full exact http://127.0.0.1:PORT/ including slash')
    p.add_argument('--launch-id', required=True)
    p.add_argument('--nonce', help='New UUID for arm; exact armed UUID for cancel')
    a = p.parse_args()
    if a.action in ('arm', 'cancel') and not a.nonce:
        p.error('--nonce required')
    print(json.dumps(operate(a.session, a.url, a.launch_id, a.action, a.nonce),
                     ensure_ascii=False, indent=2))
