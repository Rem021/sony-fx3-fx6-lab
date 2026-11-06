#!/usr/bin/env python3
"""Read-only post-run comparison. Never upgrades missing evidence to PASS."""
import argparse
import json
from pathlib import Path
from ab_observer import ARMS


def arm(path, expected):
    obs_path = path/'ab-zero-key-observation.json'
    receipt_path = path/'receipt.json'
    if not obs_path.exists() or not receipt_path.exists():
        return {'arm':expected, 'classification':'inconclusive_missing_receipt'}
    obs = json.loads(obs_path.read_text())
    rec = json.loads(receipt_path.read_text())
    run = str(path.resolve())
    identity_ok = (obs.get('arm') == expected and obs.get('run') == run
                   and rec.get('run') == run
                   and obs.get('candidate_sha256') == ARMS[expected]['candidate']
                   and obs.get('cpio_sha256') == ARMS[expected]['cpio']
                   and rec.get('candidate_sha256') == ARMS[expected]['candidate'])
    result = {'arm':expected, 'decision':obs.get('decision'),
              'run_identity_ok':identity_ok,
              'screen0_ns':obs.get('observation',{}).get('screen0_ns'),
              'first_commit_ns':obs.get('observation',{}).get('first_commit_ns'),
              'latest_poll_ns':obs.get('observation',{}).get('latest_poll_ns'),
              'steps':rec.get('key_steps'), 'stop_cause':rec.get('stop_cause'),
              'render_pass':rec.get('render_pass'),
              'API16_restored':rec.get('cleanup',{}).get('API16_restored'),
              'qemu_exit':rec.get('qemu_exit'), 'process_reaped':rec.get('process_reaped'),
              'locks':rec.get('locks'), 'inputs_unchanged':rec.get('inputs_unchanged')}
    if not identity_ok or rec.get('inputs_unchanged') is not True:
        result['classification']='inconclusive_identity_or_inputs'
    elif rec.get('key_steps') != 0 or obs.get('decision') in ('protocol_fault_nonzero_key','storage_or_status_unavailable'):
        result['classification']='inconclusive_protocol_or_storage'
    elif rec.get('host_observer_error') or rec.get('stop_cause') == 'host_error':
        result['classification']='inconclusive_host_failure'
    elif obs.get('decision') == 'startup_incomplete':
        result['classification']='startup_incomplete'
    elif obs.get('decision') in ('first_host_verified_frame','no_commit_or_verified_frame_after_60_guest_seconds',
                                 'commit_seen_visual_unverified_after_60_guest_seconds'):
        result['classification']=obs['decision']
    else:
        result['classification']='inconclusive_other'
    return result


def compare(a_path, b_path):
    a=arm(a_path,'A');b=arm(b_path,'B')
    comparable=('first_host_verified_frame','no_commit_or_verified_frame_after_60_guest_seconds',
                'commit_seen_visual_unverified_after_60_guest_seconds')
    same_mode=(a['classification'] in comparable and b['classification'] in comparable)
    return {'A':a,'B':b,'paired_observation_mode_eligible':same_mode,
                      'paired_observation_comparable':False,
                      'storage_window_verified':False,
                      'note':'Mode eligibility is not causal comparability. Check kernel USB/APFS events for both windows; lifecycle gates remain separate.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--a',type=Path,required=True);p.add_argument('--b',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(compare(args.a,args.b), ensure_ascii=False,indent=2))


if __name__=='__main__':main()
