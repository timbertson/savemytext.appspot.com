import cgi

from base import *
from models import Text
from logging import debug, info

class TextHandler(BaseHandler):
	def key(self):
		return self._get_param('key')

	def title(self):
		return self._get_param('title')

	def content(self):
		return self._get_param('content')

	def _add(self, user, title, content):
		text = Text(user=self.user(), title=self.title(), content=self.content())
		text.save()
		return text.key()
	
	def _update(self, user, title, content, key):
		info("updating text with key: %s" % (key,))
		if key is None:
			return self._add(user, title,content,key)
		text = Text.find(user, key)
		text.content = self.content()
		text.title = self.title() or ''
		text.save()
		return text

	def post(self):
		text = self._update(self.user(), self.title(), self.content(), self._get_param('key',None))
		self._render_success(text)
	
	def delete(self):
		text = Text.find(owner=self.user(), key=self.key())
		if text:
			text.delete()
			self._render_success()
		else:
			info("could not find text" % (self.key(),))
			raise HttpError(404, "could not find text")
	
	def _render_success(self, tex):
		if self.is_ajax():
			self.response.out.write(tex.key())
		else:
			self.redirect('/')


class TextDeleteHandler(TextHandler):
	# alias for DELETE on TextHandler
	get = post = TextHandler.delete
