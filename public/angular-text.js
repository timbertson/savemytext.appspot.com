var BASE = '/api';
var quiet_seconds = 5;
var registry = {};
var defaultText = {
	key: null,
	title: '(untitled)',
	content: '',
	expanded:true
};
var log;

// --------------------------------

function TextController(log)
{
	this.log = log;
	this.$watch('text.form.content', this.ensureDelaySave);
	this.$watch('text.form.expanded', this.ensureDelaySave);
	this.$watch('text.form.title', this.ensureDelaySave);
}
TextController.$inject = ['$log'];

TextController.prototype = {
	ensureDelaySave: function() {
		var text = this.text;
		this.log.log("delaySave trigger on " + text.form.title);
		if(text.delaySave) {
			this.log.log("(replacing)");
			window.clearTimeout(text.delaySave);
		}
		var self = this;
		text.delaySave = window.setTimeout(function() {
			text.save();
			text.delaySave = null;
			self.$root.$eval();
		}, quiet_seconds * 1000);
	}
}

function Text(log, resource)
{
	this.log = log;
	this.resource = resource;
	this.form = angular.copy(this.resource);
	if(this.isPersisted()) {
		this.set_master(this.form);
	} else {
		this.set_master(defaultText);
	}
	var self = this;

	this.delaySave = null;
	this.inProgress = false;
}

Text.prototype = {
	set_master: function(new_master) {
		this.master = angular.copy(new_master);
	},

	toggleExpanded: function() {
		this.form.expanded = !this.form.expanded;
	},

	isPersisted: function() {
		return !! this.resource.key;
	},

	rows: function() {
		lines = this.form.content.split(/\n/).length;
		var rows = lines + 1;
		if (rows < 4) return 4;
		if (rows > 20) return 20;
		return rows;
	},

	isDeleted: function() {
		return this.master == null;
	},

	markDeleted: function() {
		this.master = null;
	},

	save: function() {
		this.log.log("saving: \"" + this.form.title + "\"");
		if(this.isDeleted()) {
			this.log.log("not saving deleted item");
			return;
		}
		if(this.isClean()) {
			this.log.log("not saving clean text.");
			return;
		}
		if(this.inProgress) {
			this.log.log("save already in progress...");
			return;
		}
		var self = this;
		this.inProgress = true;
		angular.copy(this.form, this.resource);
		this.resource.old_content = this.master.content;
		this.log.log("sending request, form = " + JSON.stringify(this.form));
		this.resource.$save(function(){
			self.log.log("saved. " + self.form.title);
			self.resource.old_content = null;
			self.set_master(self.resource);
			self.form.key = self.resource.key;
			self.inProgress = false;
		});
	},

	isClean: function() {
		var isClean = angular.equals(this.master, this.form);
		return isClean;
	},

	state: function() {
		var states = [];
		if(!this.isPersisted()) {
			states.push("fresh");
		}
		states.push(this.isClean() ? "clean" : "dirty");
		return states.join(" ");
	}
	
}

function Action(description, undo) {
	this.undo = undo;
	this.description = description;
};

// --------------------------

function Texts(log, $resource)
{
	this.debug = location.href.indexOf('verbose') != -1;
	this.log = log;
	this.loaded = false;
	this.TextResource = TextResource = $resource(BASE + '/text/:key', {key: '@key'});
	this.undo_actions = [];
	window.texts = this;

	//TODO: remove once this is fixed in either appengine or angular:
	this.TextResource.prototype.$do_remove = function() {
		return TextResource.remove({key:this.key});
	};

	var self = this;
	this.items = [];
	this.TextResource.query(function(items) {
		self.loaded = true;
		angular.forEach(items, function(item) {
			if(angular.isDefined(item.key)) {
				self.items.push(self.new_text(item));
			}
		});
		self.ensureAtLeastOneText();
	});
	this.$root.$set('texts', this);
	var existingTitle = $("title");
	var titleText = existingTitle.text();
	var newTitle = angular.element('<title>{{texts.unreadMarker()}}' + titleText + '</title>');
	var linker = angular.compile(newTitle);
	linker(this.$root, function(elem, scope) {
		existingTitle.replaceWith(elem);
	});
}

Texts.$inject = ['$log', '$resource'];

Texts.prototype = {
	ensureAtLeastOneText: function() {
		if(!this.loaded) return;
		if(this.items.length == 0) {
			this.log.log("ensuring at least one item");
			this.add();
		}
	},

	new_text: function(item) {
		return new Text(this.log, item);
	},

	remove: function(item) {
		this.log.log("removing: " + item.form.title);
		var self = this;
		if (item.isPersisted()) {
			item.resource.$do_remove();
		}
		item.markDeleted();
		angular.Array.remove(self.items, item);
		var self = this;
		this.add_undo(new Action("removed: " + item.form.title, function() {
			self.add(item.form);
		}));
		self.ensureAtLeastOneText();
	},

	add: function(text)
	{
		text = text || defaultText;
		text.key = null;
		var resource = new this.TextResource(text);
		var new_text = this.new_text(resource);
		this.items.unshift(new_text);
	},
	
	unreadMarker: function() {
		var count=0;
		angular.forEach(this.items, function(item) {
			if(!Text.prototype.isClean.call(item)) {
				count += 1;
			}
		});
		if(count > 0) {
			return "* ";
		}
		return "";
	},

	undo_action: function() {
		return this.undo_actions[0];
	},
	undo: function() {
		var undo_action = this.undo_actions.shift();
		undo_action.undo();
	},
	add_undo: function(action) {
		var self = this;
		this.undo_actions.push(action);
		window.setTimeout(function() {
			angular.Array.remove(self.undo_actions, action);
			self.$eval();
		}, 5000);
	},
	clear_undo: function() {
		this.undo_actions = [];
	}
}

// -------------------------------


angular.widget('tc:expando', function(compileElement){
	var compiler = this;
	compileElement.css('display', 'block');
	compiler.descend(true);
	var watch_expr = compileElement.attr('show');
	var identity_expr = compileElement.attr('identity');

	var setWithAnimation = function(doAnimate, elem, value) {
		if(!doAnimate) {
			if(!value) {
				elem.hide();
			} else {
				elem.show();
			}
		} else {
			if (value) {
				elem.delay(0).slideDown();
			} else {
				elem.slideUp();
			}
		}
	}
	return function(linkElement) {
		var currentScope = this;
		setWithAnimation(false, linkElement, currentScope.$eval(watch_expr));
		currentScope.$watch(watch_expr, function(value){
			var model_id = currentScope.$eval(identity_expr);
			var sameElement = linkElement.data("model_id") == model_id;
			setWithAnimation(sameElement, linkElement, value);
			linkElement.data("model_id", model_id);
		});
	};
});


// -------------------------------

var dirtyTexts = function() {
	return $('.text:not(.clean)');
}

var saveAll = function() {
	dirtyTexts().find(".save").click();
	return false;
}

var confirmExit = function() {
	var dirty = $.grep(dirtyTexts(), function(x) {
		x = $(x);
		if(x.hasClass("dirty")) return true;
		return x.find("textarea").attr("value") != "";
	});

	if(dirty.length > 0) {
		return "You have unsaved changes!";
	}
}

window.onbeforeunload = confirmExit;

$(function() {
	$("#ngtexts").show();
	$(window).keypress(function(event) {
		if (!(event.which == 19 && event.ctrlKey)) return true;
		event.preventDefault();
		saveAll();
	});
	$("#ngtexts form").live('submit', function(event) {
		event.preventDefault();
		saveAll();
	});
});




// override $xhr.error to alert the user when a conflict occurs
angular.service('$xhr.error', function(log){
	var rootScope = this;
	return function(request, response) {
		log.log("request failed! request:");
		log.log(request);
		log.log("... and response:");
		if(response.status == 409 && request.method == 'POST') {
			alert("Saving failed due to a conflict. Try refreshing your browser.");
		} else {
			throw("error: response failed with code " + response.status);
		}
	};
}, {$inject: ['$log']});

