# standard python libs
import os
import re
import bz2
import sys
import json
import time
import base64
import random
import hashlib
import multiprocessing
from datetime import datetime
from datetime import timedelta

# custom webxray classes
from webxray.ChromeDriver 		import ChromeDriver
from webxray.OutputStore		import OutputStore
from webxray.Utilities 			import Utilities

class Collector:
	"""
	This class does the main work of sorting out the page address to process

	the list of pages **must** be in the ./page_lists directory or it will not work

	when checking page addresses it skips over binary documents with known extensions
		and makes sure we aren't duplicating pages that have already been analyzed
		this means it is safe to re-run on the same list as it won't duplicate entries, but it
		*will* retry pages that may not have loaded
	"""

	def __init__(self, db_name=None, db_engine=None, client_id=None):
		"""
		This class can be called to run store_results_from_queue which connects
			to the server_config database to fetch results, in which case a global
			db_name isn't needed, so we have db_name=None to account for that.
			However, if we *do* have a db_name we set up a global config.
		"""
		self.db_name		 	= db_name
		self.db_engine			= db_engine
		self.client_id			= client_id
		self.debug				= True
		self.utilities			= Utilities()

		# get global config for this db
		if db_name:
			# set up database connection
			if self.db_engine == 'sqlite':
				from webxray.SQLiteDriver import SQLiteDriver
				sql_driver = SQLiteDriver(self.db_name)
			elif self.db_engine == 'postgres':
				from webxray.PostgreSQLDriver import PostgreSQLDriver
				sql_driver = PostgreSQLDriver(self.db_name)
			else:
				print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
				quit()

			self.config = sql_driver.get_config()
			self.browser_config = {}

			for item in self.config:
				if 'client' in item:
					self.browser_config[item] = self.config[item]

			sql_driver.close()
	# __init__

	def process_tasks_from_queue(self,process_num):
		"""
		Selects the next page from the task_queue and passes to 
			process_url.  If load is unsucessful places page
			back into queue and updates attempts.  Returns once 
			when there are no pages in the queue under max_attempts.
		"""

		print('\t[p.%s]\t🏃‍♂️ Starting process' % process_num)

		# need a local connection for each queue manager
		if self.db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			sql_driver = SQLiteDriver(self.db_name)
		elif self.db_engine == 'postgres':
			from webxray.PostgreSQLDriver import PostgreSQLDriver
			sql_driver = PostgreSQLDriver(self.db_name)
		else:
			print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
			quit()

		# keep getting tasks from queue until none are left at max attempt level
		while sql_driver.get_task_queue_length(max_attempts=self.config['max_attempts'], unlocked_only=True) != 0:
			# it is possible for two processes to both pass the above conditional
			#	and then try to get a task from the queue at the same time.
			#	however, the second process that attempts to get a task will
			#	get an empty result (and crash), so we have a try/except block here
			#	to handle that condition gracefully
			try:
				target, task = sql_driver.get_task_from_queue(max_attempts=self.config['max_attempts'],client_id=self.client_id)
			except:
				break

			print('\t[p.%s]\t👉 Initializing: %s for target %s' % (process_num,task,target[:50]))

			# import and set up specified browser driver
			# 	note we set up a new browser each time to 
			#	get a fresh profile
			if self.browser_config['client_browser_type'] == 'chrome':
				browser_driver 	= ChromeDriver(self.browser_config, port_offset=process_num)
			else:
				print(f"🥴 INVALID BROWSER TYPE for {self.browser_config['client_browser_type']}!")
				return

			# does the webxray scan or policy capture
			if task == 'get_scan':
				task_result = browser_driver.get_scan(target)
			elif task == 'get_crawl':
				task_result = browser_driver.get_crawl(json.loads(target))
			elif task == 'get_policy':
				task_result = browser_driver.get_scan(target, get_text_only=True)
			elif task == 'get_random_crawl':
				task_result = browser_driver.get_random_crawl(target)
			
			# kill browser
			del browser_driver

			# browser has failed to get result, unlock and continue
			if task_result['success'] == False:
				print('\t[p.%s]\t👎 Error: %s %s' % (process_num, target[:50],task_result['result']))

				# for times we don't want to retry, such as a rejected 
				#	redirect or network resolution failure, this could be expanded
				fail_cases = [
					'reached fail limit',
					'rejecting redirect',
					'did not find enough internal links'
				]
				
				if task_result['result'] in fail_cases or 'ERR_NAME_NOT_RESOLVED' in task_result['result']:
					sql_driver.set_task_as_failed(target, task)
				else:
					sql_driver.unlock_task_in_queue(target, task)

				# keep track of error regardless of fail/unlock
				sql_driver.log_error({
					'client_id'	: 'localhost', 
					'target'	: target,
					'task'		: task,
					'msg'		: task_result['result']
				})
				continue

			# debug
			if self.debug: print('\t[p.%s]\t📥 Got browser result on task %s, going to store: %s' % (process_num, task, target[:50]))

			# store_result also handles task queue mangement
			store_result = self.store_result({
					'target'		: target,
					'task'			: task,
					'task_result'	: task_result['result'],
					'client_id'		: self.client_id
				})

			if store_result['success'] == True:
				print(f'\t[p.{process_num}]\t👍 Success: {target[:50]}')
			else:
				print(f'\t[p.{process_num}]\t👎 Error: {target[:50]} {store_result["result"]}')

		# tidy up
		sql_driver.close()
		del sql_driver

		print('\t[p.%s]\t✋ Completed process' % process_num)
		return
	# process_tasks_from_queue

	def store_result(self, params):
		"""
		Handles storing task_result and removing jobs
			from the task_queue.
		"""

		# unpack params
		target 			= params['target']
		task 			= params['task']
		task_result 	= params['task_result']
		client_id 		= params['client_id']

		# client_ip is optional
		if 'client_ip' in params:
			client_ip = params['client_ip']
		else:
			client_ip = None

		# if db_name is specified we are running in server mode and we
		#	connect to the db which corresponds to the result being
		#	processed.  otherwise, we use the global db_name as we are
		#	running in non-server mode.
		if 'db_name' in params:
			if self.db_engine == 'sqlite':
				from webxray.SQLiteDriver import SQLiteDriver
				sql_driver = SQLiteDriver(params['db_name'])
			elif self.db_engine == 'postgres':
				from webxray.PostgreSQLDriver import PostgreSQLDriver
				sql_driver = PostgreSQLDriver(params['db_name'])
			else:
				print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
				quit()
			output_store 	= OutputStore(params['db_name'], self.db_engine)
		else:
			if self.db_engine == 'sqlite':
				from webxray.SQLiteDriver import SQLiteDriver
				sql_driver = SQLiteDriver(self.db_name)
			elif self.db_engine == 'postgres':
				from webxray.PostgreSQLDriver import PostgreSQLDriver
				sql_driver = PostgreSQLDriver(self.db_name)
			else:
				print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
				quit()

			output_store 	= OutputStore(self.db_name, self.db_engine)

		if task == 'get_policy':
			store_result = output_store.store_policy(task_result, client_id, client_ip=client_ip)
			# we never retry policies
			sql_driver.remove_task_from_queue(target,task)
			if store_result['success']:
				result = {'success': True}
			else:
				# log error
				sql_driver.log_error({
					'client_id'	: client_id,
					'task'		: task,
					'target'	: target,
					'msg'		: 'output_store fail on '+store_result['result']
				})
				result = {'success': False, 'result': store_result['result']}
		# elif task == 'get_crawl' or task == 'get_random_crawl':
		else:
			all_crawls_ok = True

			# We want to be able to re-run random crawls, and to do so we make sure
			#	the crawl_id will match
			if task == 'get_crawl' or task == 'get_scan':
				crawl_id = target
			elif task == 'get_random_crawl':
				crawl_id = []
				for result in task_result:
					crawl_id.append(result['start_url'])
				crawl_id = json.dumps(crawl_id)

			# tweak to account for differences between scans/crawls
			if task =='get_scan': task_result = [task_result]
			
			# keep track of domains
			all_3p_cookie_domains 		= set()
			all_3p_dom_storage_domains 	= set()
			all_3p_request_domains 		= set()
			all_3p_response_domains 	= set()
			all_3p_websocket_domains 	= set()

			# When we store a crawl we add optional fields in the page table
			#	that allow us to connect the page loads into a single crawl.
			#	the crawl_id is a hash of the target (which is a json string
			#	derived from the url_list), and the crawl_timestamp which is the
			#	first accessed time from the crawl.
			for crawl_sequence,result in enumerate(task_result):
				store_result = output_store.store_scan({
					'browser_output'	: result,
					'client_id'			: client_id,
					'crawl_id'			: crawl_id,
					'crawl_timestamp'	: task_result[0]['accessed'],
					'crawl_sequence'	: crawl_sequence,
					'client_ip'			: client_ip
				})

				if store_result['success'] != True:
					all_crawls_ok = False
				else:
					# we are successful, create entries in page_lookup table
					page_lookup_table = self.build_lookup_table('page', store_result['page_id'], {
						'requests'		: store_result['page_3p_request_domains'],
						'responses'		: store_result['page_3p_response_domains'],
						'websockets'	: store_result['page_3p_websocket_domains'],
						'dom_storage'	: store_result['page_3p_dom_storage_domains'],
						'cookies'		: store_result['page_3p_dom_storage_domains']
					})

					for lookup_item in page_lookup_table:
						sql_driver.add_page_id_domain_lookup_item(page_lookup_table[lookup_item])

					# we are also making a lookup table for the crawl, keep joing the
					#	sets as we go along
					all_3p_request_domains.update(store_result['page_3p_request_domains'])
					all_3p_response_domains.update(store_result['page_3p_response_domains'])
					all_3p_websocket_domains.update(store_result['page_3p_websocket_domains'])
					all_3p_dom_storage_domains.update(store_result['page_3p_dom_storage_domains'])
					all_3p_cookie_domains.update(store_result['page_3p_dom_storage_domains'])

			if all_crawls_ok:
				sql_driver.remove_task_from_queue(target,task)
				result = {'success': True}

				# build crawl lookup table
				crawl_lookup_table = self.build_lookup_table('crawl', crawl_id, {
					'requests'		: all_3p_request_domains,
					'responses'		: all_3p_response_domains,
					'websockets'	: all_3p_websocket_domains,
					'dom_storage'	: all_3p_dom_storage_domains,
					'cookies'		: all_3p_cookie_domains
				})

				# patch lookup table
				for lookup_item in crawl_lookup_table:
					sql_driver.add_crawl_id_domain_lookup_item(crawl_lookup_table[lookup_item])

			else:
				sql_driver.unlock_task_in_queue(target, task)
				# log error
				sql_driver.log_error({
					'client_id'	: client_id,
					'task'		: task,
					'target'	: target,
					'msg'		: 'output_store fail to store all scans for crawl_id_target '+target
				})
				result = {'success': False, 'result': 'unable to store all crawl loads'}

		# tidy up
		output_store.close()
		sql_driver.close()
		
		# done
		return result
	# store_result

	def build_lookup_table(self, type, id, domains):
		"""
		Take all the domains by type and build a lookup table we
			can insert to db.  type is for either page or crawl.
		"""
		domain_lookup_table = {}

		# if given domain/type is not in lookup table we create new
		#	entry, otherwise update extant entry
		for domain, domain_owner_id in domains['requests']:
			if domain not in domain_lookup_table:
				domain_lookup_table[domain] = {f'{type}_id': id, 'domain': domain, 'domain_owner_id': domain_owner_id, 'is_request': True,'is_response':False,'is_cookie':False,'is_websocket':False,'is_domstorage':False}
		
		for domain, domain_owner_id in domains['responses']:
			if domain not in domain_lookup_table:
				domain_lookup_table[domain] = {f'{type}_id': id, 'domain': domain, 'domain_owner_id': domain_owner_id, 'is_request': False,'is_response':True,'is_cookie':False,'is_websocket':False,'is_domstorage':False}
			else:
				domain_lookup_table[domain]['is_response'] = True

		for domain, domain_owner_id in domains['websockets']:
			if domain not in domain_lookup_table:
				domain_lookup_table[domain] = {f'{type}_id': id, 'domain': domain, 'domain_owner_id': domain_owner_id, 'is_request': False,'is_response':False,'is_cookie':False,'is_websocket':True,'is_domstorage':False}
			else:
				domain_lookup_table[domain]['is_websocket'] = True

		for domain, domain_owner_id in domains['dom_storage']:
			if domain not in domain_lookup_table:
				domain_lookup_table[domain] = {f'{type}_id': id, 'domain': domain, 'domain_owner_id': domain_owner_id, 'is_request': False,'is_response':False,'is_cookie':False,'is_websocket':False,'is_domstorage':True}
			else:
				domain_lookup_table[domain]['is_domstorage'] = True

		for domain, domain_owner_id in domains['cookies']:
			if domain not in domain_lookup_table:
				domain_lookup_table[domain] = {f'{type}_id': id, 'domain': domain, 'domain_owner_id': domain_owner_id, 'is_request': False,'is_response':False,'is_cookie':True,'is_websocket':False,'is_domstorage':False}
			else:
				domain_lookup_table[domain]['is_cookie'] = True

		return domain_lookup_table
	# build_lookup_table

	def build_crawl_task_queue(self, params):
		"""
		Enter crawl tasks to the database after performing checks to 
			verify urls are valid.
		"""

		# these vars are specific to this function
		crawl_file_name 		= params['crawl_file_name']
		flush_crawl_task_queue	= params['flush_crawl_task_queue']

		# only need this sql_driver to build the task list
		sql_driver = PostgreSQLDriver(self.db_name)

		# open list of pages
		try:
			crawl_list = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/../crawl_lists/' + crawl_file_name, 'r', encoding='utf-8'))
		except:
			print(f'Could not open {crawl_file_name}, is it correctly formatted and present in the ./crawl_lists directory?  Exiting.')
			sql_driver.close()
			exit()

		# get rid of whatever is in there already
		if flush_crawl_task_queue: 
			sql_driver.flush_task_queue(task='get_crawl')

		for count,url_list in enumerate(crawl_list):
			# first make sure the urls are valid, if we 
			#	encounterd a non-valid url we trash the
			#	entire list
			url_list_valid = True

			# we keep our fixed urls here
			idna_url_list = []

			# look at each url
			for url in url_list:
				if self.utilities.is_url_valid(url) == False:
					print(f'{url} is not valid from {url_list}, not entering crawl to queue')
					url_list_valid = False
					break

				# perform idna fix
				idna_url_list.append(self.utilities.idna_encode_url(url))

			# we need to put the continue here for the outer loop
			if url_list_valid == False: continue

			# if we are allowing time series we see if page has been scanned in the
			#	specified interval, otherwise if we are *not* allowing a time series
			#	we skip anything already in the db
			if self.config['timeseries_enabled']:
				if sql_driver.crawl_exists(json.dumps(idna_url_list),timeseries_interval=self.config['timeseries_interval']):
					print(f'\t{count} | {url[:30]}... Scanned too recently.')
					continue
			else:
				if sql_driver.crawl_exists(json.dumps(idna_url_list)):
					print(f'\t{count} | {url[:30]}... Exists in DB, skipping.')
					continue

			# we have a valid list, queue it up!
			if url_list_valid: sql_driver.add_task_to_queue(json.dumps(idna_url_list),'get_crawl')
			print(f'\t{count} | {str(idna_url_list)[:30]}... Adding to queue.')
			
		# done
		sql_driver.close()
	# build_crawl_task_queue

	def build_scan_task_queue(self, params):
		"""
		Takes a given list of pages and puts them into a queue
			to be scanned either by the same machine building 
			the queue, or remote machines.
		"""

		# these vars are specific to this function
		pages_file_name 		= params['pages_file_name']
		flush_scan_task_queue	= params['flush_scan_task_queue']
		task 					= params['task']

		# set up sql connection used to determine if items are already in the db	
		if self.db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			sql_driver = SQLiteDriver(self.db_name)
		elif self.db_engine == 'postgres':
			from webxray.PostgreSQLDriver import PostgreSQLDriver
			sql_driver = PostgreSQLDriver(self.db_name)
		else:
			print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
			quit()

		# open list of pages
		try:
			url_list = open(os.path.dirname(os.path.abspath(__file__)) + '/../page_lists/' + pages_file_name, 'r', encoding='utf-8')
		except:
			print('File "%s" does not exist, file must be in ./page_lists directory.  Exiting.' % pages_file_name)
			sql_driver.close()
			exit()

		# get list of pages already scanned
		already_scanned = []
		print('\tFetching list of pages already scanned...')
		if self.config['timeseries_enabled']:
			for url, in sql_driver.get_all_pages_exist(timeseries_interval=self.config['timeseries_interval']):
				already_scanned.append(url)
		else:
			for url, in sql_driver.get_all_pages_exist():
				already_scanned.append(url)
		print(f'\t => {len(already_scanned)} pages already scanned')

		# get rid of whatever is in there already
		if flush_scan_task_queue: 
			sql_driver.flush_task_queue(task=task)

		# simple counter used solely for updates to CLI
		count = 0
		
		print('\t---------------------')
		print('\t Building Page Queue ')
		print('\t---------------------')

		for url in url_list:
			# skip lines that are comments
			if "#" in url[0]: continue
		
			count += 1
		
			# make sure url is valid
			if self.utilities.is_url_valid(url) == False: 
				print(f'\t\t{count} | {url} is invalid')
				continue

			# perform idna fix
			url = self.utilities.idna_encode_url(url)

			# if we are allowing time series we see if page has been scanned in the
			#	specified interval, otherwise if we are *not* allowing a time series
			#	we skip anything already in the db
			if url in already_scanned and self.config['timeseries_enabled']:
				print(f'\t\t{count} | {url[:30]}... Scanned too recently.')
				continue

			elif url in already_scanned:
				print(f'\t\t{count} | {url[:30]}... Exists in DB, skipping.')
				continue

			# add to the queue, duplicates will be
			#	ignored
			sql_driver.add_task_to_queue(url, task)
			print(f'\t\t{count} | {url[:30]}... Adding to queue.')
		
		# close the db connection
		sql_driver.close()
	# build_scan_task_queue

	def build_policy_task_queue(self, flush_policy_task_queue=True, timeseries_interval=10080):
		"""
		Takes a given list of pages and puts them into a queue
			to be scanned either by the same machine building 
			the queue, or remote machines.
		"""

		# set up new db connection
		if self.db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			sql_driver = SQLiteDriver(self.db_name)
		elif self.db_engine == 'postgres':
			from webxray.PostgreSQLDriver import PostgreSQLDriver
			sql_driver = PostgreSQLDriver(self.db_name)
		else:
			print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
			quit()

		# get rid of whatever is in there already
		if flush_policy_task_queue: 
			sql_driver.flush_task_queue(task='get_policy')

		# get list of all policies we have
		scanned_policies = []
		for policy_url, in sql_driver.get_scanned_policy_urls():
			scanned_policies.append(policy_url)

		# run the query and add to list
		for policy_url, in sql_driver.get_policies_to_collect():
			# if page has an anchor, we drop everything after
			if policy_url[-1] == '#':
				policy_url = policy_url[:-1]
			elif '#' in policy_url:
				policy_url = re.search('^(.+?)#.+$', policy_url).group(1)

			# skip invalid links
			if not self.utilities.is_url_valid(policy_url): continue

			# already did it, skip
			if policy_url in scanned_policies: continue
			
			sql_driver.add_task_to_queue(policy_url,'get_policy')

		# fyi
		print('\t%s pages in task_queue for get_policy' % sql_driver.get_task_queue_length(task='get_policy'))

		# we no longer need this db connection
		sql_driver.close()
	# build_policy_task_queue

	def store_results_from_queue(self, process_num):
		"""
		If we are using a result queue this function will process
			all pending results.
		"""

		# set up new db connection to the server
		from webxray.PostgreSQLDriver import PostgreSQLDriver
		server_sql_driver = PostgreSQLDriver('server_config')

		# time to sleep when queue is empty
		wait_time = 5

		# loop continues indefintely
		while True:
			result = server_sql_driver.get_result_from_queue()
			if not result:
				print(f'\t[p.{process_num}]\t😴 Going to sleep for {wait_time} seconds to wait for more tasks.')
				time.sleep(wait_time)
				continue

			# result is a dictionary object, unpack it
			result_id		= result['result_id']
			client_id		= result['client_id']
			client_ip		= result['client_ip']
			mapped_db		= result['mapped_db']
			target			= result['target']
			task			= result['task']

			# the task_result needs to be uncompressed
			task_result = json.loads(bz2.decompress(base64.urlsafe_b64decode(result['task_result'])).decode('utf-8'))

			if self.debug: print(f'\t[p.{process_num}]\t📥 Going to store result for {str(target)[:30]}')

			# store_result also handles task queue mangement
			store_result = self.store_result({
					'target'		: target,
					'task'			: task,
					'task_result'	: task_result,
					'client_id'		: client_id,
					'client_ip'		: client_ip,
					'db_name'		: mapped_db
				})

			# we finished processing this result, remove it from result queue
			server_sql_driver.remove_result_from_queue(result_id)
	
			# FYI
			if store_result['success'] == True:
				print('\t[p.%s]\t👍 Success: %s' % (process_num, target[:50]))
			else:
				print('\t[p.%s]\t👎 Error: %s %s' % (process_num, target[:50], store_result['result']))

		# techincally we never get here...
		server_sql_driver.close()
		return
	# store_results_from_queue

	def run(self, task='process_tasks_from_queue', pool_size=None):
		"""
		this function manages the parallel processing of the url list using the python Pool class

		the function first reads the list of urls out of the page_lists directory, cleans it
			for known issues (eg common binary files), and issues with idna encoding (tricky!)

		then the page list is mapped to the process_url function  and executed in parallell

		pool_size is defined in the run_webxray.py file, see details there

		when running in slave mode the list is skipping and we got straight to scanning
		"""

		if task == 'process_tasks_from_queue':
			# set up sql connection to get queue_length	
			if self.db_engine == 'sqlite':
				from webxray.SQLiteDriver import SQLiteDriver
				sql_driver = SQLiteDriver(self.db_name)
			elif self.db_engine == 'postgres':
				from webxray.PostgreSQLDriver import PostgreSQLDriver
				sql_driver = PostgreSQLDriver(self.db_name)
			else:
				print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
				quit()

			queue_length = sql_driver.get_task_queue_length()
			sql_driver.close()
			del sql_driver

			print('\t----------------------------------')
			print('\t%s addresses will now be webXray\'d'  % queue_length)
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
		
		# map requires we pass an argument to the function
		#	(even though we don't need to), so we create
		#	a list equal to pool_size which will
		#	spawn the desired number of processes
		process_num = []
		if pool_size == None:
			pool_size = multiprocessing.cpu_count()

		for i in range(0,pool_size):
			process_num.append(i)

		if task == 'process_tasks_from_queue':
			myPool.map(self.process_tasks_from_queue, process_num)
		elif task == 'store_results_from_queue':
			myPool.map(self.store_results_from_queue, process_num)
	# run
# Collector
