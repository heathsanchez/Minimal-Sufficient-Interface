"""Reproduce the small ARC dependency slice of the pinned global core."""
from __future__ import annotations
import argparse
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'kaggle/src/metalogic_arc3/continuation_core.py'
PIN = '2efa47b2efc27434ed24dbf6ad6e1f50e463f947'
BLOBS = {'crystal.py': '3f3a0547eec2c6b04993494cd12b20a5711eede8',
         'protected_future.py': '0cff202beececa9afea0a28b97363481adc1715b'}
NAMES = {'JSONScalar', 'JSONValue', '_canonical', 'canonical_bytes', 'content_id',
         '_SEMANTIC_OBJECT_MAGIC', '_pack_u32', '_pack_u64', '_pack_text', 'SemanticObject'}


def render(source: Path) -> str:
    texts = {}
    for name, expected in BLOBS.items():
        raw = (source / 'mathgraph' / name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual != expected:
            raise ValueError(f'global source pin mismatch: {name}: {actual}')
        texts[name] = raw.decode('utf-8')
    out = ['"""Generated dependency slice; edit only through the pinned global source.\n'
           f'metalogiclabs/mathgraph@{PIN}\n'
           'Warranted historical observations do not certify unobserved dynamics.\n"""\n',
           'from __future__ import annotations\n',
           'from dataclasses import asdict, dataclass, is_dataclass\n',
           'from enum import Enum\nimport hashlib\nimport json\n',
           'from typing import Any, Iterable, Mapping, Sequence\n']
    for name, text in texts.items():
        lines = text.splitlines(keepends=True)
        for node in ast.parse(text).body:
            if name == 'crystal.py':
                ids = {getattr(node, 'name', None)}
                if isinstance(node, ast.Assign):
                    ids.update(t.id for t in node.targets if isinstance(t, ast.Name))
                if not NAMES.intersection(ids):
                    continue
            elif isinstance(node, (ast.Import, ast.ImportFrom)) or (
                    isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)):
                continue
            start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
            out.append('\n' + ''.join(lines[start-1:node.end_lineno]))
    return ''.join(out).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = render(args.source)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != result:
            raise SystemExit('GLOBAL_CORE_SLICE=FAIL')
    else:
        OUTPUT.write_text(result)
    print('GLOBAL_CORE_SLICE=PASS', hashlib.sha256(result.encode()).hexdigest())


if __name__ == '__main__':
    main()
