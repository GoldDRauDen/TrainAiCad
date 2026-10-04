import json
import sys
from pathlib import Path
import yaml
root = Path(sys.argv[1])
router = yaml.safe_load((root / 'skills/lispcad/router/ROUTER.yaml').read_text())
coverage = yaml.safe_load((root / 'skills/lispcad/router/RULE_COVERAGE.yaml').read_text())
print(json.dumps({'router': router, 'coverageRelease': coverage['release']}))
