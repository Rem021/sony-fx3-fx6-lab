"""Offline shell-source generation only; no app, sudo, root or USB launcher."""
from pathlib import Path
import json
import re
import shlex

def render_user_channel(invocation,directory,grant,nonce):
    """The outer user shell owns stdout. Verification stderr stays on its TTY.

    invocation must be trusted reviewed shell source, not external/user input.
    This function returns text and never executes it. A real device integration
    still requires a new fixed grant/bundle and the complete entry supervisor.
    """
    directory=Path(directory)
    if not directory.is_absolute() or not re.fullmatch(r'fx3-[a-z0-9-]{1,80}',grant) or not re.fullmatch(r'[0-9a-f]{32}',nonce):
        raise ValueError('reviewed absolute directory, grant and nonce required')
    q=lambda s:shlex.quote(str(s))
    status=json.dumps({'schema':1,'grant_id':grant,'nonce':nonce,'returncode':'CODE'},separators=(',',':')).replace('"CODE"','%s')+'\n'
    return '\n'.join(['#!/bin/sh','set -euC','cd /','umask 077',
        '/bin/mkdir -m 700 '+q(directory/'terminal-command.once'),
        'if '+invocation+' > '+q(directory/'relay-stdout.txt')+'; then',
        '    code=0','else','    code=$?','fi',
        'printf '+q(status)+' "$code" > '+q(directory/'terminal-command-result.json'),
        'exit "$code"',''])

if __name__=='__main__':
    print(json.dumps({'state':'PLAN_ONLY_OFFLINE_RECEIPT_CHANNEL','camera_operations':0,
        'root_or_Terminal_executed':False,'apply_to_consumed05_supported':False}))
