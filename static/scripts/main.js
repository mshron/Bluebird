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
        q = f;
        f.set({'parent': this.id});
        f.set({'score': this.get('score')*.9999});
        f.set({'id': rnd()});
        f.forking = true;
        this.trigger('register', f);
    },
    defaults: {
        "up": 0,
        "down": 0,
        "score": 0
    },
    initialize: function () {
		/*
		if (!this.get('parent')) {
            this.set({'id': rnd()});
            this.set({'root': this.get('id')});
            this.set({'parent': this.get('id')});
        }
        */
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
       this.bind('save', this.save, this);
    },
    setdoc: function (revs) {
       this.documentid = revs.first().get('document').split(':')[1];
    },
    save: function (rev) {
        rev.save();
    },
    register: function(rev) {
        this.add(rev);
    }
});

var RevisionsInAIdea = Backbone.Collection.extend({
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
       this.root = this.first().get('root');
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

var RevisionsInAIdeaView = Backbone.View.extend({
    tagName: "div",
    template: _.template($('#idea-template').html()),
    render: function () {
        var that = this;
        var public_count = (that.model.length - 1);

        this.$('.top-text').html(that.model.first().get('text'));
        this.$('.revisions').html('');
        this.$('.revision-count').html(public_count);

        if(public_count < 1) this.$('.edit-count').addClass('no_edits');
        if(public_count == 1) this.$('.edits-label').html('Edit');
        
        this.model.each(function (rev) {
			that.$('.revisions').append(new RevisionView({model: rev}).render().el);
		}); 
        return this;
    },
    initialize: function () {
        this.rvs = [];
        $('#ideas').append(this.el);
        this.model.bind('add', this.render, this);
        this.improve = false;
        $(this.el).html(this.template({}));
    },
    events: {
        'click .improve': 'improve',
        'click .edit-count': 'improve',
        'click .idea-text a': 'improve',
    },
    improve: function () {
        if (this.improve) {
            this.$('.revisions').addClass('noimprove');
            this.improve = false;
        } else {
            this.$('.revisions').removeClass('noimprove');
            this.improve = true;
        }
		return false;
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
        "click .fork": "doFork",
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
        this.model.trigger('save', this.model);
    }
});

//------------------------------------------------------------------------

var MainView = Backbone.View.extend({
    el: '#main',
    initialize: function () {
        this.el = $('#main');
        this.ideas = [];
        window.revisions = new RevisionCollection;
        window.revisions.bind('reset', this.reset, this);
        window.revisions.bind('done', this.render, this);
    },
    reset: function (revs) {
        this.ideas = [];
        var that = this;
        revs.each(function (rev) {that.addRevisionToIdea(rev)} );
        this.render();
        window.revisions.bind('add', this.addRevisionToIdea, this);
        this.documentid = window.revisions.first().get('document');
    },
    addRevisionToIdea: function (rev) {
        var root = rev.get('root');
        var t = _(this.ideas)
                 .find(function (th) {return th.root == root });
        if (!t) {
            this.ideas.push(new RevisionsInAIdea([rev]));
        } else {
            t.add(rev);
        }
    },
    render:  function () {
        this.$('#ideas').html('');
        var that = this;
        _(this.ideas).each(function (th) {
                            that.$('#ideas')
                                .append(new RevisionsInAIdeaView({model: th}).render().el)
                          });
    },
    events: {
        "click .done": "newIdea",
        "keypress .new-text": "pressenter",
        "click .refresh": "refresh",
        'click .show-idea-box': 'idea_dialog',
        'click .close-dialog': 'idea_dialog'
    },
    pressenter: function (e) {
        if (e.keyCode == 13) {
            //this.newIdea();
        }
    },
    refresh: function () {
        window.revisions.fetch();
    },
    newIdea: function () {
        var rev = new Revision({'text': this.$('.new-text').val(), 
                                'parent': '', 'document': this.documentid});
        window.revisions.add(rev);
        window.revisions.trigger('save', rev);
        this.$('.new-text').val('');
        this.render();
    },
    idea_dialog: function () {
    	$('#new-idea-box').toggle();
    }

});

window.Main = new MainView;

//}); // I open at the close (of DOM rendering).
