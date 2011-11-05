//
// Backbone Models
//

//------------------------------------------------------------------------

var Document = Backbone.Model.extend({
});

var DocumentCollection = Backbone.Collection.extend({
    model: Document,
    url: '/api/documents'
});

//------------------------------------------------------------------------

var Thread = Backbone.Model.extend({
    initialize: function () {
        this.revisions = [];
    },
    addRevision: function (rev) {
        this.revisions.push(rev);
    }
});

var ThreadCollection = Backbone.Collection.extend({
    model: Thread,
    url: function () {
        return _.sprintf('/api/documents/%{docid}/threads', this.toJSON());
    },
    comparator: function (th) {
    },
    initialize: function () {
        var that = this;
        window.revisions.each(function (x) {
            var th = that.get(x.get('root'));
            th.addRevision(x);
          });
    }
});

//------------------------------------------------------------------------

var Revision = Backbone.Model.extend({
    upVote: function() {
        this.set({upVotes: this.get('upVotes') + 1});
        return this.upVotes
    },
    downVote: function() {
        this.set({downVotes: this.get('downVotes') + 1});
        return this.downVotes
    }
});

var RevisionCollection = Backbone.Collection.extend({
    model: Revision,
    url: function () {
        return '/api/documents/0/revisions'
    },
    initialize: function () {
        this.bind('add', function(x) {console.log(x)});
    },
    genThreads: function () {
        window.threads = new ThreadCollection(
            this.chain()
                .filter(function (x) {return x.id == x.get('root')})
                .map(function (x) { return {id: x.id} } )
                .value()
          );
    },
    comparator: function (rev) {
        return rev.get('score');
    }
});

window.revisions = new RevisionCollection([{"parent": 0, "text": "hello world", "downvotes": 0, "score": 0.6, "upvotes": 1, "root": 0, "id": 0}, {"parent": 0, "text": "hello cruel world", "downvotes": 1, "score": 0.4, "upvotes": 1, "root": 0, "id": 1}, {"parent": 1, "text": "hello cruel cruel world", "downvotes": 0, "score": 0.8, "upvotes": 2, "root": 0, "id": 2}, {"parent": 3, "text": "I like ponies", "downvotes": 0, "score": 0.6, "upvotes": 1, "root": 3, "id": 3}]);


window.revisions.genThreads();


//------------------------------------------------------------------------

var Vote = Backbone.Model.extend({
    initialize: function () {
        this.id = window.user.id;
    }
});

var VotesUp = Backbone.Collection.extend({
    model: Vote,
    url: function () {
        return _.sprintf('/api/documents/%{docid}/threads/%{threadid}/revisions/${revision}/upvotes', this.toJSON());
    }

});

var VotesDown = Backbone.Collection.extend({
    model: Vote,
    url: function () {
        return _.sprintf('/api/documents/%{docid}/threads/%{threadid}/revisions/${revision}/downvotes', this.toJSON());
    }

});

window.upvotes = new VotesUp;
window.downvotes = new VotesDown;

//------------------------------------------------------------------------

var User = Backbone.Model.extend({
    url: '/api/users'
});

//------------------------------------------------------------------------

//
// Backbone Views
//

var ThreadView = Backbone.View.extend({
    tagName: "li",
    render: function () {
        $(this.el).html(_.template("<%= topics %>", this.model.toJSON()));
        _(this.revisions)
            .each(function (rev) { rev.render(); });
        return this
    }
});

var RevisionView = Backbone.View.extend({
    tagName: "div",
    render: function() {
        $(this.el).html(_.template("<% text %>", this.model.toJSON()));
    }
});
