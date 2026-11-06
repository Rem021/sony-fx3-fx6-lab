"""CLI exposes local-file operations only; no camera transport exists."""
import argparse
import json
from .engine import inspect_image, create_bundle, load_bundle, diagnose, rollback
from .fat import MAX_P1
from .files import read_file, encode, new_directory
from .capture import capture_local, verify_capture
from .worker import assemble_worker_windows
from .elflink import build_worker
from . import boot_worker as B


def main():
    p = argparse.ArgumentParser(description='FX3 7.02 recovery adaptation v0.5 — local files only')
    sub = p.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='inspect a local logical/decrypted P1 image')
    inspect.add_argument('--input', required=True);inspect.add_argument('--out', required=True)
    build = sub.add_parser('build', help='build a local reference-profile candidate and preserve full original')
    build.add_argument('--input', required=True);build.add_argument('--out', required=True)
    build.add_argument('--scope', choices=['reference', 'unverified-snapshot'], default='reference')
    build.add_argument('--body-tag', help='opaque64hex operator tag; never a serial; not device-verified')
    verify = sub.add_parser('verify', help='verify all image hashes and exact transformation')
    verify.add_argument('--bundle', required=True)
    state = sub.add_parser('diagnose', help='classify original/candidate/mixed/unknown local image')
    state.add_argument('--bundle', required=True);state.add_argument('--input', required=True)
    restore = sub.add_parser('rollback', help='create an exact local backup reconstruction in a new directory')
    restore.add_argument('--bundle', required=True);restore.add_argument('--input', required=True);restore.add_argument('--out', required=True)
    capture = sub.add_parser('capture-local', help='bounded capture of an existing full local P1 file; no camera provider')
    capture.add_argument('--input', required=True);capture.add_argument('--out', required=True)
    capture.add_argument('--sha256', required=True, help='external expected whole-file SHA-256')
    capture.add_argument('--body-tag', required=True, help='opaque64hex local grouping tag; never camera attestation')
    captured = sub.add_parser('verify-capture', help='verify complete local capture evidence with an external digest')
    captured.add_argument('--capture', required=True);captured.add_argument('--sha256', required=True)
    worker = sub.add_parser('assemble-worker', help='decode three saved worker windows; never loads or executes native code')
    worker.add_argument('--windows',nargs=3,required=True)
    worker.add_argument('--returns',nargs=3,type=int,required=True,help='separately recorded producer return codes; caller supplied, not attested')
    worker.add_argument('--out',required=True);worker.add_argument('--body-tag',required=True)
    linker = sub.add_parser('build-worker', help='compile/link our pinned sources locally; never executes the ELF or accesses a camera')
    linker.add_argument('--out',required=True)
    bootreq = sub.add_parser('boot-request', help='create a local boot0/boot1 request file; no upload or execution')
    bootreq.add_argument('--capture-id',required=True);bootreq.add_argument('--target',choices=['boot0','boot1'],required=True)
    bootreq.add_argument('--window',type=int,required=True);bootreq.add_argument('--expected-total',type=int,default=0)
    bootreq.add_argument('--out',required=True)
    bootbuild = sub.add_parser('build-boot-worker', help='compile/link boot reader candidate locally; never launches it')
    bootbuild.add_argument('--out',required=True)
    bootassemble = sub.add_parser('assemble-boot-worker', help='verify/assemble one to four saved boot windows locally')
    bootassemble.add_argument('--windows',nargs='+',required=True)
    bootassemble.add_argument('--returns',nargs='+',type=int,required=True)
    bootassemble.add_argument('--out',required=True);bootassemble.add_argument('--body-tag',required=True)
    args = p.parse_args()
    try:
        if args.command == 'inspect':
            result = inspect_image(read_file(args.input, MAX_P1))
            new_directory(args.out, {'inspection.json': encode(result)})
        elif args.command == 'build':
            result = create_bundle(args.input, args.out, args.scope, args.body_tag)
        elif args.command == 'verify':
            manifest, source, candidate = load_bundle(args.bundle)
            result = {'status': 'VERIFIED_OFFLINE_ONLY', 'source_sha256': manifest['source_sha256'],
                      'candidate_sha256': manifest['candidate_sha256'], 'flashable': False}
        elif args.command == 'diagnose':
            result = diagnose(args.bundle, args.input)
        elif args.command == 'rollback':
            result = rollback(args.bundle, args.input, args.out)
        elif args.command == 'capture-local':
            result = capture_local(args.input, args.out, args.sha256, args.body_tag)
        elif args.command == 'verify-capture':
            result = verify_capture(args.capture, args.sha256)
        elif args.command == 'assemble-worker':
            result = assemble_worker_windows(args.windows,args.returns,args.out,args.body_tag)
        elif args.command == 'build-worker':
            result = build_worker(args.out)
        elif args.command == 'boot-request':
            result = B.create_request(args.capture_id,args.target,args.window,args.expected_total,args.out)
        elif args.command == 'build-boot-worker':
            result = B.build_worker(args.out)
        elif args.command == 'assemble-boot-worker':
            result = B.assemble_windows(args.windows,args.returns,args.out,args.body_tag)
        else:
            raise ValueError('unknown local operation')
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'REJECTED', 'error_type': type(error).__name__, 'error': str(error),
                          'camera_operations': 0, 'automatic_retry': False}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
