import unittest
import data

class DataTestCases(unittest.TestCase):
    def setUp(self):
        self.ds = data.DataStore()
        self.user = data.User(handle='ginuwine', 
                              name='Ginuwine', 
                              location='US', 
                              bio='Come ride my pony')
        self.doc = data.Document(name='Ponies and Horses')
        self.rev = data.Revision(text='We need more Ponies', 
                                 author=self.user, 
                                 document=self.doc)
        self.fork = data.Revision(text='We need more Horses', 
                                  author=self.user, 
                                  document=self.doc,
                                  parent=self.rev)

    def assert_equal(self, a, b):
        for k in a.__dict__.keys() + b.__dict__.keys():
            self.assertTrue(k in a.__dict__, 
                            'Missing key in %s object a: %s' % (a.key.type(), k))
            self.assertTrue(k in b.__dict__, 
                            'Missing key in %s object b: %s' % (b.key.type(), k))
            try:
                av = getattr(a,k)
                bv = getattr(b,k)
                self.assertEqual(av, bv, 
                  'Written and read keys for %s object do not match:\n' % a.key.type() 
                  + '    written.%s: %s\n' % (k, av)
                  + '    read.%s:    %s\n' % (k, bv))
            except KeyError:
                pass
    
    def get_put_test(self, obj):
        '''tests storage and retrieval of objects'''
        self.ds.put(obj)
        obj_ = self.ds.get(obj.key)
        self.assert_equal(obj, obj_)

    def update_test(self, obj, key, new_val):
        '''tests updating of object properties'''
        self.ds.update({'key':obj.key, key: new_val})
        obj_ = self.ds.get(obj.key)
        self.assertEqual(getattr(obj_,key), new_val)

    def reference_test(self, rev):
        '''checks whether rev is incorporated in index sets'''
        if rev.parent:
            self.assertTrue(self.ds.ismember('%s:forks' % rev.parent, rev.key))
        if rev.document:
            self.assertTrue(self.ds.ismember('%s:revisions' % rev.document, rev.key))
            if rev.key == rev.root:
                self.assertTrue(self.ds.ismember('%s:roots' % rev.document, rev.key))
        if rev.key != rev.root:
            self.assertTrue(self.ds.ismember('%s:revisions' % rev.root, rev.key))
        if rev.author:
            self.assertTrue(self.ds.ismember('%s:authored' % rev.author, rev.key))

    def test_user(self):
        self.assertEqual(self.user.key.type(), 'User')
        self.get_put_test(self.user)
        self.assertTrue(self.ds.redis.sismember('users', self.user.key))
        self.update_test(self.user, 'location', 'Washington, DC')

    def test_doc(self):
        self.assertEqual(self.doc.key.type(), 'Document')
        self.get_put_test(self.doc)
        self.assertTrue(self.ds.redis.sismember('documents', self.doc.key))
        self.update_test(self.doc, 'name', 'Of Mice and Men')

    def test_rev(self):
        for r in [self.rev, self.fork]:
            self.assertEqual(r.key.type(), 'Revision')
            self.get_put_test(r)
            self.reference_test(r)
            self.update_test(r, 'text', 'We need more Ponies.')
    
    def test_vote(self):
        self.ds.put(self.user)
        self.ds.put(self.rev)
        self.ds.put(self.fork)
        # test upvoting
        self.assertTrue(self.ds.vote(self.user, self.rev, 1))
        self.assertTrue(self.ds.ismember('%s:up_voted' % self.user, self.rev))
        # test blank voting
        self.assertTrue(self.ds.vote(self.user, self.rev, 0))
        self.assertFalse(self.ds.ismember('%s:up_voted' % self.user, self.rev))
        self.assertFalse(self.ds.ismember('%s:down_voted' % self.user, self.rev))
        # test downvoting
        self.assertTrue(self.ds.vote(self.user, self.rev, -1))
        self.assertTrue(self.ds.ismember('%s:down_voted' % self.user, self.rev))
        # test scoring
        for r in [self.rev, self.fork]:
            for v in [-1, 1]:
                u = data.User(**self.user.__dict__)
                self.ds.put(u)
                self.ds.vote(u, r, v)
        r = self.ds.get(self.rev.key)
        self.assertTrue(r.tot_up == 1, 
                        'r.tot_up = %d (expected: %d)' % (r.tot_up, 1))
        self.assertTrue(r.tot_down == 2,
                        'r.tot_down = %d (expected: %d)' % (r.tot_down, 2))
        self.assertTrue(r.score == 2. / 5.,
                        'r.score = %.2f (expected: %.2f)' % (r.score, 2./5.))
        f = self.ds.get(self.fork.key)
        self.assertTrue(f.tot_up == 2, 
                        'f.tot_up = %d (expected: %d)' % (f.tot_up, 2))
        self.assertTrue(f.tot_down == 3,
                        'f.tot_down = %d (expected: %d)' % (f.tot_down, 3))
        self.assertTrue((f.score - 3. / 7.)**2 < 1e-5,
                        'f.score = %.2f (expected: %.2f)' % (f.score, 3./7.))


if __name__ == '__main__':
    unittest.main()