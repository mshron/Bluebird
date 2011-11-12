//$(function () {

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
    //    return th.get('revisions').count()
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
        s = this;
        q = f;
        f.set({'parent': this.id});
        f.set({'score': this.get('score')*.9999});
        f.forking = true;
        this.trigger('register', f);
    },
    defaults: {
        "up": 0,
        "down": 0
    },
    initialize: function () {
        this.set({'id': rnd()});
        if (!this.get('parent')) {
            this.set({'root': this.get('id')});
        }
    }

});

var RevisionCollection = Backbone.Collection.extend({
    model: Revision,
    url: function () {
        return '/api/documents/' + this.documentid + '/revisions'
    },
    initialize: function () {
       this.bind('register', this.register, this);
       this.bind('reset', this.setdoc, this);
    },
    register: function (rev) {
        this.add(rev);
    },
    setdoc: function (revs) {
       this.documentid = revs.first().get('document').split(':')[1];
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

var MainView = Backbone.View.extend({
    el: '#main',
    initialize: function () {
        this.el = $('#main');
        window.revisions = new RevisionCollection;
        window.revisions.bind('add', this.addRevision, this);
        window.revisions.bind('reset', this.reset, this);
    },
    reset: function (revs) {
        this.threads = new ThreadCollection;
        var that = this;
        revs.each(function (rev) {that.addRevision(rev)} );
        this.render();
    },
    addRevision: function (rev) {
        var t = this.threads.get(rev.get('root'));
        if (t) {
           t.add(rev); 
        } else {
            this.threads.add({'revisions': new RevisionsInAThread([rev]),
                              'id': rev.get('root')});
        }
        var t = this.threads.get(rev.get('root'));
    },
    render:  function () {
        this.$('#threads').html('');
        var that = this;
        this.threads.each(function (th) {
                            that.$('#threads')
                                .append(new ThreadView({model: th}).render().el)
                          });
    },
    events: {
        "click .done": "newThread",
        "keypress .new-text": "pressenter",
        "click .refresh": "refresh"
    },
    pressenter: function (e) {
        if (e.keyCode == 13) {
            this.newThread();
        }
    },
    refresh: function () {
        window.revisions.fetch();
    },
    newThread: function () {
        window.revisions.add({'text': this.$('.new-text').val()});
        this.$('.new-text').val('');
        this.render();
    }

});

window.Main = new MainView;

//}); // I open at the close (of DOM rendering).
