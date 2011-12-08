//$(function () {

//
// Convenience functions
//

function rnd () {
    return parseInt(Math.random()*(Math.pow(2,32))).toString('16');
}

function getid(u) {
    if (u.indexOf(':') > 0) {
        return u.split(':')[1];
    } else {
        return u;
    }
    
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
        if (this.get('user_voted_up') == null) {
            alert("Login, human!");
            return 
        }
        if ((!this.get('user_voted_up') && !this.get('user_voted_down')) 
                && window.user.get('up_voted').length<3) {
            this.set({up: this.get('up') + 1});
            this.set({user_voted_up: true});
            $.get(this.voteurl + "1");
        } else if (this.get('user_voted_up')) {
            this.set({up: this.get('up') - 1});
            this.set({user_voted_up: false})
            $.get(this.voteurl + "0");

        }
        return
    },
    downVote: function() {
        if (this.get('user_voted_down') == null) {
            alert("Login, human!");
            return 
        }
        if ((!this.get('user_voted_up') && !this.get('user_voted_down')) 
                && window.user.get('down_voted').length<3) {
            this.set({down: this.get('down') + 1});
            this.set({user_voted_down: true});
            window.user.get('down_voted').push('Revision:'+this.id);
            $.get(this.voteurl + "-1");
        } else if (this.get('user_voted_down')) {
            this.set({down: this.get('down') - 1});
            this.set({user_voted_down: false})
            $.get(this.voteurl + "0");
        } //else if (this.id  0

        return
    },
    fork: function () {
        var f = this.clone();
        q = f;
        f.set({'parent': this.id});
        f.set({'score': this.get('score')*.9999});
        f.set({'id': rnd()});
        f.unset('user_voted_up');
        f.unset('user_voted_down');
        f.unset('documentid');
        f.unset('edit_count');
        f.forking = true;
        this.trigger('register', f);
        f.trigger('checkuser');
    },
    defaults: {
        "up": 0,
        "down": 0,
        "score": 0
    },
    checkuser: function () {
        if (window.user) {
            this.set({'user_voted_up' : _(
                                   _(window.user.get('up_voted')).map(getid)
                                  ).include(this.get('id')) })

            this.set({'user_voted_down' : _(
                                   _(window.user.get('down_voted')).map(getid)
                                  ).include(this.get('id'))})

        } else {
            this.set({'user_voted_up': null});
            this.set({'user_voted_down': null});
        }
    },
    initialize: function () {
        this.set({'id': getid(this.get('key'))});
        this.set({'documentid': getid(this.get('document'))});
        this.voteurl = "/api/documents/"+this.get('documentid')+"/revisions/"+this.get('id')+"/vote?type=";
        this.bind('checkuser', this.checkuser, this);
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
       this.bind('checkusers', this.checkuser, this);
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
    },
    checkuser: function() {
        this.each(function (rev) {rev.trigger('checkuser')});
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
    urlRoot: '/api/users/',
    init: function() {
        this.id = window.user_id;
    }
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

        this.model.each(function (rev, idx) {
            rev.set({
            	"idx" : idx,
            	"edit_count" : public_count
            });
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
            //this.$('.revisions').hide();
            this.$('.revisions').fadeOut(300);
            this.improve = false;
        } else {
            this.$('.revisions').fadeIn(300);
            this.improve = true;
        }
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
        "click .upvote": "upvote",
        "click .downvote": "downvote",
        "click .close-dialog" : "cancelEditing"
    },
    upvote: function() {
        this.model.upVote();
    },
    downvote: function() {
        this.model.downVote();
    },
    editing: function () {
        $(this.el).addClass('editing');
        //$(this.el).hide()
    },
    endEditing: function () {
        $(this.el).show();
        this.model.forking = false;
        this.model.set({'text': this.$('.edit-text').val()});
        this.model.trigger('save', this.model);
    },
    cancelEditing: function () {
    	//$(this.el).removeClass("editing");
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
