import cgi

from base import *
from models import Text
from logging import debug, info
from view_helpers import render_snippet

class TextHandler(BaseHandler):
	def key(self):
		return self._get_param('key')

	def title(self):
		return self._get_param('title')

	def content(self):
		return self._get_param('content')

	def _add(self, user):
		text = Text.add(owner=user)
		text.save()
		return text

	def _update(self, user, title, content, key):
		if not key:
			info("adding new text")
			return self._add(user)
		info("updating text with key=%s, title=%s" % (key,title))
		text = Text.find(user, key)
		if text is None:
			raise HttpError(404, "no such textarea to edit!")
		text.content = content
		text.title = title or ''
		text.save()
		return text

	def post(self):
		text = self._update(self.user(), self.title(), self.content(), self._get_param('key',''))
		self._render_success(text)
	
	def delete(self):
		text = Text.find(owner=self.user(), key=self.key())
		if text:
			text.delete()
			self._render_success()
		else:
			info("could not find text" % (self.key(),))
			raise HttpError(404, "could not find text")
	
	def _render_success(self, text = None):
		info("ajax = %s" % (self.is_ajax()))
		if self.is_ajax():
			if text is not None:
				self.response.out.write(render_snippet('text', {'text':text}))
		else:
			info("REDIRECTING!")
			self.redirect('/')


class TextDeleteHandler(TextHandler):
	# alias for DELETE on TextHandler
	get = post = TextHandler.delete
