'''Provides the business logic'''
from operator import itemgetter

def flattenTree(rev, c=[]):
    for child in rev.children:
        c = c + flattenTree(child, c)
    return c + [rev]

def scoreRev(rev):
    up = rev.votesFor
    down = rev.votesAgainst
    return (up + 1.) / (up + down + 2.)

def rankRevisions(rev):
    '''Takes in revision, hands back ordered list of that revision plus all its children'''
    l = flattenTree(rev)
    l = zip(map(scoreRev,l),l)
    l = sorted(l)[::-1]
    return map(itemgetter(1),l)

def scoreThread(revlist):
    up = sum(map(lambda x: x.votesFor, revlist))
    down = sum(map(lambda x: x.votesAgainst, revlist))
    return up-down

def rankThreads(rootlist):
    l = zip(map(scoreThread, rootlist), rootlist)
    l = sorted(l)[::-1]
    return map(itemgetter(1),l)


