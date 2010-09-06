import os

__all__ = [
		'BASE',
		'API',
		'AppError',
		'UsageError',
		'AmbiguousMatch',
		'NoMatchingItem',
		'NoSuchItem',
]

BASE = os.environ.get('SAVEMYTEXT_BASE', 'http://savemytext.appspot.com/')
API = "api/text/"

class AppError(StandardError): pass
class UsageError(AppError): pass
class AmbiguousMatch(AppError):
	def message(self):
		return "Ambiguous title pattern: %r" % (self.args[0],)

class NoMatchingItem(AppError):
	def message(self):
		return "No items matched pattern: %r" % (self.args[0],)

class NoSuchItem(AppError):
	def message(self):
		return "No such item: %r" % (self.args[0],)


