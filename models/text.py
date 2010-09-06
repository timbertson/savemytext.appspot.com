from google.appengine.ext import db

from logging import debug, info, warning, error
from base import BaseModel

class Text(BaseModel):
	title = db.StringProperty(required=False)
	content = db.TextProperty()
	owner = db.UserProperty(required=True)
	expanded = db.BooleanProperty(default=True)

	def __init__(self, *a, **k):
		super(type(self), self).__init__(**k)
		if not self.title:
			self.title = "(untitled)"

	@classmethod
	def add(cls, owner):
		text = cls(owner=owner, content='', title='')
		text.save()
		return text

	@classmethod
	def find_all(cls, owner):
		return db.Query(cls).filter('owner =', owner).order('title').fetch(limit=50)
	
	@classmethod
	def find(cls, owner, key):
		text = cls.get(key)
		if text and text.owner == owner:
			return text

