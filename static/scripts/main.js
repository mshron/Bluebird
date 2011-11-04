// Backbone Models

//------------------------------------------------------------------------

var Document = Backbone.Model.extend({
});

var DocumentCollection = Backbone.Collection.extend({
    model: Document,
    url: '/api/documents'
});

//------------------------------------------------------------------------

var Thread = Backbone.Model.extend({
    root: function (rev) {
        this.set({'root': rev.id});
    }
});

var ThreadCollection = Backbone.Collection.extend({
    model: Thread,
    url: function () {
        return _.sprintf('/api/documents/%{docid}/threads', this.toJSON());
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
        return _.sprintf('/api/documents/%{docid}/threads/%{threadid}/revisions', this.toJSON());
    }
});

window.revisions = new RevisionCollection;

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

window.Revisions = new RevisionCollection();
