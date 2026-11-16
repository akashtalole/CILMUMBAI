"""Check the specs for traceability.

- Every requirement (Rn) is verified by at least one acceptance criterion.
- Every acceptance criterion names requirements that exist.
- The progress table in 02-spec-index.md has the right number of criteria per spec.

Run: python aamcha-hishob-specs/tools/check_specs.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
problems = []

index = (ROOT / "02-spec-index.md").read_text(encoding="utf-8")

for path in sorted((ROOT / "specs").glob("SPEC-*.md")):
    text = path.read_text(encoding="utf-8")
    spec = path.name[:8]
    requirements = set(re.findall(r"^\| (R\d+) \|", text, re.M))
    criteria = re.findall(r"^\| (AC\d+) \|.*\| ([R\d, ]+) \|$", text, re.M)
    verified = {r.strip() for _, refs in criteria for r in refs.split(",") if r.strip()}

    for r in sorted(requirements - verified, key=lambda x: int(x[1:])):
        problems.append(f"{spec}: {r} has no acceptance criterion")
    for ac, refs in criteria:
        for r in (x.strip() for x in refs.split(",") if x.strip()):
            if r not in requirements:
                problems.append(f"{spec}: {ac} names {r}, which does not exist")

    row = re.search(rf"^\| {spec} \| [^|]+ \| (\d+) \|", index, re.M)
    if not row:
        problems.append(f"{spec}: missing from the progress table in 02-spec-index.md")
    elif int(row.group(1)) != len({ac for ac, _ in criteria}):
        problems.append(f"{spec}: index says {row.group(1)} criteria, spec has {len(criteria)}")

if problems:
    print("\n".join(problems))
    sys.exit(1)
print("specs: traceability ok")
