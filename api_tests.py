import unittest
import json
import api
import data


class ApiTestCases(unittest.TestCase):
    def setUp(self):
        api.app.debug = True
        self.app = api.app.test_client()
        # generate some sample objects
        self.user = data.User(screen_name='ginuwine', 
                              real_name='Ginuwine', 
                              location='US', 
                              bio='Come ride my pony')
        self.doc = data.Document(name='Ponies and Horses')
        self.rev = data.Revision(text='We need more Ponies', 
                                 author=self.user, 
                                 document=self.doc)
        self.fork = data.Revision(text='We need more Horses', 
                                  author=self.user, 
                                  document=self.doc,
                                  parent=self.rev,
                                  root=self.rev)

    def assert_resp(self, resp, code):
        self.assertEqual(resp.status_code, code,
                         'Request returned status: %s (expected: %s)' 
                         % (resp.status, code))

    def post(self, col, obj):
        url = '/api/%s' % col
        print 'POST to: %s' % url
        resp = self.app.post(path=url,
                             data=json.dumps(obj.__dict__), 
                             content_type='application/json')
        self.assert_resp(resp, 200)
        self.assertEqual(obj.key.id(), resp.data,
                         'Key returned by server not equal to key requested in url:\n'
                         + '  request: %s\n' % obj.key.id()
                         + '  returned: %s' % resp.data)
        return resp

    def vote(self, rev, user, vote):
        dat = {'user':str(user), 'vote':vote}
        url = '/api/documents/%s/revisions/%s/vote' \
               % (data.Key(rev.document).id(), self.rev.key.id())
        print 'PUT to: %s' % url
        resp = self.app.put(path=url, data=json.dumps(dat), content_type='application/json')
        return resp
            
    def get_all(self, col):
        url = '/api/%s' % col
        print 'GET from: %s' % url
        resp = self.app.get(path=url)
        self.assertEqual(resp.status_code, 200,
                         'GET request on URL=%s returned status: %s' 
                         % (url, resp.status))
        attrs_list = json.loads(resp.data)
        obj_list = [data.parse(a) for a in attrs_list]
        return obj_list
    
    def test_api(self):
        # test posting
        self.post('users', self.user)
        self.post('documents', self.doc)
        self.post('documents/%s/revisions' % self.doc.key.id(), self.rev)
        self.post('documents/%s/revisions' % self.doc.key.id(), self.fork)
        # check whether objects are in collections
        self.assertTrue(self.user in self.get_all('users'),
                        '%s not in %s'  % (self.user, self.get_all('users')))
        self.assertTrue(self.doc in self.get_all('documents'))
        self.assertTrue(self.rev in self.get_all('documents/%s/revisions' % self.doc.key.id()))
        self.assertTrue(self.fork in self.get_all('documents/%s/revisions' % self.doc.key.id()))
        # vote up 
        resp = self.vote(self.rev, self.user, 1)
        self.assert_resp(resp, 200)
        self.assertTrue(self.rev.key in api.ds.members('%s:up_voted' % self.user.key))
        # blank vote
        resp = self.vote(self.rev, self.user, 0)
        self.assert_resp(resp, 200)
        self.assertFalse(self.rev.key in api.ds.members('%s:up_voted' % self.user.key))
        # vote down
        resp = self.vote(self.rev, self.user, -1)
        self.assert_resp(resp, 200)
        self.assertTrue(self.rev.key in api.ds.members('%s:down_voted' % self.user.key))
        # this should fail (not allowed to vote twice)
        resp = self.vote(self.rev, self.user, -1)
        self.assert_resp(resp, 403)
        # this should fail (already voted in thread)
        resp = self.vote(self.fork, self.user, -1)
        self.assert_resp(resp, 403)
        # after blanking vote this should work
        resp = self.vote(self.rev, self.user, 0)
        self.assert_resp(resp, 200)
        resp = self.vote(self.fork, self.user, -1)
        self.assert_resp(resp, 200)

if __name__ == '__main__':
    unittest.main()
