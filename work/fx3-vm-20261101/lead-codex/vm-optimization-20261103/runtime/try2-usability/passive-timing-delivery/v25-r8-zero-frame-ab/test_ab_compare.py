#!/usr/bin/env python3
"""Small synthetic comparison gate fixtures; no VM or old log replay."""
import json
import tempfile
import copy
from pathlib import Path

from ab_compare import compare
from ab_observer import ARMS


def fixture(root, arm):
    path = root/arm
    path.mkdir()
    obs = {'arm':arm, 'run':str(path.resolve()),
           'candidate_sha256':ARMS[arm]['candidate'],
           'cpio_sha256':ARMS[arm]['cpio'],
           'decision':'first_host_verified_frame',
           'observation':{'screen0_ns':1,'first_commit_ns':2}}
    rec = {'run':str(path.resolve()), 'candidate_sha256':ARMS[arm]['candidate'],
           'inputs_unchanged':True, 'key_steps':0, 'render_pass':True,
           'cleanup':{'API16_restored':True}, 'process_reaped':True}
    write(path, obs, rec)
    return path, obs, rec


def write(path, obs, rec):
    (path/'ab-zero-key-observation.json').write_text(json.dumps(obs))
    (path/'receipt.json').write_text(json.dumps(rec))


with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    a,ao,ar=fixture(root,'A')
    b,bo,br=fixture(root,'B')
    result=compare(a,b)
    assert result['paired_observation_mode_eligible'] is True
    assert result['paired_observation_comparable'] is False
    assert result['storage_window_verified'] is False
    original_obs=copy.deepcopy(ao)
    original_rec=copy.deepcopy(ar)
    for mutate in (
        lambda: ar.__setitem__('inputs_unchanged',False),
        lambda: ar.pop('inputs_unchanged',None),
        lambda: ar.__setitem__('candidate_sha256',ARMS['B']['candidate']),
        lambda: ar.__setitem__('run',str(b.resolve())),
        lambda: ao.__setitem__('arm','B'),
        lambda: ao.__setitem__('run',str(b.resolve())),
        lambda: ao.__setitem__('candidate_sha256',ARMS['B']['candidate']),
        lambda: ao.__setitem__('cpio_sha256',ARMS['B']['cpio']),
    ):
        ao=copy.deepcopy(original_obs)
        ar=copy.deepcopy(original_rec)
        mutate();write(a,ao,ar)
        result=compare(a,b)
        assert result['A']['classification']=='inconclusive_identity_or_inputs',result
        assert result['paired_observation_mode_eligible'] is False
print('PASS identity/input/storage gates; no VM')
