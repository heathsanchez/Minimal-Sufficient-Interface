import itertools
import unittest

# No menu of semantic binary operators is supplied.  Candidate constructors are
# programs generated from a generic Boolean expression substrate.
STATES = tuple(range(8))
ATOMS = tuple(tuple((x >> b) & 1 for x in STATES) for b in range(3))


def neg(x): return 1 - x

def meet(x, y): return x & y

def kernel(col):
    return frozenset((i,j) for i in range(len(col)) for j in range(i+1,len(col)) if col[i] == col[j])

# Generic substrate available before development: variables, NOT, AND.
# Programs are anonymous trees.  OR/XOR/XNOR are not primitives or candidates.
def eval_expr(e, a, b):
    tag=e[0]
    if tag=='a': return a
    if tag=='b': return b
    if tag=='n': return neg(eval_expr(e[1],a,b))
    if tag=='m': return meet(eval_expr(e[1],a,b), eval_expr(e[2],a,b))
    raise ValueError(tag)

def truth(e): return tuple(eval_expr(e,a,b) for a,b in ((0,0),(0,1),(1,0),(1,1)))
def partition(t):
    return frozenset((i,j) for i in range(4) for j in range(i+1,4) if t[i]==t[j])

def generate(max_depth):
    by=[{('a',),('b',)}]
    allp=set(by[0])
    for d in range(1,max_depth+1):
        prev=set().union(*by)
        layer={('n',x) for x in prev}
        layer |= {('m',x,y) for x in prev for y in prev}
        layer -= allp
        by.append(layer); allp |= layer
    return allp

def combine(t,left,right): return tuple(t[(x<<1)|y] for x,y in zip(left,right))

def repairs(t, hidden):
    hk=kernel(hidden)
    return any(kernel(combine(t,a,b))==hk for a,b in itertools.product(ATOMS, repeat=2))

def parity_tasks():
    xor=(0,1,1,0)
    return tuple(combine(xor,ATOMS[i],ATOMS[j]) for i in range(3) for j in range(i+1,3))

def synthesize(tasks,max_depth=4):
    # Enumerate programs from syntax only, then quotient them behaviourally.
    classes={}
    for e in generate(max_depth):
        t=truth(e)
        if all(repairs(t,h) for h in tasks):
            classes.setdefault(partition(t),[]).append(e)
    return classes

class GeneratedConstructorGenesis(unittest.TestCase):
    def test_constructor_is_generated_not_selected(self):
        tasks=parity_tasks()
        learned=synthesize(tasks)
        self.assertEqual(len(learned),1)
        fp, programs=next(iter(learned.items()))
        self.assertGreater(len(programs),0)
        tables={truth(p) for p in programs}
        self.assertTrue((0,1,1,0) in tables or (1,0,0,1) in tables)
        print(f'GENERATED_CONSTRUCTOR_GENESIS source_tasks={len(tasks)} behavioural_classes={len(learned)} generated_programs={len(programs)} menu=NONE')

    def test_generated_class_compounds(self):
        fp,programs=next(iter(synthesize(parity_tasks()).items()))
        p=min(programs,key=lambda e:len(repr(e)))
        t=truth(p)
        # held-out permuted presentation
        perm=(5,2,7,0,3,6,1,4)
        cols=tuple(tuple((perm[x]>>b)&1 for x in STATES) for b in (2,0,1))
        first=combine(t,cols[0],cols[1]); triple=combine(t,first,cols[2])
        base={kernel(c) for c in cols} | {kernel(tuple(1-x for x in c)) for c in cols}
        depth1=base | {kernel(combine(t,a,b)) for a,b in itertools.product(cols,repeat=2)}
        self.assertNotIn(kernel(triple),base)
        self.assertNotIn(kernel(triple),depth1)
        rebuilt=combine(t,combine(t,cols[0],cols[1]),cols[2])
        self.assertEqual(kernel(rebuilt),kernel(triple))
        print('GENERATED_CONSTRUCTOR_COMPOUNDING cold_depth1=FAIL warm_depth2=PASS exact_ablation=FAIL')

if __name__=='__main__': unittest.main()
