import logging
import json
import urllib2
import re
import sys
import commands

import appengine_auth
from common import *

def init_api(user, password=None):
	logging.debug("base = %s" % (BASE,))
	app = appengine_auth.App('savemytext', BASE)
	if not password:
		status, password = commands.getstatusoutput("zenity --entry --hide-text --text='Google password for %s'" % (user,))
		if status != 0:
			sys.exit(1)
	logging.debug("logging in as %s..." % (user,))
	try:
		app.login(email=user, password=password)
	except appengine_auth.AuthError:
		logging.error("login failed - check your credentials")
		sys.exit(1)
	logging.debug("login successful")
	return SaveMyText(app)


class SaveMyText(object):
	def __init__(self, app):
		self.app = app
		self.base = app.base_url + 'api/text/'
	
	def request(self, method, path, data=None):
		if data is not None:
			data = json.dumps(data)
			logging.debug(repr(data))
		uri = self.base + str(path)
		request = Request(method, uri, data, headers={'Content-Type': 'application/json'})
		response = urllib2.urlopen(request)
		#response = self.app.request(self.base + str(path), method=method, data=data, content_type='application/json')
		return json.load(response)

	def query(self, *a): return self.get('')
	def get(self, id): return self.request('GET', id)
	def post(self, doc):
		logging.debug("updating item %r" % (doc['title'],))
		id = doc['key']
		if id is None:
			return self.request('POST', '', doc)
		else:
			return self.request('POST', doc['key'], doc)
	def delete(self, doc): return self.request('DELETE', doc['key'], None)

class Request(urllib2.Request):
	def __init__(self, method, url, data=None, *a, **kw):
		self.__method = method
		urllib2.Request.__init__(self, url, data, *a, **kw)
		
	def get_method(self):
		return self.__method


class Texts(object):
	def __init__(self, smt):
		self.smt = smt
		self.refresh()
	
	def refresh(self):
		self.contents = self.smt.query()
	
	def at(self, index):
		return self.contents[index-1]

	def find(self, locator):
		regex = re.compile(locator, re.I)
		matches = []
		for text in self.contents:
			if re.search(regex, text['title']):
				matches.append(text)
		if len(matches) == 1:
			return matches[0]
		if len(matches) > 1:
			raise AmbiguousMatch(locator)
		else:
			raise NoMatchingItem(locator)

	def __getitem__(self, key):
		for text in self.contents:
			if text['key'] == key:
				return text
		raise KeyError(key)
	
	def get(self, title):
		for text in self.contents:
			if text['title'] == title:
				return text
		raise NoSuchItem(title)
	
	def __str__(self):
		return "\n".join("%s: %s" % (i, text['title'],) for i, text in enumerate(self.contents, start=1))

