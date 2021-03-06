//$(function () {

//
// Convenience functions
//

function rnd () {
    return parseInt(Math.random()*(Math.pow(2,32))).toString('16');
}

function getid(u) {
    return u.split(':')[1];
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
        if (window.user === undefined) {
            alert("Login, human!");
            return 
        }

        // FIXME doesn't subselect for this document; tie in to top vote numbe
        var nvotes = window.user.get('up_voted').length + window.user.get('down_voted').length;
        var up = this.get('user_voted_up');
        var down = this.get('user_voted_down');
        console.log(nvotes, up, down);

        if (!up && !down && nvotes < 5) {
            this.set({up: this.get('up') + 1});
            this.set({user_voted_up: true});
            console.log(window.user.get('up_voted'));
            window.user.get('up_voted').push('Revision:'+this.id);
            console.log(window.user.get('up_voted'));
            window.user.trigger('change');
            $.get(this.voteurl + "1");
        }
        else if (up) {
            this.set({up: this.get('up') - 1});
            this.set({user_voted_up: false})
            console.log(window.user.get('up_voted'));
            window.user.get('up_voted').pop(window.user.get('down_voted').indexOf('Revision:'+this.id));
            console.log(window.user.get('up_voted'));
            window.user.trigger('change');
            $.get(this.voteurl + "0");
        }
    },
    downVote: function() {
        if (window.user === undefined) {
            alert("Login, human!");
            return 
        }

        var nvotes = window.user.get('up_voted').length + window.user.get('down_voted').length;
        var up = this.get('user_voted_up');
        var down = this.get('user_voted_down');

        if (!down && !up && nvotes < 5) {
            this.set({down: this.get('down') + 1});
            this.set({user_voted_down: true});
            window.user.get('down_voted').push('Revision:'+this.id);
            window.user.trigger('change');
            $.get(this.voteurl + "-1");
        }
        else if (down) {
            this.set({down: this.get('down') - 1});
            this.set({user_voted_down: false})
            window.user.get('down_voted').pop(window.user.get('down_voted').indexOf('Revision:'+this.id));
            window.user.trigger('change');
            $.get(this.voteurl + "0");
        } //else if (this.id  0
    },
    fork: function (text) {
        var f = this.clone();
        f.set({'parent': this.id});
        f.set({'score': this.get('score')*.9999});
        f.set({'id': rnd()});
        f.set({'text': text});
        f.unset('user_voted_up');
        f.unset('user_voted_down');
        f.unset('documentid');
        this.trigger('register', f);
        f.save();
        f.trigger('checkuser');
    },
    defaults: {
        "up": 0,
        "down": 0,
        "score": 0,
        "user_voted_up": false,
        "user_voted_down": false
    },
    initialize: function () {
        //this.set({'id': getid(this.get('key'))});
        this.set({'documentid': getid(this.get('document'))});
        this.set({'id': getid(this.get('key'))});
        this.voteurl = "/api/documents/"+this.get('documentid')+"/revisions/"+this.get('id')+"/vote?type=";
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
        console.log('foo');
        rev.save();
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
    initialize: function() {
        this.bind('change', this.update, this)
    },
    update: function() {
        var total_votes = 0;
        _.each(this.get('up_voted'),
               function (rid) {
                    rev = window.revisions.get(getid(rid));
                    if (rev!==undefined) {
                        rev.set({'user_voted_up': true});
                        total_votes += 1;
                    }
               }, this)
        _.each(this.get('down_voted'),
               function (rid) {
                    rev = window.revisions.get(getid(rid));
                    if (rev!==undefined) {
                        rev.set({'user_voted_down': true});
                        total_votes += 1;
                    }
               }, this)
        window.Main.populateUserData(total_votes);
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
        this.$('.revisions-content').html('');
        this.$('.revision-count').html(public_count);

        if(public_count < 1) this.$('.edit-count').addClass('no_edits');
        if(public_count == 1) this.$('.edits-label').html('Edit');

        this.model.each(function (rev, idx) {
            rev.set({
            	"idx" : idx,
            	"edit_count" : public_count
            });
			that.$('.revisions-content').append(new RevisionView({model: rev}).render().el);
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
        'click .improve'	: 'improve',
        'click .edit-count'	: 'improve',
        'click .idea-text a': 'improve',
    },
    improve: function () {
        if (this.improve) { // Close Idea

        	window.Main.close_dialog();
            var offset = $(this.el).offset();
        	var travel = offset.top;
        	var b_travel = ( $(window).height() - travel - $(this.el).height() );
            clone_wrap = this.$('.slider');
            
            this.$('.revisions').fadeOut(200,function() {
            	$(clone_wrap).animate({ top: travel + 'px', bottom: b_travel +"px" }, 400,
					function() {
						$(clone_wrap).fadeOut(100,function() {
		    				$(clone_wrap).remove();	
		    			});
	  				}
				);
            });
            this.improve = false;
        }
        else { // Open Idea
        
        	window.Main.close_dialog();
        	revheight = $(this.el).height();
        	var offset = $(this.el).offset();
        	var travel = offset.top;
        	var b_travel = ( $(window).height() - travel - $(this.el).height() );
        	var that = this;
        	
        	// Duplicate idea row
        	item = $(this.el).find('.idea-wrap');            
            clone = $(item[0]).clone();
			$(clone).css("box-shadow","0 0 5px rgba(0, 0, 0, 0.1)");
			$(clone).children("div.idea").css("padding-left",0);

			clone_wrap = $(document.createElement('div'));
			$(clone_wrap).addClass("slider");
			$(clone).appendTo(clone_wrap);
			$(clone_wrap).appendTo(this.el);
			$(clone_wrap).css("top",travel + "px");
			$(clone_wrap).css("bottom",b_travel + "px");
			
			// Slide up and show the revisions
			$(clone_wrap).animate({ top: '62px', bottom: "0"}, 300,
				function() {
					that.$('.revisions').css("top",(revheight + 62) + "px");
		    		that.$('.revisions').fadeIn(300);
  				}
			);
            this.improve = true;
        }
    }
});

var RevisionView = Backbone.View.extend({
    tagName: "div",
    template: _.template($('#revision-template').html()),
    render: function() {
        $(this.el).html(this.template(this.model.toJSON()));
        $(this.el).removeClass('voted_up').removeClass('voted_down');
        if (this.model.get('user_voted_up')) {
            $(this.el).addClass('voted_up');
        }
        if (this.model.get('user_voted_down')) {
            $(this.el).addClass('voted_down');
        }

        return this;
    },
    initialize: function () {
        this.model.bind('all', this.render, this);
    },
    finishFork: function () {
        this.model.fork($("#fork-input textarea").val());
    },
    startFork: function () {
        $('#fork-input textarea').val(this.model.get('text'));
        $('#fork-input').unbind();
        var that = this;
        $('#fork-input .done').click(function () { that.finishFork() });
        $('#fork-input .done').click(function () { window.Main.close_dialog() });
        $('#fork-input').toggle();
    },
    events: {
        "click .fork"		: "startFork",
        "click .upvote"		: "upvote",
        "click .downvote"	: "downvote",
    },
    upvote: function() {
        this.model.upVote();
    },
    downvote: function() {
        this.model.downVote();
    },
    editing: function () {
        $(this.el).addClass('editing');
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
        var t = _(this.ideas).find(function (th) {return th.root == root });
        if (!t) {
            this.ideas.push(new RevisionsInAIdea([rev]));
        }
        else {
            t.add(rev);
        }
    },
    render:  function () {
        this.$('#ideas').html('');
        var that = this;
        _(this.ideas).each(function (th) {
			that.$('#ideas').append(new RevisionsInAIdeaView({model: th}).render().el)
		});
    },
    populateUserData: function (total_votes) {
		$("#screen_name strong").html(window.user.get('screen_name'));
		$("#screen_name").show();
		$("#header-right .remaining .header-link").html(5 - total_votes);
		/* $(".dialog").draggable({ handle: '.dialog-header' }); */
		$.ajax({
			url: "/api/documents",
			success: function(data){
				var pathname = getid(window.revisions.first().get('document'));
				$(data).each(function(i,doc) {
					if(doc.id == pathname) $("#doc-title").text(doc.name);
				});
			}
		});
		
    },
    events: {
        "click #new-idea-box .done": "newIdea",
        "keypress .new-text": "pressenter",
        "click .refresh": "refresh",
        'click .show-idea-box': 'idea_dialog',
        'click .close-dialog': 'close_dialog'
    },
    pressenter: function (e) {
        if (e.keyCode == 13) {
        
        }
    },
    refresh: function () {
        window.revisions.fetch();
    },
    newIdea: function () {
        /* console.log('newidea'); */
        var rev = new Revision({'text': this.$('.new-text').val(), 
                                'parent': '', 'document': this.documentid});
        window.revisions.add(rev);
        this.$('.new-text').val('');
        rev.trigger('save', rev);
        this.render();
        this.idea_dialog();
    },
    idea_dialog: function () {
    	$('#new-idea-box').toggle();
    	$('#new-idea-box textarea').focus();
    },
    close_dialog: function () {
    	//console.log(this);
    	$(".dialog").hide();
    }

});

window.Main = new MainView;

//}); // I open at the close (of DOM rendering).

