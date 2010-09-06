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

function TextController()
{
	var self = this;
	this.$watch('text.form.content', this.ensureDelaySave);
	this.$watch('text.form.expanded', this.ensureDelaySave);
	this.$watch('text.form.title', this.ensureDelaySave);
	this.$watch('text.resource.title', function() {this.$parent.sort(); });
}

TextController.prototype = {
	ensureDelaySave: function() {
		var text = this.text;
		if(text.delaySave) {
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

function Text(resource)
{
	this.resource = resource;
	this.form = angular.copy(this.resource);
	this.set_master(this.form);
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
		if (rows > 40) return 40;
		return rows;
	},

	save: function() {
		if(this.isClean()) {
			return;
		}
		if(this.inProgress) {
			log.log("invalid save!");
			return;
		}
		var self = this;
		angular.copy(this.form, this.resource);
		this.inProgress = true;
		log.log("saving: " + this.form.title);
		this.resource.$save(function(){
			log.log("saved. " + self.form.title);
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
		if(!this.isPersisted()) {
			return "fresh";
		}
		return this.isClean() ? "clean" : "dirty";
	}
	
}

// --------------------------

function Texts()
{
	this.debug = location.href.indexOf('verbose') != -1;
	log = this.$log;
	this.loaded = false;
	this.TextResource = TextResource = this.$resource(BASE + '/text/:key', {key: '@key'});

	//TODO: remove onve this is fixed in either appengine or angular:
	this.TextResource.prototype.$do_remove = function() {
		return TextResource.remove({key:this.key});
	};

	var self = this;
	this.items = [];
	this.TextResource.query(function(items) {
		self.loaded = true;
		angular.foreach(items, function(item) {
			if(angular.isDefined(item.key)) {
				self.items.push(new Text(item));
			}
		});
		self.ensureAtLeastOneText();
	});
	this.$root.$set('texts', this);
}

Texts.prototype = {
	ensureAtLeastOneText: function() {
		if(!this.loaded) return;
		if(this.items.length == 0) {
			log.log("ensuring at least one item");
			this.add();
		}
	},

	remove: function(item) {
		if (!confirm("really remove?")) return;
		log.log("dead: " + item);
		var self = this;
		if (item.isPersisted()) {
			item.resource.$do_remove();
		}
		angular.Array.remove(self.items, item);
		self.ensureAtLeastOneText();
	},

	sort: function()
	{
		if(this.sorting) {
			return;
		}
		this.sorting = true;
		this.items = this.items.sort(function(a, b) {
			return (a.resource.title < b.resource.title)?-1:(a.resource.title == b.resource.title)?0:1;
		});
		this.$root.$eval();
		this.sorting = false;
	},

	add: function()
	{
		var resource = new this.TextResource(defaultText);
		var new_text = new Text(resource);
		this.items.unshift(new_text);
	}
}

// -------------------------------


angular.widget('tc:expando', function(element){
	element.css('display', 'block');
	this.descend(true);
	return function(element) {
		if(!this.$eval(element.attr('show'))) {
			element.hide();
		}
		var watch = element.attr('show');
		this.$watch(watch, function(value){
			if (value) {
				element.delay(0).slideDown();
			} else {
				element.slideUp();
			}
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
	$(window).keypress(function(event) {
		if (!(event.which == 19 && event.ctrlKey)) return true;
		event.preventDefault();
		return saveAll();
	});
});
