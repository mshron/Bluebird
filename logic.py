'''Provides the business logic'''
from operator import itemgetter

def flattenTree(rev, c=[]):
    for child in rev.children:
        c = c + flattenTree(child, c)
    return c + [rev]

def scoreRev(rev):
    '''Individual score for a single revision'''
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
    '''Takes a list of revisions (from one thread) and gives the whole list a score'''
    up = sum(map(lambda x: x.votesFor, revlist))
    down = sum(map(lambda x: x.votesAgainst, revlist))
    return up-down

def rankThreads(threadlist):
    '''Takes a list of list of revisions and ranks the outer list by scoreThread'''
    l = zip(map(scoreThread, threadlist), threadlist)
    l = sorted(l)[::-1]
    return map(itemgetter(1),l)


