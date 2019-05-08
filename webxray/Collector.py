# standard python libs
import os
import re
import sys
import random
import urllib.request
import multiprocessing
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

# custom webxray classes
from webxray.OutputStore	import OutputStore
from webxray.ChromeDriver 	import ChromeDriver

class Collector:
	"""
	This class does the main work of sorting out the page address to process

	the list of pages **must** be in the ./page_lists directory or it will not work

	when checking page addresses it skips over binary documents with known extensions
		and makes sure we aren't duplicating pages that have already been analyzed
		this means it is safe to re-run on the same list as it won't duplicate entries, but it
		*will* retry pages that may not have loaded
	"""

	def __init__(self, db_engine, db_name, pages_file_name, browser_types, browser_wait):
		self.db_engine			= db_engine
		self.startTime		 	= datetime.now()
		self.db_name		 	= db_name
		self.pages_file_name	= pages_file_name
		self.browser_types		= browser_types
		self.browser_wait		= browser_wait

		# set the correct ua string for chrome, only do once
		if 'chrome' in browser_types:
			chrome_driver = ChromeDriver()
			self.chrome_ua = chrome_driver.get_ua_for_headless()
	# __init__

	def print_runtime(self):
		print('\t-----------------------------------------')
		print('\t Collection Finished in %s!' % str(datetime.now()-self.startTime))
		print('\t-----------------------------------------')
	# print_runtime

	def process_url(self, url):
		"""
		this function takes a specified url, loads it in the browser
			and returns json-formatted output with relevant request data, etc.

		the output_store class then puts this data in the db for later analysis
		"""

		# set up sql connection used to log errors and do checks
		if self.db_engine == 'sqlite':	
			from webxray.SQLiteDriver import SQLiteDriver
			sql_driver = SQLiteDriver(self.db_name)

		# output store does the heavy lifting of analyzing browser output and storing to db
		output_store = OutputStore(self.db_engine, self.db_name)

		# support for loading same page with multiple browsers - purposefully undocumented 
		for browser_type in self.browser_types:

			# import and set up specified browser driver
			# 	note we need to set up a new browser each time to 
			#	get a fresh profile
			if browser_type == 'chrome':
				browser_driver 	= ChromeDriver(ua=self.chrome_ua)

			# attempt to load the page, fail gracefully
			try:
				browser_output = browser_driver.get_webxray_scan_data(url, self.browser_wait)
			except:
				print('\t\t%-50s Browser %s Did Not Return' % (url[:50], browser_type))
				sql_driver.log_error(url, 'Unable to load page')
				sql_driver.close()
				return
			
			# if there was a problem we log the error
			if browser_output['success'] == False:
				print('\t\t%-50s Browser %s Error: %s' % (url[:50], browser_type, browser_output['result']))
				sql_driver.log_error(url, 'Unable to load page')
				sql_driver.close()
				return
			else:
				# no error, treat result as browser output
				browser_output = browser_output['result']

			# attempt to store the output
			if output_store.store(url, browser_output):
				print('\t\t%-50s Success with %s' % (url[:50],browser_type))
			else:
				print('\t\t%-50s Fail with %s' % (url[:50],browser_type))
				sql_driver.log_error(url, 'Unable to load page')

		sql_driver.close()
		return
	# process_url

	def run(self, pool_size):
		"""
		this function manages the parallel processing of the url list using the python Pool class

		the function first reads the list of urls out of the page_lists directory, cleans it
			for known issues (eg common binary files), and issues with idna encoding (tricky!)

		then the page list is mapped to the process_url function  and executed in parallell

		pool_size is defined in the run_webxray.py file, see details there
		"""

		# the list of url MUST be in the page_lists directory!
		try:
			url_list = open(os.path.dirname(os.path.abspath(__file__)) + '/../page_lists/' + self.pages_file_name, 'r', encoding='utf-8')
		except:
			print('File "%s" does not exist, file must be in ./page_lists directory.  Exiting.' % self.pages_file_name)
			exit()

		# set up sql connection used to determine if items are already in the db
		if self.db_engine == 'sqlite':	
			from webxray.SQLiteDriver import SQLiteDriver
			sql_driver = SQLiteDriver(self.db_name)

		# this list gets mapped to the Pool, very important!
		urls_to_process = set()

		# simple counter used solely for updates to CLI
		count = 0
		
		print('\t------------------------')
		print('\t Building List of Pages ')
		print('\t------------------------')
				
		for url in url_list:
			# skip lines that are comments
			if "#" in url[0]: continue
		
			count += 1
		
			# only do lines starting with https?://
			if not (re.match('^https?://.+', url)):
				print("\t\t%s | %-50s Not a valid address, Skipping." % (count, url[:50]))
				continue

			# non-ascii domains may cause issues, so we need to convert them to 
			# 	idna/ascii/utf-8
			# this requires splitting apart the url, converting the domain to idna,
			#	and pasting it all back together
			
			split_url = urlsplit(url.strip())
			idna_fixed_netloc = split_url.netloc.encode('idna').decode('utf-8')
			url = urlunsplit((split_url.scheme,idna_fixed_netloc,split_url.path,split_url.query,split_url.fragment))

			# if it is a m$ office or other doc, skip
			if re.match('.+(pdf|ppt|pptx|doc|docx|txt|rtf|xls|xlsx)$', url):
				print("\t\t%s | %-50s Not an HTML document, Skipping." % (count, url[:50]))
				continue

			# skip if in db already
			if sql_driver.page_exists(url):
				print("\t\t%s | %-50s Exists in DB, Skipping." % (count, url[:50]))
				continue
	
			# only add if not in list already
			if url not in urls_to_process:
				print("\t\t%s | %-50s Adding." % (count, url[:50]))
				urls_to_process.add(url)
			else:
				print("\t\t%s | %-50s Already queued, Skipping." % (count, url[:50]))

		# close the db connection
		sql_driver.close()

		print('\t----------------------------------')
		print('\t%s addresses will now be webXray\'d'  % len(urls_to_process))
		print('\t\tBrowser(s) are %s' % self.browser_types)
		print('\t\tBrowser wait time is %s seconds' % self.browser_wait)
		print('\t\t...you can go take a walk. ;-)')
		print('\t----------------------------------')

		# for macOS (darwin) we must specify start method as 'forkserver'
		#	this is essentially voodoo to ward off evil spirits which 
		#	appear when large pool sizes are used on macOS
		# get_start_method must be set to 'allow_none', otherwise upon
		#	checking the method it gets set (!) - and if we then get/set again
		#	we get an error
		if sys.platform == 'darwin' and multiprocessing.get_start_method(allow_none=True) != 'forkserver':
			multiprocessing.set_start_method('forkserver')
		myPool = multiprocessing.Pool(pool_size)
		myPool.map(self.process_url, urls_to_process)

		# FYI
		self.print_runtime()
	# run
# class Collector
