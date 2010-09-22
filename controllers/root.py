import urllib2

from base import *

from models import Text
import datetime

class MainHandler(BaseHandler):
	def all_instances(self):
		return Page.find_all(self.user())
	
	def get(self):
		user = self.user()
		
		template_values = {
			'name': user.nickname(),
			'title': '{{texts.unreadMarker()}}'
		}
		expires_date = datetime.datetime.utcnow()
		expires_str = expires_date.strftime("%d %b %Y %H:%M:%S GMT")
		self.response.headers.add_header("Expires", expires_str)
		self.response.headers.add_header("Cache-Control", "no-store")
		self.response.headers.add_header("Pragma", 'no-cache')

		file = open(view('content', 'index.html'))
		content = file.read()
		file.close()

		self.response.out.write(render_page('index', template_values, content=content))

