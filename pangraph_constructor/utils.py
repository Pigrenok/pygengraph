# AUTOGENERATED! DO NOT EDIT! File to edit: 04_utils.ipynb (unless otherwise specified).

__all__ = ['sortAccessions', 'pathFileToPathDict', 'pathConvert', 'checkZoomLevels', 'adjustZoomLevels', 'NpEncoder',
           'bidict', 'resetDB', 'iset_add', 'iset_get', 'iset_score', 'iset_not_score', 'iset_del']

# Cell
from collections.abc import Iterable
# from copy import deepcopy
import json
import numpy as np
import os
import random
import joblib

from redis import Redis

# Cell
def sortAccessions(sort,_paths):
    paths = {}
    if isinstance(sort,bool):
        for accession in sorted(list(_paths.keys())):
            paths[accession] = _paths[accession]
    elif isinstance(sort,str):
        pathNamesList = list(_paths.keys())
        try:
            paths[sort] = _paths[sort]
            pathNamesList.remove(sort)
        except KeyError:
            Warning(f'Path name {sort} was not found in path file. All paths are sorted in lexicographic order')
        for accession in sorted(pathNamesList):
            paths[accession] = _paths[accession]
    elif isinstance(sort,Iterable):
        pathNamesList = list(_paths.keys())
        for pathInd in sort:
            accession = pathNamesList[pathInd]
            paths[accession] = _path[accession]
    return paths

# Cell
def pathFileToPathDict(filePath,directional=True,sort=True,v2=True):
    '''
    Reads path file (ASCII file) and translates it to path dictionary for `GenGraph` class constructor.

    Path file has a path on each line in the following format:
    <path name>: <nodeID[+|-]>[,<nodeID[+,-]>]

    Parameters
    ==========

    `filePath`: str. Absolute path to the path file.
    `directional`: boolean (default: True). Whether the path file contains
                   directionality (whether nodeID has `+` or `-` at the end).
                   If False (the file does not contain directionality marks),
                   then all nodes in all paths are treated as positive (not inverted).
    `sort`: boolean, str or iterable (e.g. list). If Boolean, true means that the paths should be sorted
            in lexicographic order (by names) and appear in the path dict in sorted order. If False,
            then no sorting is done and paths will appear as they are in the file. If iterable with
            indexes of the paths (from 0 to n-1 for n paths), then this particular order will be used
            in the paths dictionary. If str, then it should provide a single path name that should appear
            first with the rest being sorted in lexicographic order.

    Return
    ======

    `paths`: a dictionary with path names as keys and lists of nodeID (str) with directionality markers (`+` or `-`)
             at the end as values.

    '''
    _paths = {}
    with open(filePath) as f:
        for line in f:
            pathNameChr,pathNodeList = line.strip(' \n\t').split(':')
            if v2:
                pathName,seqID = [name.strip() for name in pathNameChr.split('-')]
            else:
                pathName = pathNameChr.strip()
                seqID = None
            if directional:
                chainList = [nodedir.strip() for nodedir in pathNodeList.strip().split(',')]
            else:
                chainList = [f'{node.strip()}+' for node in pathNodeList.strip().split(',')]

            if v2:
                _paths.setdefault(seqID,{})[pathName] = chainList
            else:
                _paths[pathName] = chainList

    if isinstance(sort,bool):
        if sort:
            if v2:
                paths = {}
                for seqID in _paths.keys():
                    paths[seqID] = sortAccessions(sort,_paths[seqID])
            else:
                paths = sortAccessions(sort,_paths)
            del _paths
        else:
            paths = _paths
    elif isinstance(sort,str):
        if v2:
            paths = {}
            for seqID in _paths.keys():
                paths[seqID] = sortAccessions(sort,_paths[seqID])
        else:
            paths = sortAccessions(sort,_paths)
        del _paths
    elif isinstance(sort,Iterable):
        if v2:
            paths = {}
            for seqID in _paths.keys():
                paths[seqID] = sortAccessions(sort,_paths[seqID])
        else:
            paths = sortAccessions(sort,_paths)
        del _paths
    else:
        paths = _paths

    return paths

# Cell
def pathConvert(inputPath, suffix=''):
    outputPath = os.path.dirname(inputPath)
    outputName = '.'.join(os.path.splitext(os.path.basename(inputPath))[:-1])+suffix
    return outputPath,outputName

# Cell
def checkZoomLevels(zoomLevels):
    '''
    Check that each previous zoom level is factor of next one
    '''
    _zoomLevels = np.array(zoomLevels)
    div = _zoomLevels[1:]/_zoomLevels[:-1]
    return not np.any(div - div.astype(np.int))

# Cell
def adjustZoomLevels(zoomLevels):
    '''
    If there is no zoom level 1, adds it to the list.
    '''
    if not checkZoomLevels(zoomLevels):
        raise ValueError('Zoom level list is incorrect. Each next level \
                          should have previous one as factor.')
    if min(zoomLevels) > 1:
        zoomLevels = [1] + zoomLevels
    return zoomLevels

# Cell
# https://stackoverflow.com/questions/50916422/python-typeerror-object-of-type-int64-is-not-json-serializable
# Class for encoding np types to JSON
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return super(NpEncoder, self).default(obj)


# Cell
class bidict(dict):
    '''
    Here is a class for a bidirectional dict, inspired by Finding key from
    value in Python dictionary and modified to allow the following 2) and 3).

    Note that :

    1) The inverse directory bd.inverse auto-updates itself when the standard
        dict bd is modified.
    2) The inverse directory bd.inverse[value] is always a list of keys such
        that value in bd[key] for each key.
    3) Unlike the bidict module from https://pypi.python.org/pypi/bidict,
        here we can have 2 keys having same value, this is very important.
    4) After modification, values in the "forward" (not inversed) dict
        can be lists (or any iterables theoretically,
        but only list was tested).

    For implementing 4), new method `add` was introduced.
    If d[key].append(value) attempted, the link between main and inversed dict
    will be broken. Method `add` can accept both

    Credit:
    Implemented as an answer to
    https://stackoverflow.com/questions/3318625/how-to-implement-an-efficient-bidirectional-hash-table
    by Basj (https://stackoverflow.com/users/1422096/basj).
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            if isinstance(value, Iterable):
                for v in value:
                    self.inverse.setdefault(v, []).append(key)
            else:
                self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            keyV = self[key]
            if isinstance(keyV, Iterable):
                for v in keyV:
                    self.inverse[v].remove(key)
            else:
                self.inverse[keyV].remove(key)
        super(bidict, self).__setitem__(key, value)
        if isinstance(value, Iterable):
            for v in value:
                self.inverse.setdefault(v, []).append(key)
        else:
            self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        value = self[key]
        if isinstance(value, Iterable):
            for v in value:
                self.inverse.setdefault(v, []).remove(key)
                if v in self.inverse and not self.inverse[v]:
                    del self.inverse[v]
        else:
            self.inverse.setdefault(value, []).remove(key)
            if value in self.inverse and not self.inverse[value]:
                del self.inverse[value]
        super(bidict, self).__delitem__(key)

    def add(self, key, value):
        valKey = self.setdefault(key, [])
        if isinstance(valKey,Iterable):
            valKey = set(valKey)
        else:
            valKey = set([valKey])

        if isinstance(value, Iterable):
            valKey = valKey.union(value)
        else:
            valKey.add(value)

        self[key] = list(valKey)

    def remove(self,key,value):
        valKey = set(self.setdefault(key,[]))

        if isinstance(value,Iterable):
            valKey.difference_update(value)
        else:
            valKey.remove(value)

        self[key] = list(valKey)

# Cell
def resetDB(pathToDictFile,redisServer='redis',port=6379):
    os.remove(pathToDictFile)
    conn = Redis(host=redisServer,port=port,db=0)
    conn.flushall()
    return 0

# Cell
def iset_add(r,name,intervalMapping):
    '''
        Add members with intervals to interval set. If interval set does not exist, it will be created.
        In reality, it will create two Redis Sorted Sets for starts and ends of the intervals.
        The rest of the functions ``iset_`` will know what to do with them.

        ``r``: Redis object. Redis client.
        ``name``: string. Name of the interval set.
        ``intervalMapping``: dict. Dictionary with names of intervals as keys and
                tuples with start and end of intervals.


        Return number of added intervals. In reality, it adds equal number of elements
        to two sorted sets, if number of added elements are not equal, DataError is raised.

    '''
    starts = {f'{n}_{seqnum}':int(interval[0]) for n,inv in intervalMapping.items() for seqnum,interval in enumerate(inv)}
    ends = {f'{n}_{seqnum}':int(interval[1]) for n,inv in intervalMapping.items() for seqnum,interval in enumerate(inv)}
    numAddedStarts = r.zadd(f'{name}Start',mapping=starts)
    numAddedEnds = r.zadd(f'{name}End',mapping=ends)
    if numAddedStarts!=numAddedEnds:
        raise DataError(f'Not equal number of starts and ends were added to DB. For consistency, the sorted sets {name}Start and {name}End should be checked and/or recreated')
    return numAddedStarts

# Cell
def iset_get(r,name,member=None):
    '''
        Return either the whole interval set or specific name(s) with its interval.

        ``r``: Redis object. Redis client.
        ``name``: string. Name of the interval set.
        ``member``: string, list, tuple or None. If None, function return all members with their respective intervals.
            If string, returns a single member with its interval,
            if list or tuple, returns all requested members with their respecitve intervals.

        Return a dictionary with member names as keys and tuples with interval starts and ends as values.
        For member names not found in interval set, the value for the given key will be a tuple (None,None).
    '''
    if member is None:
        starts = {k.decode():v for k,v in r.zrange(f'{name}Start',0,-1,withscores=True)}
        ends = {k.decode():v for k,v in r.zrange(f'{name}End',0,-1,withscores=True)}
        return {k:(starts[k],ends[k])for k in starts.keys()}
    elif isinstance(member,str):
        intStart = r.zscore(f'{name}Start',member)
        intEnd = r.zscore(f'{name}End',member)
        return {member: (intStart, intEnd)}
    else:
        res = {}
        for mm in member:
            intStart = r.zscore(f'{name}Start',mm)
            intEnd = r.zscore(f'{name}End',mm)
            res[mm] = (intStart, intEnd)
        return res

# Cell
def iset_score(r,name,start,end=None):
    '''
        Returns all member names whose interval contains a given value or intersects with the given interval

        ``r``: Redis object. Redis client.
        ``name``: string. Name of the interval set
        ``start``: int. Query value or the start of query interval.
        ``end``: int or None. If None, ``start`` is treated as a single query value.
                If int, then ``start`` is the start of the query interval,
                ``end`` is the end of the query interval.

        Returns a list of members whose intervals either contain query value or intersects with query interval.
    '''
    if end:
        _endPos = end
    else:
        _endPos = start
    if _endPos<start:
        raise ValueError('``start`` should be less or equal to ``end``.')
    tid = random.randint(1e8,1e9-1)
#     r.execute_command('ZRANGESTORE',*['startSetTemp','geneStart','-inf',_endPos,'BYSCORE'])
#     r.execute_command('ZRANGESTORE',*['endSetTemp','geneEnd',start,'inf','BYSCORE'])
    r.zrangestore(f'startSetTemp_{tid}',f'{name}Start','-inf',_endPos,byScore=True)
    r.zrangestore(f'endSetTemp_{tid}',f'{name}End',start,'inf',byScore=True)
    res = ['_'.join(el.decode().split('_')[:-1]) for el in r.zinter([f'startSetTemp_{tid}',f'endSetTemp_{tid}'])]
    r.delete(f'startSetTemp_{tid}',f'endSetTemp_{tid}')
    return res

# Cell
def iset_not_score(r,name,start,end=None):
    '''
        Returns all intervals (member names only) where query value is not contained or query interval is not intersecting.
        Inverison of ``iset_score()`` function

        ``r``: Redis object. Redis client.
        ``name``: string. Name of the interval set
        ``start``: int. Query value or the start of query interval.
        ``end``: int or None. If None, ``start`` is treated as a single query value.
                If int, then ``start`` is the start of the query interval,
                ``end`` is the end of the query interval.

        Returns a list of members whose intervals either does not contain query value or does not intersect with query interval.

    '''
    if end:
        _endPos = end
    else:
        _endPos = start
    if _endPos<start:
        raise ValueError('``start`` should be less or equal to ``end``.')
    tid = random.randint(1e8,1e9-1)

    r.zrangestore(f'startSetTemp_{tid}',f'{name}Start','-inf',_endPos,byScore=True)
    r.zrangestore(f'endSetTemp_{tid}',f'{name}End',start,'inf',byScore=True)
    r.zinterstore(f'foundSetTemp_{tid}',[f'startSetTemp_{tid}',f'endSetTemp_{tid}'])
    r.zrangestore(f'allSetTemp_{tid}',f'{name}Start','-inf','inf',byScore=True)
    res = [el.decode() for el in (r.zdiff([f'allSetTemp_{tid}',f'foundSetTemp_{tid}']))]
    r.delete(f'startSetTemp_{tid}',f'endSetTemp_{tid}',f'allSetTemp_{tid}',f'foundSetTemp_{tid}')

    return res

# Cell
def iset_del(r,name,member=None):
    '''
        Return either the whole interval set or specific name(s) with its interval.

        ``r``: Redis object. Redis client.
        ``name``: string. Name of the interval set.
        ``member``: string, list, tuple or None. If None, function return all members with their respective intervals.
            If string, returns a single member with its interval,
            if list or tuple, returns all requested members with their respecitve intervals.

        Return number of removed intervals. In reality, it removes equal number of elements
        from two sorted sets, if number of added elements are not equal, DataError is raised.
    '''
    if member is None:
        keyRemovedStart = r.delete(f'{name}Start')
        keyRemovedEnd = r.delete(f'{name}End')
        if keyRemovedStart==1 and keyRemovedEnd==1:
            return 1
        else:
            raise DataError('Less than two sorted sets were deleted. Something is wrong with the Redis DB.')
    elif isinstance(member,str):
        removedStartCount = r.zrem(f'{name}Start',member)
        removedEndCount = r.zrem(f'{name}End',member)
    else:
        removedStartCount = r.zrem(f'{name}Start',*member)
        removedEndCount = r.zrem(f'{name}End',*member)

    if removedStartCount==removedEndCount:
        return removedStartCount
    else:
        raise DataError(f'Not equal number of starts and ends were deleted from DB. \
        For consistency, the sorted sets {name}Start and {name}End should be checked and/or recreated')