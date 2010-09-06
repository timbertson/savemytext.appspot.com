import time
import inspect
import subprocess
import tempfile
import optparse
import threading
import logging
import os
import sys
import readline

from savemytext import init_api, Texts
from common import *

class Editor(object):
	def __init__(self, smt_func):
		self._texts = self._smt = None
		self._smt_func = smt_func
	
	# lazily set texts and smt so that passwords and network fetches aren't invoked unnecessarily
	def get_texts(self):
		if self._texts is None:
			self._texts = Texts(self.smt)
		return self._texts
	texts = property(get_texts)

	def get_smt(self):
		if self._smt is None:
			self._smt = self._smt_func()
		return self._smt
	smt = property(get_smt)
	

	@classmethod
	def main(cls):
		parser = optparse.OptionParser(usage="usage: %prog username ACTION [document-locator [action-specific-args]]")

		cls.commands = [
			Command('edit',   help='edit (with $EDITOR, or opener)'),
			Command('list',   help='list current texts'),
			Command('info',   help='get text info (key)', short='n'),
			Command('delete', help='delete (locator)'),
			Command('add',    help='add a new item (title, file)'),
			Command('set',    help='set new content for an item (locator, file)'),
			Command('get',    help='print out the contents of a text'),
			Command('rename', help='rename item (locator, new_title)'),
			Command('quit',   help=None),
		]

		cls.command_map = {}
		for command in cls.commands:
			if command.help is not None:
				command.add(parser)
			cls.command_map[command.short] = command.name

		cls.command_summary = ", ".join([command.description() for command in cls.commands][:-1]) + " or " + cls.commands[-1].description()

		parser.add_option('-i', '--interactive', action='store_const', const='interactive', dest='action', help='savemytext console')

		parser.add_option('-o', '--opener', help='set opener command (defaults to $EDITOR)', default=None)
		parser.add_option('-L', '--literal', dest='literal_content', action='store_true', help='use literal text content instead of file names', default=False)
		parser.add_option('--regex', help='find by case-indensitive regex (the default)', dest='locator', default='regex')
		parser.add_option('-x', '--exact', action='store_const', const='exact', help='find by exact title match (default regex)', dest='locator')
		parser.add_option('-k', '--key',   action='store_const', const='key',   help='find by DB key', dest='locator')
		parser.add_option('-I', '--index', action='store_const', const='index', help='find by index', dest='locator')

		parser.add_option('-v', '--verbose', action='store_true', default=False, help='verbose output')
		opts, args = parser.parse_args()

		try:
			if len(args) < 1:
				raise UsageError()

			user = args.pop(0)

			# general configuration - find method and editor
			cls.find = getattr(cls, 'find_by_' + opts.locator)
			cls.editor_args = (opts.opener or os.environ.get('EDITOR', 'gnome-text-editor')).split()
			cls.literal_content = opts.literal_content

			if opts.verbose:
				logging.root.setLevel(logging.DEBUG)

			action = opts.action or 'interactive'
			cls.interactively = action in ('interactive', 'edit', 'get')
			smt_func = lambda: init_api(user)
			instance = cls(smt_func)
			action_method = getattr(instance, action)
			instance.execute(action_method, args)
		except UsageError:
			parser.print_usage()
			sys.exit(1)
	
	def find_by_regex(self, regex):  return self.texts.find(regex)
	def find_by_exact(self, title):  return self.texts.get(title)
	def find_by_index(self, index):  return self.texts.at(int(index))

	def edit(self, doc):
		tmpfile = tempfile.NamedTemporaryFile(prefix='savemytext', delete=False)
		try:
			tmpfile.write(doc['content'])
			tmpfile.close()
			proc = subprocess.Popen(self.editor_args + [tmpfile.name])
			self.watch_for_updates(tmpfile.name, doc)
		finally:
			tmpfile.unlink(tmpfile.name)
	
	def watch_for_updates(self, filename, doc):
		stop = threading.Event()
		changed = threading.Event()

		watcher = threading.Thread(name='watcher', target=lambda: self.watch_file_for_edits(event=changed, filename=filename, stop=stop))
		uploader = threading.Thread(name='uploader', target=lambda: self.keep_uploading(event=changed, filename=filename, doc=doc, stop=stop))
		threads = (watcher, uploader)

		for thread in threads:
			thread.daemon = True
			thread.start()

		raw_input("Please press enter when you are finished editing the text.")
		stop.set()
		for thread in threads:
			thread.join()
		logging.debug("saving complete!")

	def watch_file_for_edits(self, event, filename, stop):
		lastmod = os.stat(filename).st_mtime
		while True:
			if stop.is_set():
				break
			time.sleep(3)
			new_lastmod = os.stat(filename).st_mtime
			if new_lastmod != lastmod:
				logging.debug("file changed!")
				event.set()
				lastmod = new_lastmod
		event.set()

	def keep_uploading(self, event, filename, doc, stop):
		while True:
			if stop.is_set():
				logging.info("editing finished")
				break
			event.clear()
			event.wait()
			logging.debug("upload event signalled - checking content")
			content = doc['content']
			with open(filename) as f:
				new_content = f.read()
			if new_content != content:
				logging.debug("new content is: %s" % (new_content,))
				doc['content'] = new_content
				self.smt.post(doc)

	def delete(self, doc):
		self.smt.delete(doc)

	def set(self, doc, content):
		doc['content'] = content
		self.smt.post(doc)
	
	def rename(self, doc, new_name):
		doc['title'] = new_name
		self.smt.post(doc)

	def get(self, doc):
		print doc['content']
	
	def info(self, doc):
		print """%(key)s (%(title)s)""" % doc
	
	def add(self, title, content):
		self.smt.post({
			'content': content,
			'title': title,
			'key': None,
		})

	def list(self):
		self.do_list()
	
	def do_list(self, refresh=True):
		if refresh:
			self.texts.refresh()
		print "-" * 40
		print self.texts

	
	def interactive(self):
		self.do_list(refresh=False)
		print
		while True:
			try:
				cmd_pair = self.ask("Command (%s): " % (self.command_summary,), (self.command_map.keys() + self.command_map.values())).split(' ', 1)
				cmd = cmd_pair[0]
				args = cmd_pair[1:]
				if len(cmd) == 1:
					cmd = self.command_map[cmd]
				method = getattr(self, cmd)
				self.execute(method, args)
			except (EOFError, KeyboardInterrupt):
				break
			except AppError, e:
				logging.error(e.message())
			except StandardError, e:
				logging.debug('Error performing command', exc_info=True)
				logging.error(e)
				continue
			finally:
				print >> sys.stderr
	
	def quit(self):
		sys.exit(0)

	# -- helper functions
	def ask(self, prompt, valid_responses=None):
		if not self.interactively:
			raise UsageError()
		while True:
			response = raw_input(prompt)
			if valid_responses is None or (response and response.split()[0]) in valid_responses:
				return response

	def execute(self, method, available_args):
		logging.debug("args in = %r" % (available_args,))
		def get_arg(name):
			while True:
				if len(available_args) > 0:
					return available_args.pop(0)
				else:
					try:
						return self.ask('\nplease enter %s: ' % (name,))
					except (NoMatchingItem, AmbiguousMatch, NoSuchItem):
						continue

		def read_from_file(filepath):
			logging.debug("reading content from file")
			if filepath == '-':
				logging.info("reading input from STDIN")
				return sys.stdin.read()
			with open(filepath, 'r') as f:
				return f.read()
	
		result_args = []
		expected_args = inspect.getargspec(method).args[1:]

		for expected_arg in expected_args:
			arg = None
			if expected_arg == 'doc':
				logging.debug("getting locator for doc")
				if len(available_args) == 0:
					self.list()
				doc = self.find(get_arg('title'))
				arg = doc
			elif expected_arg == 'content' and not self.literal_content:
				arg = read_from_file(get_arg('content (file)'))
			else:
				# normal arg, just prompt for it:
				arg = get_arg(expected_arg)
			result_args.append(arg)

		logging.debug("args out = %r" % (result_args,))

		if len(available_args) > 0:
			raise AppError("too many arguments provided!")
		logging.debug("method = %r, args = %r" % (method, result_args))
		method(*result_args)


class Command(object):
	def __init__(self, name, help, short=None):
		if short is None:
			short = name[0]
		self.help = help
		self.name = name
		self.short = short

	def add(self, parser):
		parser.add_option('-' + self.short, '--' + self.name, action='store_const', const=self.name, dest='action', default=None, help=self.help)

	def description(self):
		return self.name.replace(self.short, "[%s]" % (self.short,), 1)

