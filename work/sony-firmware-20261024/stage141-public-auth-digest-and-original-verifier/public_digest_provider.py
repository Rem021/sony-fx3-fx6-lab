"""Bounded CPU-only FX3 7.02 SHA-256 response provider using fixed public material.

No USB, authentication request, firmware or camera-file operation is implemented.
The public PMCA data is MIT licensed; preserve upstream/LICENSE.txt with it.
"""
from pathlib import Path
import ast
import hashlib

PUBLIC_CONSTANTS_SHA256 = '94bf081d3c1a51a60cf8fc214dce25a491413d4d786716460fde3fba832eb692'
UPSTREAM = Path(__file__).resolve().parent / 'upstream/constants.py'


class UnsupportedInput(ValueError):
    pass


def parse_sha256_material(raw):
    """Literal AST data only; never import or execute the upstream constants file."""
    tree = ast.parse(raw)
    nodes = [n for n in tree.body if isinstance(n, ast.Assign)
             and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id == 'senserKeysSha256']
    if len(nodes) != 1:
        raise UnsupportedInput('expected one fixed material table')
    material = ast.literal_eval(nodes[0].value)
    if not isinstance(material, list) or len(material) != 3:
        raise UnsupportedInput('expected three material blocks')
    if not all(isinstance(x, bytes) and len(x) == 512 for x in material):
        raise UnsupportedInput('expected512 byte literal material blocks')
    return tuple(material)


class FX3PublicDigestProvider:
    """Load pinned public data once; subsequent compute() is a bounded SHA-256 call."""
    def __init__(self):
        raw = UPSTREAM.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PUBLIC_CONSTANTS_SHA256:
            raise UnsupportedInput('public source pin mismatch')
        self._material = parse_sha256_material(raw)

    def compute(self, challenge_code, round_index, challenge):
        if type(challenge_code) is not int or challenge_code != 8:
            raise UnsupportedInput('this fixed FX3 verifier uses challenge code8')
        if type(round_index) is not int or not 0 <= round_index < 3:
            raise UnsupportedInput('round index must be0,1,2')
        if not isinstance(challenge, bytes) or len(challenge) != 512:
            raise UnsupportedInput('challenge must be512 bytes')
        return hashlib.sha256(challenge + self._material[round_index]).digest()

    def compute_inert_task(self, action):
        if action.inert_only is not True or action.phase != 'DERIVE_DIGEST':
            raise UnsupportedInput('expected a separately timed inert digest task')
        return self.compute(action.digest_family, action.digest_round, action.private_payload)
