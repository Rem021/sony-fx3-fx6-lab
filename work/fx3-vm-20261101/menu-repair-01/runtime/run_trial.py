#!/usr/bin/env python3
"""FX3 local menu trial entry point; versioned implementation kept beside it."""
from run_trial_v3 import main
import sys
if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('Stopped:', exc, file=sys.stderr)
        sys.exit(2)
