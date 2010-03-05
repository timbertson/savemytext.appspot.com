class HttpError(Exception):
	def __init__(self, code, content=''):
		self.code = code
		self.content = content

class RedirectError(Exception):
	def __init__(self, target):
		self.target = target

