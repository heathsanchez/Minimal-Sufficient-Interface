import itertools, sys
from pysat.solvers import Solver

K5_ROWS = ((0,2,1,4,3),(3,1,4,0,2),(4,3,2,1,0),(2,4,0,3,1),(1,0,3,2,4))
BAD_SHIFT = (1,3,0,4,2)
orbit = [0,1,3,4,2]
n = 20
block = tuple(range(5))

def cell(r,i,v): return 1 + (r*n+i)*n+v
def ex1(cl,lits):
    cl.append(list(lits))
    for a,b in itertools.combinations(lits,2): cl.append([-a,-b])

clauses=[]
for r in range(n):
    for i in range(n): ex1(clauses,[cell(r,i,v) for v in range(n)])
    for v in range(n): ex1(clauses,[cell(r,i,v) for i in range(n)])
def fix(r,i,v): clauses.append([cell(r,i,v)])

# K5 shadow
for lr,row in enumerate(block):
    for li,inp in enumerate(block):
        if li==lr: continue
        fix(row,inp,block[K5_ROWS[lr][li]])

# equivariant shift (4 layers)
shift=list(BAD_SHIFT)
for base in (5,10,15):
    shift.extend(base+((i+1)%5) for i in range(5))
for r in range(n):
    for i in range(n):
        for v in range(n):
            s=cell(r,i,v); im=cell(shift[r],shift[i],shift[v])
            clauses.append([-s,im]); clauses.append([-im,s])

# H companion (orbit positions)
h_index=[ [ci for ci,cv in enumerate(orbit) if K5_ROWS[orbit[(i+1)%5]][cv]==orbit[i]][0] for i in range(5) ]

# four-layer SHORT bands
for i,x in enumerate(orbit):
    succ=orbit[(i+1)%5]
    sq=5+i; sg=10+i; kap=15+i
    fix(x,x,sq)         # x*x = s(x)
    fix(sq,x,sg)        # s*x = sigma
    fix(x,sg,kap)       # x*sigma = kappa
    fix(x,kap,x)        # x*kappa = x
    fix(sg,x,succ)      # sigma*x = D(x) = successor
    fix(kap,sq,sg)      # kappa*s = sigma

# Good idempotent + terminal-K5
bad=set(block); good=set(range(n))-bad
for g in good: fix(g,g,g)
for p in bad:
    for r in range(n): clauses.append([-cell(r,p,p)])
for p in good:
    clauses.append([cell(r,p,p) for r in range(n)])
for p in bad:
    for sq in range(n):
        for sg in range(n):
            for g in good:
                clauses.append([-cell(p,p,sq),-cell(sq,p,sg),-cell(sg,p,g)])

# E677 gating
next_var=n**3+1
sel_of={}
for x in range(n):
    for y in range(n):
        sel=next_var; next_var+=1; sel_of[(x,y)]=sel
        g=[-sel]
        mid=list(range(next_var,next_var+n)); next_var+=n
        out=list(range(next_var,next_var+n)); next_var+=n
        ex1(clauses,mid); ex1(clauses,out)
        for f in range(n):
            for s2 in range(n): clauses.append([*g,-cell(y,x,f),-cell(f,y,s2),mid[s2]])
        for s2 in range(n):
            for t in range(n): clauses.append([*g,-mid[s2],-cell(x,s2,t),out[t]])
        for t in range(n): clauses.append([*g,-out[t],cell(y,t,x)])

# z-colour per cell: z_i = sigma(x)*D(x) = cell(sigma=10+i, successor). 
# ZIPPER: = H(x) Bad.  G-CROSS: Good (in 5..19).
z_cell = {}
def z_good_clause(i):
    sigma=10+i; succ=orbit[(i+1)%5]
    return [cell(sigma,succ,g) for g in range(5,20)]   # OR over Good values
def z_bad_clause(i):
    sigma=10+i; succ=orbit[(i+1)%5]; hval=orbit[h_index[i]]
    return [cell(sigma,succ,hval)]                     # = H(x)

# assumptions: all E677 selectors
all_sel = [sel_of[(x,y)] for x in range(n) for y in range(n)]

def run(config_bad_cells, extra_lits=()):
    # config_bad_cells: list of cell indices forced ZIPPER (z Bad); others forced G-CROSS (z Good)
    ass = list(all_sel)
    extra = list(extra_lits)
    for i in range(5):
        if i in config_bad_cells:
            extra.append(z_bad_clause(i))
        else:
            extra.append(z_good_clause(i))
    with Solver(name="glucose42", bootstrap_with=clauses+extra, use_timer=True) as s:
        r = s.solve(assumptions=ass)
        return r

# k=0: all ZIPPER (z Bad at all 5) -> expect UNSAT (descent)
print("k=0 all-ZIPPER (5 z-Bad):", "UNSAT" if run([0,1,2,3,4]) is False else "SAT/UNKNOWN")
# k=1: one G-CROSS cell (cell 0 z Good), rest ZIPPER
print("k=1 G-CROSS cell0 (z-Good), rest ZIPPER:", "UNSAT" if run([1,2,3,4]) is False else "SAT/UNKNOWN")
# k=2: two G-CROSS cells
print("k=2 G-CROSS cells {0,1}:", "UNSAT" if run([2,3,4]) is False else "SAT/UNKNOWN")
print("k=2 G-CROSS cells {0,3}:", "UNSAT" if run([1,2,4]) is False else "SAT/UNKNOWN")
