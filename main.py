#!/usr/bin/env python

import logging
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import users

from controllers import *
from controllers import api

application = webapp.WSGIApplication([
		('/', MainHandler),
		#('/logout/', LogoutHandler),
		('/api/text/?', api.TextSetHandler),
		#('/api/text/delete/(.*)', api.TextDeleteHandler),
		('/api/text/(.*)', api.SpecificTextHandler),
		], debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()

