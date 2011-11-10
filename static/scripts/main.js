//
// Convenience functions
//

function rnd () {
    return parseInt(Math.random()*(Math.pow(2,32))).toString('16');
}

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
    }
});

var ThreadCollection = Backbone.Collection.extend({
    model: Thread,
    comparator: function (th) {
        return th.get('revisions').count()
    },
    initialize: function () {
    }
});

//------------------------------------------------------------------------

var Revision = Backbone.Model.extend({
    upVote: function() {
        this.set({upVotes: this.get('up') + 1});
        return this.upVotes
    },
    downVote: function() {
        this.set({downVotes: this.get('down') + 1});
        return this.downVotes
    },
    fork: function () {
        var f = this.clone();
        f.set({'parent': this.id, 'id': rnd()});
        f.set({'score': this.get('score')*.9999});
        f.forking = true;
        this.trigger('register', f);
    }

});

var RevisionCollection = Backbone.Collection.extend({
    model: Revision,
    url: function () {
        return '/api/documents/48e57d25f4b2d4c8/revisions'
    },
    initialize: function () {
       this.bind('register', this.register, this);
    },
    genThreads: function () {
        window.threads = new ThreadCollection(
            this.chain()
                .groupBy(function (x) {return x.get('root')})
                .map(function (xs) {
                  return {'revisions': new RevisionsInAThread(xs), 
                          'id': xs[0].get('root') }})
                .value()
          );
    },
    register: function (rev) {
        this.add(rev);
    }
});

var RevisionsInAThread = Backbone.Collection.extend({
    model: Revision,
    comparator: function (rev) {return -rev.get('score')},
    count: function () {
        var up =  this.chain()
                  .map(function (rev) { return rev.get('up') })
                  .reduce(function (memo,num) { return memo+num }, 0)
                  .value();
        var down = this.chain()
                  .map(function (rev) { return rev.get('down') })
                  .reduce(function (memo,num) { return memo+num }, 0)
                  .value();
        return down-up;
    },
    initialize: function () {
       this.bind('register', this.register, this);
       this.root = this.first().get('root');
    },
    register: function (rev) {
        this.add(rev);
        window.threads.get(this.root).trigger('addrevision',rev);
    }
});

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
    render: function () {
        $(this.el).html(this.template(this.model.toJSON()));
        var that = this;
        this.model.get('revisions')
            .each(function (rev) {
                console.log(rev.get('id'))
                that.$('.revisions')
                    .append(new RevisionView({model: rev}).render().el);
            }); 
        return this
    },
    initialize: function () {
        this.rvs = [];
        $('#threads').append(this.el);
        this.model.bind('all', this.render, this);
    }
});

var RevisionView = Backbone.View.extend({
    tagName: "div",
    template: _.template($('#revision-template').html()),
    render: function() {
        $(this.el).html(this.template(this.model.toJSON()));
        return this;
    },
    initialize: function () {
        this.model.bind('all', this.render, this);
        if (this.model.forking == true) {
            this.editing();
        }
    },
    doFork: function () {
        this.model.fork();        
    },
    events: {
        "click .text": "doFork",
        "click .done": "endEditing",
        "keypress .edit-text": "pressenter"
    },
    editing: function () {
        $(this.el).addClass('editing');
    },
    pressenter: function (e) {
        if (e.keyCode == 13) {
            this.endEditing();
        }
    },
    endEditing: function () {
        $(this.el).removeClass('editing');
        this.model.forking = false;
        this.model.set({'text': this.$('.edit-text').val()});
        this.model.save();
    }
});

//------------------------------------------------------------------------

window.revisions = new RevisionCollection([{"parent": 0, "text": "hello world", "down": 0, "score": 0.6, "up": 1, "root": 0, "id": 0}, {"parent": 0, "text": "hello cruel world", "down": 1, "score": 0.4, "up": 1, "root": 0, "id": 1}, {"parent": 1, "text": "hello cruel cruel world", "down": 0, "score": 0.8, "up": 2, "root": 0, "id": 2}, {"parent": 3, "text": "I like ponies", "down": 0, "score": 0.6, "up": 1, "root": 3, "id": 3}]);

//window.revisions = new RevisionCollection();

//window.revisions.fetch();

window.revisions.genThreads();

window.threadViews = window.threads
                        .map(function (th) {return new ThreadView({model: th})});

window.threads.map(function (th) {th.trigger('go')});
