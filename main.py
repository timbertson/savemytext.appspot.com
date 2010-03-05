#!/usr/bin/env python

import logging
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import users

from controllers import *

application = webapp.WSGIApplication([
		('/', MainHandler),
		('/text/', TextHandler),
		#('/logout/', LogoutHandler),
		('/text/del/', TextDeleteHandler),
		], debug=True)

def main():
	logging.getLogger().setLevel(logging.DEBUG)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()

