"""Canonical induced-dyad patch admission, supplied states only."""
from collections import Counter
from itertools import combinations


def patches(nodes, edges):
    if type(nodes) is not int or not 0 <= nodes <= 64:
        raise ValueError('nodes outside reference domain')
    edges=list(edges)
    if len(edges)>64:
        raise ValueError('edges outside reference domain')
    arcs=[]
    for edge in edges:
        if not isinstance(edge,(list,tuple)) or len(edge)!=2:
            raise ValueError('invalid arc')
        if any(type(v) is not int or not 0<=v<nodes for v in edge):
            raise ValueError('invalid endpoint')
        arcs.append(tuple(edge))
    counts=Counter(arcs)
    dyads=sorted((a,b) for a,b in counts if a<b and counts[a,b]==counts[b,a]==1)
    result=[]
    for left,right in combinations(dyads,2):
        vertices=set(left+right)
        if len(vertices)!=4:continue
        induced=sum(count for (a,b),count in counts.items() if a in vertices and b in vertices)
        if induced==4:result.append(left+right)
    return result
