"""Explicitly separate public MSC reference inputs from original service inputs.

CPU only. MSC parity is against the pinned public implementation, not an FX3
initial-MSC verifier. This module neither authorizes nor implements USB access.
"""
from dataclasses import dataclass,field
from pathlib import Path
from hashlib import sha1,sha256
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
SERVICE=BASE/'stage141-public-auth-digest-and-original-verifier'
SERVICE_MANIFEST='2800a952e5a4a960ba9c98463048cdebf6e4f27a0c1ae8b48fe6be3cae162866'


class UnsupportedInput(ValueError):pass


@dataclass(frozen=True)
class Profile:
    mode:str
    vid:int
    pid:int


@dataclass(frozen=True)
class BoundTask:
    token:str
    profile:Profile
    challenge_code:int
    round_index:int
    challenge:bytes=field(repr=False)


def _service_provider():
    manifest=SERVICE/'final-receipt.json'
    if sha256(manifest.read_bytes()).hexdigest()!=SERVICE_MANIFEST:raise UnsupportedInput('service source manifest mismatch')
    path=SERVICE/'public_digest_provider.py'
    member=next(x for x in json.loads(manifest.read_text())['files'] if x['path']==path.relative_to(ROOT).as_posix())
    if path.stat().st_size!=member['bytes'] or sha256(path.read_bytes()).hexdigest()!=member['sha256']:
        raise UnsupportedInput('service provider pin mismatch')
    spec=importlib.util.spec_from_file_location('fixed_service_only_digest',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.FX3PublicDigestProvider()


def validate_profile(profile):
    if type(profile) is not Profile or type(profile.mode) is not str or type(profile.vid) is not int or type(profile.pid) is not int:
        raise UnsupportedInput('explicit typed USB profile required')
    if (profile.mode,profile.vid,profile.pid) not in {('MSC',0x054c,0x0da1),('SERVICE',0x054c,0x0336)}:
        raise UnsupportedInput('mode and VID/PID disagree or are unsupported')


class ModeDigestProvider:
    def __init__(self):
        self.service=_service_provider();self.used_tokens=set()

    def compute(self,profile,challenge_code,round_index,challenge):
        validate_profile(profile)
        if type(challenge_code) is not int or type(round_index) is not int or not 0<=round_index<3:
            raise UnsupportedInput('invalid challenge family or round')
        if type(challenge) is not bytes or len(challenge)!=512:
            raise UnsupportedInput('exact immutable 512-byte challenge required')
        if profile.mode=='SERVICE':
            if challenge_code!=8:raise UnsupportedInput('fixed original FX3 service verifier only proves family8')
            return self.service.compute(8,round_index,challenge)
        # Pinned PMCA's non-0336 branch hashes ONLY the first4 bytes. For that
        # exact length, its legacy SHA1 length bug has no effect: 4 & 31 == 4.
        if challenge_code==2:return sha1(challenge[:4]).digest()
        if challenge_code==8:return sha256(challenge[:4]).digest()
        raise UnsupportedInput('unreviewed initial-MSC public reference family')

    def bind_inert_task(self,controller,action):
        if controller.pending is not action or controller.phase!='DERIVE_DIGEST' or action.phase!='DERIVE_DIGEST' or action.inert_only is not True:
            raise UnsupportedInput('digest action is not the current pending inert task')
        if controller.mode not in ('MSC','SERVICE') or controller.auth_resume!='AUTH_'+controller.mode:
            raise UnsupportedInput('digest mode is missing or inconsistent with authentication phase')
        if controller.family!=action.digest_family or controller.round!=action.digest_round or controller.challenge!=action.private_payload:
            raise UnsupportedInput('digest task no longer matches pending challenge')
        if not action.issued_at<=controller.last_now<=action.deadline:
            raise UnsupportedInput('digest task is outside its controller time window')
        profile=Profile(controller.mode,0x054c,0x0da1 if controller.mode=='MSC' else 0x0336)
        return BoundTask(action.token,profile,action.digest_family,action.digest_round,action.private_payload)

    def compute_bound_task(self,task):
        if type(task) is not BoundTask or type(task.token) is not str or not 8<=len(task.token)<=128 or task.token in self.used_tokens or len(self.used_tokens)>=6:
            raise UnsupportedInput('duplicate or excessive bounded digest task')
        result=self.compute(task.profile,task.challenge_code,task.round_index,task.challenge)
        self.used_tokens.add(task.token)
        return result


if __name__=='__main__':
    sys.exit('CPU provider only; there is no device command-line entrypoint')
