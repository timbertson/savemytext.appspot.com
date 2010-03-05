import urllib2

from base import *

from models import Text

class MainHandler(BaseHandler):
	def all_instances(self):
		return Page.find_all(self.user())
	
	def get(self):
		user = self.user()
		
		template_values = {
			'name': user.nickname(),
			'texts': Text.find_all(user) or [Text.add(user)],
		}
		#raise RuntimeError(template_values['texts'])
		info("template values: %r" % template_values)
		
		self.response.out.write(render_page('index', template_values))

