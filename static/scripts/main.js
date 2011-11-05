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
        this.bind('all', this.orderRevs, this);
    },
    addRevisionision: function (rev) {
        this.revisions.push(rev);
    },
    orderRevs: function () {
        console.log('foo');
        this.revisions = _(this.revisions)
                          .sortBy(function (rev) { return rev.get('score') })
    }
});

var ThreadCollection = Backbone.Collection.extend({
    model: Thread,
    comparator: function (th) {
        var up = _(th.revisions)
                  .chain()
                  .map(function (rev) { return rev.get('upvotes') })
                  .reduce(function (memo,num) { return memo+num }, 0)
                  .value();
        var down = _(th.revisions)
                  .chain()
                  .map(function (rev) { return rev.get('downvotes') })
                  .reduce(function (memo,num) { return memo+num }, 0)
                  .value();
        return down-up;
    },
    initialize: function () {
        var that = this;
        window.revisions.each(function (x) {
            var th = that.get(x.get('root'));
            th.addRevisionision(x);
          });
    }
});

//------------------------------------------------------------------------

var Revision = Backbone.Model.extend({
    upVote: function() {
        this.set({upVotes: this.get('upvotes') + 1});
        return this.upVotes
    },
    downVote: function() {
        this.set({downVotes: this.get('downvotes') + 1});
        return this.downVotes
    }
});

var RevisionCollection = Backbone.Collection.extend({
    model: Revision,
    url: function () {
        return '/api/documents/0/revisions'
    },
    initialize: function () {
    },
    genThreads: function () {
        window.threads = new ThreadCollection(
            this.chain()
                .filter(function (x) {return x.id == x.get('root')})
                .map(function (x) { return {id: x.id} } )
                .value()
          );
        window.threads.sort();
    },
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
    template: _.template($('#thread-template').html()),
    addRevision: function (rev) {
       var rv = new RevisionView({model: rev});
       this.rvs.push(rv);
    },
    render: function () {
        $(this.el).html(this.template(this.model.toJSON()));
        var that = this;
        _(this.rvs).each(function (rv) {
            that.$('.revisions').append(rv.el)
        });
    },
    initialize: function () {
        this.rvs = [];
        var that = this;
        $('#threads').append(this.el);
        _(this.model.revisions)
         .each(function (rev) { that.addRevision(rev) });
        this.model.bind('all', this.render, this);
    }
});

var RevisionView = Backbone.View.extend({
    tagName: "div",
    template: _.template($('#revision-template').html()),
    render: function() {
        $(this.el).html(this.template(this.model.toJSON()));
    },
    initialize: function () {
        this.model.bind('all', this.render, this);
    }
});


//------------------------------------------------------------------------

window.threadViews = window.threads
                        .map(function (th) {return new ThreadView({model: th})});


window.threads.map(function (th) {th.trigger('go')});
window.revisions.map(function (rev) {rev.trigger('go')});
