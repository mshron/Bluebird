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
        f.set({'id': rnd()});
        f.forking = true;
        this.trigger('register', f);
    },
    defaults: {
        "up": 0,
        "down": 0
    },
    initialize: function () {
        if (this.get('parent')=='') {
            this.set({'id': rnd()});
            this.set({'root': this.get('id')});
            this.set({'parent': this.get('id')});
        }
    }

});

var RevisionCollection = Backbone.Collection.extend({
    model: Revision,
    url: function () {
        return '/api/documents/' + this.documentid + '/revisions'
    },
    initialize: function () {
       this.bind('register', this.add, this);
       this.bind('reset', this.setdoc, this);
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
       this.bind('register', this.add, this);
       this.root = this.first().get('root');
       console.log(this.root);
    },
});

//------------------------------------------------------------------------

var User = Backbone.Model.extend({
    url: '/api/users'
});

//------------------------------------------------------------------------

//
// Backbone Views
//

var RevisionsInAThreadView = Backbone.View.extend({
    tagName: "li",
    template: _.template($('#thread-template').html()),
    render: function () {
        $(this.el).html(this.template(this.model.toJSON()));
        var that = this;
        this.model
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
        this.threads = [];
        window.revisions = new RevisionCollection;
        window.revisions.bind('reset', this.reset, this);
        window.revisions.bind('done', this.render, this);
    },
    reset: function (revs) {
        this.threads = [];
        var that = this;
        revs.each(function (rev) {that.addRevisionToThread(rev)} );
        this.render();
        window.revisions.bind('add', this.addRevisionToThread, this);
    },
    addRevisionToThread: function (rev) {
        var root = rev.get('root');
        var t = _(this.threads)
                 .find(function (th) {return th.root == root });
        if (!t) {
            this.threads.push(new RevisionsInAThread([rev]));
        }
    },
    render:  function () {
        this.$('#threads').html('');
        var that = this;
        _(this.threads).each(function (th) {
                            that.$('#threads')
                                .append(new RevisionsInAThreadView({model: th}).render().el)
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
        var rev = new Revision({'text': this.$('.new-text').val(), 'parent': ''});
        window.revisions.add(rev);
        this.addRevisionToThread(rev);
        this.$('.new-text').val('');
        this.render();
    }

});

window.Main = new MainView;

//}); // I open at the close (of DOM rendering).
