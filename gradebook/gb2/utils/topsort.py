"""
Topological sort.

Used for determining execution order of calculations.

http://en.wikipedia.org/wiki/Topological_sorting

FYI, see the alternative algorithm based on depth-first search 
(reproduced here).

NB: DAG: Directed Acyclic Graph.

-------------------------------------------------------------

L <- Empty list that will contain the sorted nodes
while there are unmarked nodes do
    select an unmarked node n
    visit(n) 
function visit(node n)
    if n has a temporary mark then stop (not a DAG)
    if n is not marked (i.e. has not been visited yet) then
        mark n temporarily
        for each node m with an edge from n to m do
            visit(m)
        mark n permanently
        unmark n temporarily
        add n to head of L

-------------------------------------------------------------

Note that the M2M dependencies field indicates the *incoming* direction
in the dependency DAG.
"""
from __future__ import print_function, unicode_literals

###############################################################


def collect_nodes(n):
    """
    Collect all nodes connecting to obj in both the forward and 
    backward directions.
    The resulting DAG may not be complete for topsort().
    """
    G = set()  # the set of node objects

    def _collect(n, reverse):
        G.add(n)
        if reverse:
            for m in n.dependencies.active():
                _collect(m, reverse)
        else:
            for m in n.reverse_dependencies.active():
                _collect(m, reverse)

    # _collect(n, reverse=True)
    _collect(n, reverse=False)
    return G


###############################################################


def topsort(obj, graph=None):
    """
    ``obj`` must have a ``dependencies`` m2m field with args:
        ``symmetrical=False, related_name='reverse_dependencies'``.
        
    The resulting list L contains all the related objects of ``obj``
    in the order that their associated rules should be executed.
    
    The idea here is that, if you have an Score or Task which is going
    to be updated, then everything the depends on this will also
    need to be updated.  This function returns the list of objects
    requiring updates *in order*.
    """
    L = []
    perm_mark = set()
    temp_mark = set()
    DAG = graph or collect_nodes(obj)

    def visit(n):
        if n in temp_mark:
            raise ValueError("Not a directed acyclic graph")
        if n not in perm_mark:
            temp_mark.add(n)
            for m in n.reverse_dependencies.active():
                visit(m)
            perm_mark.add(n)
            temp_mark.remove(n)
            L.append(n)

    while len(perm_mark) < len(DAG):
        for n in DAG:
            if n not in perm_mark:
                visit(n)

    assert len(DAG) == len(L), "Should be complete but we're not"

    L.reverse()
    return L


###############################################################
