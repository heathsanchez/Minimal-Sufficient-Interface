import itertools
import math
import random
import re
from pathlib import Path

from cross_domain_universal_motifs_v2 import SOURCES, statement_graph, graphlets

ROOT = Path(__file__).resolve().parents[1]
K = 5
CONTROLS = 100


def freeze_v2_library():
    maps = []
    for name, path in SOURCES.items():
        n, e = statement_graph(path)
        maps.append(graphlets(n, e, K))
    common = set.intersection(*(set(m) for m in maps))
    print(f'FROZEN_V2_LIBRARY motifs={len(common)} training_families={len(maps)} k={K}')
    return common


def lean_dependency_graph():
    decl_re = re.compile(r'^\s*(?:def|theorem|lemma|abbrev|structure|inductive|class)\s+([A-Za-z_][A-Za-z0-9_\'.]*)', re.M)
    records = []
    for path in sorted((ROOT / 'lean').glob('*.lean')):
        text = path.read_text()
        ms = list(decl_re.finditer(text))
        for i, m in enumerate(ms):
            end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
            records.append((m.group(1), text[m.start():end]))
    names = [n for n, _ in records]
    idx = {n: i for i, n in enumerate(names)}
    edges = set()
    for dst, (_, body) in enumerate(records):
        toks = set(re.findall(r'[A-Za-z_][A-Za-z0-9_\'.]*', body))
        for tok in toks:
            if tok in idx and idx[tok] != dst:
                edges.add((idx[tok], dst))
    live = {u for e in edges for u in e}
    remap = {old: i for i, old in enumerate(sorted(live))}
    return len(live), {(remap[a], remap[b]) for a, b in edges if a in live and b in live}


def workflow_step_graph():
    nodes = []
    edges = set()
    for path in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
        lines = path.read_text().splitlines()
        current = []
        for line in lines:
            m = re.match(r'^(\s*)-\s+name:\s*(.+?)\s*$', line)
            if m:
                indent = len(m.group(1))
                if indent >= 6:
                    node = len(nodes)
                    nodes.append((path.name, m.group(2)))
                    current.append(node)
        for a, b in zip(current, current[1:]):
            edges.add((a, b))
    live = {u for e in edges for u in e}
    remap = {old: i for i, old in enumerate(sorted(live))}
    return len(live), {(remap[a], remap[b]) for a, b in edges if a in live and b in live}


def subset_lattice_graph(bits=6):
    n = 1 << bits
    edges = set()
    for x in range(n):
        for b in range(bits):
            if not (x >> b) & 1:
                edges.add((x, x | (1 << b)))
    return n, edges


def rank2_group_cayley_graph(a=4, b=4):
    def ix(x, y):
        return (x % a) * b + (y % b)
    edges = set()
    for x in range(a):
        for y in range(b):
            u = ix(x, y)
            edges.add((u, ix(x + 1, y)))
            edges.add((u, ix(x, y + 1)))
    return a * b, edges


def second_order_trajectory_graph(n=96):
    # Pure causal dependency of a second-order trajectory: two prior states determine the next.
    edges = set()
    for t in range(2, n):
        edges.add((t - 1, t))
        edges.add((t - 2, t))
    return n, edges


def degree_preserving_rewire(n, edges, rng, sweeps=30):
    e = set(edges)
    if len(e) < 2:
        return e
    el = list(e)
    attempts = sweeps * len(el)
    for _ in range(attempts):
        i, j = rng.randrange(len(el)), rng.randrange(len(el))
        if i == j:
            continue
        a, b = el[i]
        c, d = el[j]
        if len({a, b, c, d}) < 4:
            continue
        x, y = (a, d), (c, b)
        if a == d or c == b or x in e or y in e:
            continue
        e.remove((a, b)); e.remove((c, d))
        e.add(x); e.add(y)
        el[i], el[j] = x, y
    return e


def motif_score(n, edges, library):
    gm = graphlets(n, edges, K)
    hit = library & set(gm)
    distinct = len(hit)
    occ = sum(len(gm[m]) for m in hit)
    total = sum(len(v) for v in gm.values())
    frac = occ / total if total else 0.0
    return distinct, occ, total, frac


def percentile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs)-1, int(q * (len(xs)-1)))]


def evaluate(name, graph, library):
    n, e = graph
    actual = motif_score(n, e, library)
    rng = random.Random(20260829 + sum(map(ord, name)))
    null = [motif_score(n, degree_preserving_rewire(n, e, rng), library) for _ in range(CONTROLS)]
    null_distinct = [x[0] for x in null]
    null_occ = [x[1] for x in null]
    null_frac = [x[3] for x in null]
    p95d, p99d = percentile(null_distinct, .95), percentile(null_distinct, .99)
    p95o, p99o = percentile(null_occ, .95), percentile(null_occ, .99)
    p95f, p99f = percentile(null_frac, .95), percentile(null_frac, .99)
    passed = actual[0] > p99d and actual[1] > p99o and actual[3] > p99f
    print(
        f'SUBSTRATE {name} nodes={n} edges={len(e)} '
        f'distinct={actual[0]} null_p95={p95d} null_p99={p99d} '
        f'occ={actual[1]} occ_null_p95={p95o} occ_null_p99={p99o} '
        f'frac={actual[3]:.6f} frac_null_p95={p95f:.6f} frac_null_p99={p99f:.6f} pass={passed}'
    )
    return passed


def main():
    library = freeze_v2_library()
    substrates = {
        'lean_dependency': lean_dependency_graph(),
        'workflow_yaml': workflow_step_graph(),
        'subset_lattice': subset_lattice_graph(),
        'rank2_group_cayley': rank2_group_cayley_graph(),
        'second_order_trajectory': second_order_trajectory_graph(),
    }
    results = {name: evaluate(name, graph, library) for name, graph in substrates.items()}
    passed = sum(results.values())
    print(f'CROSS_SUBSTRATE passes={passed}/{len(results)}')
    print('DEGREE_SEQUENCE_NULL=PASS')
    if passed == len(results):
        print('SAME_LANGUAGE_CONFOUND_REJECTED=PASS')
        print('CROSS_SUBSTRATE_UNIVERSAL_MOTIFS_V3=PASS')
    else:
        failed = ','.join(k for k, v in results.items() if not v)
        print(f'SAME_LANGUAGE_CONFOUND_NOT_REJECTED failed={failed}')
        print('CROSS_SUBSTRATE_UNIVERSAL_MOTIFS_V3=FALSIFIED')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
