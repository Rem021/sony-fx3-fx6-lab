#!/usr/bin/env python3
"""Run the sealed profile proof into a new directory, never overwrite results."""
from pathlib import Path
import argparse, hashlib, json, plistlib, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ALLOWED_ROOT = HERE.parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New nonexistent directory under stage12-prototype; old results are refused')
    args=parser.parse_args()
    destination=args.output.resolve()
    destination.relative_to(ALLOWED_ROOT)
    if destination.exists():
        raise SystemExit('Refusing existing output directory; supply a new --output path')
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if volume['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise SystemExit('Wrong external volume; no output directory created')
    source_files=[HERE/'profile_prototype.py',HERE/'profile-results.json',HERE/'source-receipt.json',HERE/'review-summary.json']
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    import profile_prototype as proof
    destination.mkdir(parents=True,exist_ok=False)
    # The original proof uses OUT only for its own diagnostics, not dependencies.
    # Redirect those diagnostics before running; no existing stage file is changed.
    proof.OUT=destination
    proof.main()
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    assert before==after
    receipt={'status':'PASS','entry':str(Path(__file__).relative_to(ROOT)),'entry_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'new_output_directory':str(destination.relative_to(ROOT)),'sealed_source_artifacts_before':before,'sealed_source_artifacts_after':after,'prior_results_unchanged':True}
    with (destination/'reproduction-entry.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')

if __name__=='__main__':main()
