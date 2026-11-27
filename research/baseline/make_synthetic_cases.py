"""Generate deterministic boundary cases for differential testing against cached TS."""
import json
from decimal import Decimal
from pathlib import Path
from catalog import load_catalog
from engine import govern

root = Path(__file__).resolve().parent
rules = load_catalog(root.parent/'data_enrichment')
fixtures = [
    (['yes', 'no'], [100, 99], 100),
    (['yes', 'no'], [100, 100], 100),
    (['yes', 'no'], [99, 98], 100),
    (['yes', 'no'], [0, 0], 0),
    (['Yes', 'No'], [10, 1], 0),
    (['yes', 'no', 'abstain'], [10, 9, 1000], 0),
    (['yes', 'no', 'abstain'], [10, 9, 1000], 11),
    (['accept', 'reject'], [10, 1], 0),
    (['accept', 'reject', 'Invalid question/options'], [10, 1, 0], 0),
    (['for', 'against'], [10, 1], 0),
    (['for', 'against', 'Invalid question/options'], [10, 1, 0], 0),
    (['A', 'B', 'Invalid question/options'], [10, 9, 11], 0),
    (['A', 'B', 'Invalid question/options'], [10, 9, 10], 0),
    (['A', 'A', 'Invalid question/options'], [6, 6, 10], 0),
    (['2', '1', 'Invalid question/options'], [10, 10, 10], 0),
    (['A', 'B'], [0, 0], 0),
    (['A', 'B'], [10, 1], 100),
    (['yes ', 'no'], [10, 1], 0),
]
cases = []
for r in rules:
    for i, (labels, values, floor) in enumerate(fixtures):
        votes = [{'voter': '0x'+str(j+1).zfill(40), 'choice': j+1, 'vp': x} for j, x in enumerate(values)]
        result = govern(tuple(labels), [Decimal(x) for x in values], len(votes), Decimal(floor), r)
        cases.append({'id': r.commit[:8]+':boundary:'+str(i), 'commit': r.commit,
                      'choices': labels, 'totals': values, 'threshold': floor, 'votes': votes,
                      'python_outcome': result.outcome})
    result = govern(('yes', 'no'), [Decimal(0), Decimal(0)], 0, Decimal(0), r)
    cases.append({'id': r.commit[:8]+':empty', 'commit': r.commit, 'choices': ['yes', 'no'],
                  'totals': [0, 0], 'threshold': 0, 'votes': [], 'python_outcome': result.outcome})
(root/'SYNTHETIC_CASES.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
print('Synthetic source parity cases:', len(cases))
