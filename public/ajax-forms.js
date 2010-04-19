var ajax_reqs = 0
function pushAjax(elm) { ajax_reqs += 1; if(ajax_reqs == 1) throb(); }
function popAjax(elm)  { ajax_reqs -= 1; if(ajax_reqs == 0) stopThrob(); }

function throb() {     $(".throb").fadeIn(100); }
function stopThrob() { $(".throb").fadeOut(100); }

var info;
var debug;
var PREVENT = {};

if(typeof(console) != "undefined") {
	// chrome doesn't like native code (i.e console.log) bound to
	// JS variables - so we curry it manually:
	info = function(s) { console.log(s) };
	debug = info;
} else {
	info = function(s) { alert(s) };
	debug = function(s) {}; // nothing to do
}

var transition_speed = 250; // 1/4 second

var fadeout_opacity = 0.2;
function fadeRepace(elem, replacement) {
	if(replacement) {
		replacement.css('opacity',fadeout_opacity)
		elem.replaceWith(replacement);
		elem = replacement;
	}
	elem.animate({'opacity':1, 'speed':transition_speed/2});
}

function markup(base) {
	// apply all unobtrusive JS to an element tree
	if (!base) { base = document.body; }
	makeConfirms(base);
	ajaxify(base);
	makeToggles(base);
}

function ajaxify(base) {
	$("form.ajax", base).submit(function(e) {
		if(PREVENT[e]) {
			// incredibly lame hand-rolled event-propagation,
			// but I can find nothing better from jQuery
			return false;
		}
		var frm = $(this);
		var ajax_flag = function(){ return $("input[name=ajax]", frm); }
		if(ajax_flag.length > 0) {
			alert("already submitted!");
			return false;
		}
		frm.prepend("<input name=\"ajax\" type=\"hidden\" value=\"true\" />");
		pushAjax(frm);

		var method = $("input[name=meth]", frm).val();
		var target_sel = $("input[name=dest]", frm).val();
		var target;
		if(target_sel[0] == '#'){
			target = $(target_sel);
		} else if (target_sel[0] == '.') {
			target = $(target_sel, frm);
		} else {
			target = frm.closest(target_sel);
		}
		if(target.length ==0) info("no target!");
		if(method == "replace"){
			target.animate({'opacity':fadeout_opacity, 'speed':transition_speed/2});
		}

		if(method == "status") {
			$("input[name=modified]", frm).val("false");
		}
		
		var cleanup = function() {
			ajax_flag().remove(); popAjax(frm);
		};
		
		$.ajax({
			url: frm.attr("action"),
			type: frm.attr("method"),
			data: frm.serialize(),
			dataType: "html",
			error: function(xhr, textStatus, err) {
				cleanup();
				if(method=='replace') {
					fadeRepace(target);
				}
				alert(xhr.responseText);
			},
			success: function(data, status) {
				cleanup();
				debug("Success!");
				var html = $(data, document);
				markup(html);
				if(method == "status") {
					if($("input[name=modified]", frm).val() == "false") {
						target.fadeTo(0, 1);
						target.text("saved");
						target.delay(3000).fadeTo(1000, 0.3);
					}
				} else if(method == "replace") {
					fadeRepace(target, html);
				} else if(method == "remove") {
					if(data.length > 0) {
						console.error("replacement HTML is nonzero: " + data);
					}
					target.slideUp(transition_speed, function(){target.remove()});
				} else {
					if(data.length > 0) {
						$(".placeholder", target).slideUp(); // remove any placeholder for emty content
						html.slideUp();
						if(method == "before"){
							target.prepend(html);
						} else {
							target.append(html);
						}
						html.hide().slideDown(transition_speed);
					}
				}
			},
		});
		return false; // stop propagation
	});
	
	$("form.ajax.autosave", base).each(function() {
		var frm = this;
		var timeout = null;
		var save_delay_time = 1000 * 10; //every 10 seconds after a change
		var reset_timer = function() {
			window.clearTimeout(timeout);
			timeout = null;
		};

		var timeout_func = function() {
			if(timeout == null) {
				return;
			}
			timeout = null;
			$("input[type=submit]", frm).submit();
		};

		var modifieds = $(".monitor_changes", frm);
		var apply_watch = function() {
			var check_delay_time = save_delay_time / 3;
			var elem = $(this);
			var value = elem.val();
			var check = function() {
				var new_value = elem.val();
				if (value != new_value) {
					value = new_value;
					elem.change();
				}
				window.setTimeout(check, check_delay_time);
			};
			window.setTimeout(check, check_delay_time);

			var change_func = function() {
				if(timeout) {
					reset_timer();
				}
				timeout = window.setTimeout(timeout_func, save_delay_time);
				$(".status", frm).text("pending...").fadeTo(1, 100);
				$("input[name=modified]", frm).val("true");
			};

			elem.change(change_func);
			elem.keypress(change_func);
		};

		modifieds.each(apply_watch);
	});
}

function makeToggles(base) {
	var toggleSelector = ".toggleContent";
	$(toggleSelector, base).each(function(){
		var container = $(this).closest(".toggleContainer");
		if (container.length == 0) {
			$(this).show();
			debug("no container for toggleContent!");
			return;
		}
		var toggleButton = $(".toggleButton", container);
		if(toggleButton.length == 0){
			var toggleButton = $("<div class=\"toggleButton\"></div>", document);
			container.prepend(toggleButton);
		}
		toggleButton.click(function() {
			$(toggleSelector, container).slideToggle(transition_speed);
			return false;
		});
	})
}

function makeConfirms(base) {
	$("input.confirm", base).each(function() {
		$(this).closest('form').submit(function(e) {
			PREVENT = {};
			PREVENT[e] = !confirm("Really?");
			return PREVENT[e];
		});
	});
}

document.write("<style> .startHidden { display: none; } </style>"); // hide toggleable content by default (but only if JS is enabled)

$(function(){markup()});

