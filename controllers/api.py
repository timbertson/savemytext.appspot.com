from base import *
from models import Text
from models.base import BaseModel
from logging import debug, info
from django.utils import simplejson as JSON

def flatten(obj):
	if isinstance(obj, list):
		return map(flatten, obj)
	if isinstance(obj, BaseModel):
		return obj.to_dict()
	return obj

def json(obj, self):
	JSON.dump(flatten(obj), self.response.out)

def param(name):
	def _getter(self):
		return self._get_param(name)
	return _getter

class TextHandler(BaseHandler):
	title = param('title')
	content = param('content')

	def _update(self, key):
		user = self.user()
		doc = self._postdata()
		if not key:
			info("adding new text")
			text = Text(owner=user)
			try:
				del doc['old_content']
			except KeyError: pass
		else:
			info("updating text with key=%r, title=%s" % (key,doc.get('title', None)))
			text = Text.find(owner=user, key=key)

		if text is None:
			raise HttpError(404, "no such textarea to edit!")
		try:
			if doc['old_content'] != text.content:
				raise HttpError(409, "existing content does not match datastore")
			logging.info("old_content matched datastore")
		except KeyError:
			logging.info("no old_content given - assuming no conflict")
		text.content = doc['content']
		text.title = doc['title']
		text.expanded = doc.get('expanded', True)
		text.save()
		return text

	def _postdata(self):
		return JSON.loads(self.request.body)
	
	def _render(self, obj=None):
		json(obj, self)

class SpecificTextHandler(TextHandler):
	def post(self, key):
		self._render(self._update(key))
	
	def delete(self, key):
		text = Text.find(owner=self.user(), key=key)
		if text:
			text.delete()
			self._render()
		else:
			info("could not find text" % (key,))
			raise HttpError(404, "could not find text")
	
	def get(self, key):
		self._render(Text.find(self.user(), key))

class TextSetHandler(TextHandler):
	def get(self):
		self._render(Text.find_all(self.user()))

	def post(self):
		self._render(self._update(None))

class TextDeleteHandler(SpecificTextHandler):
	# alias for DELETE on TextHandler
	post = SpecificTextHandler.delete
