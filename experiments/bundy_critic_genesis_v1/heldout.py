"""Independent of the generator's training API. Internally authored, frozen tests."""

def goals(Goal):
    positives=[]
    for n in (4,5,6,7):
        names=tuple(f"t{n}_{i}" for i in range(n+1))
        hyps=tuple((names[i],names[i+1]) for i in range(n))
        positives.append(Goal(f"future_chain_{n}",hyps,names[0],names[-1]))
    positives += [
        Goal("future_reverse",(("q","p"),("r","q"),("s","r"),("t","s")),"p","t"),
        Goal("future_permuted",(("v","w"),("x","y"),("u","v"),("w","x")),"u","y"),
        Goal("future_extra_context",(("k","l"),("x","y"),("m","n"),("l","m"),("n","o")),"k","o"),
        Goal("future_one_edge",(("aa","bb"),),"aa","bb"),
    ]
    negatives=[
        Goal("future_disconnected",(("aa","bb"),("cc","dd")),"aa","dd"),
        Goal("future_similar_but_missing",(("ra","rb"),("rc","rd"),("rd","re")),"ra","re"),
        Goal("future_reversed_unrelated",(("jj","ii"),("ll","kk")),"ii","ll"),
    ]
    return tuple(positives+negatives)