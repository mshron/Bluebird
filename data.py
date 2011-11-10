'''Data model for collaborative manifesto maker'''
# TODO: check existence of referenced objects on put. JWM

from random import randrange
import time
import sys
import json
from redis import Redis

# this is how times are stored (chosen to be sortable)
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def rnd():
    '''Generates a random value for usage in keys'''
    return hex(randrange(0,2**32))[2:]

# def parse(attrs):
#     '''Takes a dictionary representation of a DataModel
#     instance and returns the corresponding object'''
#     obj_type = attrs['type'].split(':')[-1]
#     if not obj_type in DATA_TYPES:
#         raise ValueError('Illegal type for DataModel instance: %s' % obj_type)
#     # parse lists where necessary
#     for key in LIST_ATTRS[obj_type]:
#         if isinstance(attrs[key], basestring):
#             attrs[key] = attrs[key].strip('[]').split(', ')
#     # get object class
#     Obj = globals()[obj_type]
#     # init new object with specified attributes
#     return Obj(**attrs)

def parse(attrs):
    '''Takes a dictionary representation of a DataModel
    instance and returns the corresponding object'''
    attrs = dict(attrs.items())
    obj_type = Key(attrs['key']).type()
    return globals()[obj_type](**attrs)

class DataStore(object):
    '''Interface with redis datastore'''

    def __init__(self, *args, **kwargs):
        self.redis = Redis(*args, **kwargs)

    def members(self, set_key):
        '''Returns a KeyList of references under key'''
        members = self.redis.smembers(set_key)
        return KeyList(key=set_key, members=members)

    def ismember(self, set_key, obj_key):
        '''Check whether key in set'''
        return self.redis.sismember(set_key, obj_key)

    def inter(self, set_keys):
        '''Returns intersection between sets'''
        return self.redis.sinter(set_keys)

    def get_all(self, set_key):
        '''Returns all objects in a set'''
        keys = self.members(set_key)
        return [self.get(k) for k in keys]

    def get_tree(self, rev_key, revisions={}):
        '''Returns a populated revision tree'''
        rev = self.get(rev_key)
        forks = self.members('%s:forks' % rev_key)
        rev.forks = [self.get_tree(k) for k in forks]
        return rev

    def get(self, obj_key):
        '''Retrieves a DataModel object'''
        attrs = self.redis.hgetall(obj_key)
        if Key(obj_key).type == 'User':
            # retrieve set members separately
            for k in ['authored', 'up_voted', 'down_voted']:
                attrs[k] = self.members('%s:%s' % (obj_key, k)) 
        if Key(obj_key).type == 'Revision':
            attrs['forks'] = self.members('%s:%s' % (obj_key, 'forks')) 
        return parse(attrs)

    def put(self, data):
        '''Writes out a DataModel object'''
        # new objects need to be added to their respective sets
        if not self.redis.exists(data.key):
            if isinstance(data, User):
                self.redis.sadd('users', data.key)
            if isinstance(data, Document):
                self.redis.sadd('documents', data.key)
            if isinstance(data, Revision): 
                if data.parent:
                    self.redis.sadd('%s:forks' % data.parent, data.key)
                if data.document:
                    self.redis.sadd('%s:revisions' % data.document, data.key)
                    if data.key == data.root:
                        self.redis.sadd('%s:roots' % data.document, data.key)
                if data.key != data.root:
                    self.redis.sadd('%s:revisions' % data.root, data.key)
                else:
                    self.redis.sadd('%s:revisions' % data.key, data.key)
                if data.author:
                    self.redis.sadd('%s:authored' % data.author, data.key)

        # for users, don't write out reference sets 
        # (these are stored separately)
        attrs = dict(data.__dict__.items())
        if isinstance(data, User):
            for k in ['authored', 'up_voted', 'down_voted']:
                self.redis.delete('%s:%s' % (data.key, k))
                self.redis.sadd('%s:%s' % (data.key, k), attrs.pop(k))
        success = self.redis.hmset(data.key, attrs)
        return data.key if success else success

    def update(self, attrs):
        '''Writes subset of attributes to specified object'''
        key = attrs['key']
        if self.redis.exists(key):
            data = self.get(key)
            for k,v in attrs.items():
                setattr(data, k, v)
            # write out object
            success = self.put(data)
            return data.key if success else success
        else:
            return 0
            
    def vote(self, user_key, rev_key, vote):
        '''Votes up, down or blank on specified revision, and update
        user records'''
        # vote zero means blanking
        if vote == 0:
            if self.ismember('%s:up_voted' % user_key, rev_key):
                self.redis.srem('%s:up_voted' % user_key, rev_key)
                self.redis.hincrby(rev_key, 'up', -1)
                return True
            if self.ismember('%s:down_voted' % user_key, rev_key):
                self.redis.srem('%s:down_voted' % user_key, rev_key)
                self.redis.hincrby(rev_key, 'down', -1)
                return True
        # vote 1 means upvote
        if vote == 1 and not self.ismember('%s:up_voted' % user_key, rev_key):
                self.redis.sadd('%s:up_voted' % user_key, rev_key)
                self.redis.hincrby(rev_key, 'up', 1)
                return True
        # vote -1 means downvote
        if vote == -1 and not self.ismember('%s:down_voted' % user_key, rev_key):
                self.redis.sadd('%s:down_voted' % user_key, rev_key)
                self.redis.hincrby(rev_key, 'up', 1)
                return True
        return False

class Key(str):
    '''BaseClass for datastore keys'''
    def type(self):
        '''Returns object type of key'''
        return self.split(':')[-2]

    def id(self):
        '''Returns id of object'''
        return self.split(':')[-1]

class KeyList(list):
    '''BaseClass for sets of datastore references'''
    # this is just here so you can use isinstance(object.attr, KeyList)
    def __init__(self, key=None, members=()):
        super(KeyList, self).__init__(members)


class DataModel(object):
    '''Base class for DataStore object model. Each DataModel instance
    must have a key property, which indicates its location in the 
    redis backend. Object keys take the format

        key = ObjType:obj_id

    :key: 
        Reference to object in dataset. Can be specified
        either as full key or object id.
    '''
    def __init__(self, key=None):
        key = key if key else ''
        if len(key.split(':')) < 2:
            key = '%s:%s' % (self.__class__.__name__, key if key else rnd())
        self.key = Key(key)

    def __eq__(self, other):
        if hasattr(other, 'key'):
            return (self.key == other.key)
        else:
            return False

    def __repr__(self):
        return self.key

class DataEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DataModel):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)

class Document(DataModel):
    def __init__(self, name='', created=None, key=None):
        super(Document, self).__init__(key=key)
        self.name = name
        self.created = created if created else time.strftime(TIME_FORMAT)

class Revision(DataModel):
    def __init__(self, text=None, author=None, created=None, 
                 topic='', up=0, down=0, score=0, forks=[],
                 parent=None, root=None, document=None, key=None):
        super(Revision, self).__init__(key=key)
        self.text = text
        self.author = Key(author) if author else ''
        self.root = Key(root) if root else self.key
        self.parent = Key(parent) if parent else ''
        self.document = Key(document) if document else ''
        self.forks = forks
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.topic = topic
        self.up = int(up)
        self.down = int(down)
        self.score = float(score)

# class Thread(DataModel):
#     def __init__(self, root=None, revisions=[], **kwargs):
#         super(Revision, self).__init__(**kwargs)
    
#     def tree(self, root=None):
#         '''recursively populate references in revision tree'''
#         children = []
#         for child in root.children:
#             children.append(self.tree(root=child))
        
#         return 

#     def scores(self):
#         '''get score for each revision'''


class User(DataModel):
    def __init__(self, handle=None, name=None, 
                 created=None, location=None, bio=None, 
                 authored=[], up_voted=[], down_voted=[], key=None):
        super(User, self).__init__(key=key)
        self.handle = handle
        self.name = name
        self.location = location
        self.bio = bio
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.authored = KeyList([Key(rev) for rev in authored])
        self.up_voted = KeyList([Key(rev) for rev in up_voted])
        self.down_voted = KeyList([Key(rev) for rev in down_voted])
