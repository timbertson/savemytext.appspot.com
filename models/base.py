from google.appengine.ext import db
class BaseModel(db.Model):
	version = db.IntegerProperty(default=0)

	def to_dict(self):
		IGNORE = ['owner', 'version']
		output = {'key':str(self.key())}
		for key, prop in self.properties().iteritems():
			if key in IGNORE:
				continue
			value = getattr(self, key)
			output[key] = value
		return output



