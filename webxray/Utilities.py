import os
import re
import csv
import json
import time
import decimal
import statistics
import collections
from datetime import datetime
from urllib.parse import urlparse
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from webxray.ParseURL import ParseURL

class Utilities:
	def __init__(self,db_name=None,db_engine=None):
		# if we have db params set up global db connection, otherwise we don't bother
		if db_name:
			if db_engine == 'sqlite':
				from webxray.SQLiteDriver import SQLiteDriver
				self.sql_driver = SQLiteDriver(db_name)
			elif db_engine == 'postgres':
				from webxray.PostgreSQLDriver import PostgreSQLDriver
				self.sql_driver = PostgreSQLDriver(db_name)
			else:
				print('Utilities.py: INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
				quit()
		elif db_engine:
			if db_engine == 'sqlite':
				from webxray.SQLiteDriver import SQLiteDriver
				self.sql_driver = SQLiteDriver()
			elif db_engine == 'postgres':
				from webxray.PostgreSQLDriver import PostgreSQLDriver
				self.sql_driver = PostgreSQLDriver()
			else:
				print('Utilities.py: INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
				quit()

		self.url_parser = ParseURL()
	# __init__

	def check_dependencies(self):

		import sys
		if sys.version_info[0] < 3 or sys.version_info[1] < 4:
			print('******************************************************************************')
			print(' Python 3.4 or above is required for webXray; please check your installation. ')
			print('******************************************************************************')
			quit()

		try:
			from websocket import create_connection
		except:
			print('*******************************************************')
			print(' The websocket-client library is needed for webXray.   ')
			print(' Please try running "pip3 install -r requirements.txt" ')
			print('*******************************************************')
			quit()

		try:
			from textstat.textstat import textstat
		except:
			print('*******************************************************')
			print(' The textstat library is needed for webXray.           ')
			print(' Please try running "pip3 install -r requirements.txt" ')
			print('*******************************************************')
			quit()

		try:
			import lxml.html
		except:
			print('*******************************************************')
			print(' The lxml library is needed for webXray.               ')
			print(' Please try running "pip3 install -r requirements.txt" ')
			print('*******************************************************')
			quit()

	# check_dependencies

	def get_default_config(self, config_type):
		# the following are two pre-configured options for
		#	haystack and forensic scans, can be tweaked as desired
		if config_type == 'haystack':
			return {
				'client_browser_type'			: 'chrome',
				'client_prewait'				: 10,
				'client_no_event_wait'			: 20,
				'client_max_wait'				: 60,
				'client_get_bodies'				: False,
				'client_get_bodies_b64'			: False,
				'client_get_screen_shot'		: False,
				'client_get_text'				: False,
				'client_crawl_depth'			: 3,
				'client_crawl_retries'			: 5,
				'client_page_load_strategy'		: 'none',
				'client_reject_redirects'		: False,
				'client_min_internal_links'		: 5,
				'max_attempts'					: 5,
				'store_1p'						: True,
				'store_base64'					: False,
				'store_files'					: True,
				'store_screen_shot'				: False,
				'store_source'					: False,
				'store_page_text'				: False,
				'store_links'					: True,
				'store_dom_storage'				: True,
				'store_responses'				: True,
				'store_request_xtra_headers'	: True,
				'store_response_xtra_headers'	: True,
				'store_requests'				: True,
				'store_websockets'				: True,
				'store_websocket_events'		: True,
				'store_event_source_msgs'		: True,
				'store_cookies'					: True,
				'store_security_details'		: True,
				'timeseries_enabled'			: True,
				'timeseries_interval'			: 0
			}
		elif config_type == 'forensic':
			return {
				'client_browser_type'			: 'chrome',
				'client_prewait'				: 10,
				'client_no_event_wait'			: 20,
				'client_max_wait'				: 60,
				'client_get_bodies'				: True,
				'client_get_bodies_b64'			: True,
				'client_get_screen_shot'		: True,
				'client_get_text'				: True,
				'client_crawl_depth'			: 3,
				'client_crawl_retries'			: 5,
				'client_page_load_strategy'		: 'none',
				'client_reject_redirects'		: True,
				'client_min_internal_links'		: 5,
				'max_attempts'					: 5,
				'store_1p'						: True,
				'store_base64'					: True,
				'store_files'					: True,
				'store_screen_shot'				: True,
				'store_source'					: True,
				'store_page_text'				: True,
				'store_links'					: True,
				'store_dom_storage'				: True,
				'store_responses'				: True,
				'store_request_xtra_headers'	: True,
				'store_response_xtra_headers'	: True,
				'store_requests'				: True,
				'store_websockets'				: True,
				'store_websocket_events'		: True,
				'store_event_source_msgs'		: True,
				'store_cookies'					: True,
				'store_security_details'		: True,
				'timeseries_enabled'			: True,
				'timeseries_interval'			: 0
			}
		elif config_type == 'custom':
			print('Create a custom config in Utilities.py')
			quit()
		else:
			print('Invalid config option, see Utilities.py')
			quit()
	# get_default_config

	def select_wbxr_db(self):
		"""
		databases are stored with a prefix (default 'wbxr_'), this function helps select a database in interactive mode
		"""

		# you can optionally specify a different prefix here by setting "db_prefix = '[PREFIX]'"
		wbxr_dbs = self.sql_driver.get_wbxr_dbs_list()
		wbxr_dbs.sort()

		if len(wbxr_dbs) == 0:
			print('''\t\tThere are no databases to analyze, please try [C]ollecting data or 
					import an existing wbxr-formatted database manually.''')
			interaction()
			return

		for index,db_name in enumerate(wbxr_dbs):
			print('\t\t[%s] %s' % (index, db_name))

		max_index = len(wbxr_dbs)-1
		
		# interaction step: loop until we get acceptable input
		while True:
			selected_db_index = input("\n\tPlease select database by number: ")
			if selected_db_index.isdigit():
				selected_db_index = int(selected_db_index)
				if selected_db_index >= 0 and selected_db_index <= max_index:
					break
				else:
					print('\t\t You entered an invalid string, please select a number in the range 0-%s.' % max_index)
					continue
			else:
				print('\t\t You entered an invalid string, please select a number in the range 0-%s.' % max_index)
				continue

		db_name = wbxr_dbs[selected_db_index]
		return db_name
	# select_wbxr_db

	def stream_rate(self, type='scan', return_json=False, client_id=None):
		"""
		This function is a generator which determines the rate
			at which pages are being add to the db
			allowing us to evaluate our rate of progress.
		"""

		# initialize dictionary to store rate data
		client_rate_data = {}

		# this diction will hold all the rates for each client so we can 
		#	easily figure out the average rate
		all_rates = {}

		# None store the aggregate data for all clients
		client_rate_data[None] = {}
		all_rates[None] = []

		# add entries for each client
		for client_id, in self.sql_driver.get_client_list():
			client_rate_data[client_id] = {}
			all_rates[client_id] = []

		# for client_id in ['wbxr0','wbxr1','wbxr2','wbxr3','wbxr4','wbxr5']:
		# 	client_rate_data[client_id] = {}
		# 	all_rates[client_id] = []		

		crawl_depth = self.sql_driver.get_config()['client_crawl_depth']

		# set time window we want to look at to see how many
		#	pages have been recently added
		
		# set the time gap between updates, leaving it too short
		#	means lots of db calls
		if type == 'scan' or type =='policy':
			wait_seconds = 10
			interval_seconds = 600
		elif type == 'task':
			wait_seconds = 30
			interval_seconds = 30

		# keep track of how long we've been doing this
		elapsed_seconds = 0

		# for tasks
		if type == 'task': old_task_count = self.sql_driver.get_pending_task_count()

		# this runs forever, no terminating condition
		while True:
			# simple increment, note we we /60 before we return 
			#	for minutes conversion
			elapsed_seconds += wait_seconds

			remaining_tasks = self.sql_driver.get_task_queue_length()

			total_count = 0

			for client_id, count in self.sql_driver.get_recent_page_count_by_client_id(interval_seconds):
				total_count += count

				# to get rate/hour we take the number of pages we've added per 
				#	second *3600
				current_rate = (count/interval_seconds)*3600
				
				# this list is all the rates we've seen
				all_rates[client_id] = all_rates[client_id] + [current_rate]

				# nice built-in to get the average rate
				average_rate = statistics.mean(all_rates[client_id])

				# figure out how much longer to go, gracefully handle
				#	a rate of zero
				if average_rate != 0:
					remaining_hours = remaining_tasks/average_rate
				else:
					remaining_hours = 0

				# dictionary of the data to return
				client_rate_data[client_id] = {
					'elapsed_minutes'	: round(elapsed_seconds/60,2),
					'current_rate'		: round(current_rate,2),
					'average_rate'		: round(average_rate,2),
					'remaining_tasks'	: remaining_tasks,
					'remaining_hours'	: round(remaining_hours,2)*crawl_depth
				}

			# for overall measure
			total_current_rate = (total_count/interval_seconds)*3600
			all_rates[None] += [total_current_rate]
			total_average_rate = statistics.mean(all_rates[None])
			
			# figure out how much longer to go, gracefully handle
			#	a rate of zero
			if total_average_rate != 0:
				remaining_hours = round((remaining_tasks/total_average_rate)*crawl_depth, 2)
			else:
				remaining_hours = 0

			# round down for days
			if remaining_hours > 24:
				remaining_time = f'{round(remaining_hours/24,2)} days'
			else:
				remaining_time = f'{remaining_hours} hours'

			client_rate_data[None] = {
				'elapsed_minutes'	: round(elapsed_seconds/60,2),
				'current_rate'		: round(total_current_rate,2),
				'average_rate'		: round(total_average_rate,2),
				'remaining_tasks'	: remaining_tasks,
				'remaining_hours'	: remaining_time
			}

			# if we are called by the flask admin_console it is
			#	easiest to do json formatting here, otherwise
			#	we don't.
			if return_json:
				yield f"data:{json.dumps(client_rate_data)}\n\n"
			else:
				yield client_rate_data

			# wait until we send a new update
			time.sleep(wait_seconds)
	# stream_rate

	def setup_report_dir(self, db_name):
		"""
		Create directory for where the reports go if it does not exist,
			returns the path.
		"""
		if os.path.exists('./reports') == False:
			print('\t\tMaking global reports directory at ./reports.')
			os.makedirs('./reports')
		
		# set global report_path
		report_path = './reports/'+db_name
	
		# set up subdir for this analysis
		if os.path.exists(report_path) == False:
			print('\t\tMaking subdirectory for reports at %s' % report_path)
			os.makedirs(report_path)

		print('\t\tStoring output in %s' % report_path)
		return report_path
	# setup_report_dir

	def write_csv(self, report_path, file_name, csv_rows, num_decimals=2):
		"""
		basic utility function to write list of csv rows to a file
		"""
		full_file_path = report_path+'/'+file_name
		with open(full_file_path, 'w', newline='', encoding='utf-8') as csvfile:
			csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			for row in csv_rows:
				rounded_row = []
				for item in row:
					# round floats and decimals
					if isinstance(item, float) or isinstance(item, decimal.Decimal):
						rounded_row.append(round(item,num_decimals))
					else:
						rounded_row.append(item)
						
				csv_writer.writerow(rounded_row)
		print('\t\tOutput written to %s' % full_file_path)
	# write_csv

	def print_runtime(self, action_name, start_time):
		"""
		Just for CLI info
		"""
		print('-'*40)
		print('\t%s finished in %s' % (action_name,str(datetime.now()-start_time)))
		print('-'*40)
	# print_runtime

	def get_absolute_url_from_page_link(self,page_url,link_url):
		"""
		Given a page_url and a link_url from that page we determine
			the absolute url of the link from the page_url.
		"""

		# ex nihilo nihil fit
		if link_url == None: return None
		if len(link_url) == 0: return None

		# we use the info from the original url for converting 
		#	relative links to absolute
		parsed_page_url = urlparse(page_url)

		# this is an absolute url already, nothing further to do to
		if re.match('^https?://', link_url):
			return(link_url)
		# link with no scheme, paste it in
		elif re.match('^//', link_url):
			return(parsed_page_url.scheme+':'+link_url)
		# relative link, fix it up
		else:
			if link_url[0] != '/':
				return(parsed_page_url.scheme + '://' + parsed_page_url.netloc + '/' + link_url)
			else:
				return(parsed_page_url.scheme + '://' + parsed_page_url.netloc + link_url)

		# this only happens if something breaks
		return None
	# get_absolute_url_from_link

	def get_most_common_sorted(self,list_in):
		"""
		takes a list, finds the most common items
		and then resorts alpha (b/c python's Counter will arbitrarily 
		order items with same count), then sorts again for most-common

		assumes list_in contains alphanumeric tuples
		"""
		most_common_sorted = collections.Counter(list_in).most_common()
		most_common_sorted.sort()
		most_common_sorted.sort(reverse=True, key=lambda item:item[1])
		return most_common_sorted
	# get_most_common_sorted

	#########################
	#	POLICY EXTRACTION	#
	#########################

	def get_policy_link_terms(self):
		"""
		Returns a list of terms used to indicate a link may be a policy, 
			note languages are all mixed together.
		"""
		policy_link_terms = []
		# go through json file and merge terms together
		for lang_term_set in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/policyxray/policy_terms.json', 'r', encoding='utf-8')):
			for term in lang_term_set['policy_link_terms']:
				policy_link_terms.append(term)
		return policy_link_terms
	# get_policy_link_terms

	def get_policy_verification_terms(self):
		"""
		Returns a dictionary of terms used to verify several types of
			policies, note languages are all mixed together.
		"""
		policy_verification_terms = {}
		policy_verification_terms['privacy_policy'] 	= []
		policy_verification_terms['terms_of_service']	= []
		policy_verification_terms['cookie_policy']		= []
		policy_verification_terms['ad_choices']			= []
		policy_verification_terms['gdpr_statement']		= []
		policy_verification_terms['ccpa_statement']		= []

		# go through json file and merge terms together
		for lang_term_set in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/policyxray/policy_terms.json', 'r', encoding='utf-8')):
			for term in lang_term_set['privacy_policy_verification_terms']:
				policy_verification_terms['privacy_policy'] = policy_verification_terms['privacy_policy'] + [term]

			for term in lang_term_set['terms_of_service_verification_terms']:
				policy_verification_terms['terms_of_service'] = policy_verification_terms['terms_of_service'] + [term]

			for term in lang_term_set['cookie_policy_verification_terms']:
				policy_verification_terms['cookie_policy'] = policy_verification_terms['cookie_policy'] + [term]
		
			for term in lang_term_set['ad_choices_verification_terms']:
				policy_verification_terms['ad_choices'] = policy_verification_terms['ad_choices'] + [term]

			for term in lang_term_set['gdpr_statement_verification_terms']:
				policy_verification_terms['gdpr_statement'] = policy_verification_terms['gdpr_statement'] + [term]

			for term in lang_term_set['ccpa_statement_verification_terms']:
				policy_verification_terms['ccpa_statement'] = policy_verification_terms['ccpa_statement'] + [term]

		return policy_verification_terms
	# get_policy_verification_terms

	def get_lang_to_privacy_policy_term_dict(self):
		"""
		Returns a dict of privacy policy terms keyed by language code.
		"""
		lang_to_terms = {}
		for lang_term_set in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/policyxray/policy_terms.json', 'r', encoding='utf-8')):
			lang_to_terms[lang_term_set['lang']] = lang_term_set['policy_terms']
		return lang_to_terms
	# get_lang_to_priv_term_dict


	#########################
	#	DOMAIN OWNERSHIP	#
	#########################

	def get_domain_owner_dict(self):
		"""
		read out everything in the domain_owner table into a dictionary
			so we can easily use it as a global lookup table
		
		this is purposefully independent of self.patch_domain_owners
			and does not assume the above has been run, however will return
			and empty dictionary if the db has not been patched yet

		reasons for above is that if user does not wish to update with the 
			current json file historical data will remain consistent
		"""

		# domain_owners is both returned as well as made available to other class functions
		self.domain_owners = {}
		domain_owner_raw_data = self.sql_driver.get_all_domain_owner_data()
		if domain_owner_raw_data:
			for item in domain_owner_raw_data:
				# add everything to the dict
				self.domain_owners[item[0]] = {
					'parent_id' :					item[1],
					'owner_name' :					item[2],
					'aliases' :						json.loads(item[3]),
					'homepage_url' :				item[4],
					'site_privacy_policy_urls': 	json.loads(item[5]),
					'service_privacy_policy_urls': 	json.loads(item[6]),
					'gdpr_statement_urls': 			json.loads(item[7]),
					'terms_of_use_urls': 			json.loads(item[8]),
					'platforms': 					json.loads(item[9]),
					'uses': 						json.loads(item[10]),
					'notes': 						item[11],
					'country':						item[12]
				}
		return self.domain_owners
	# get_domain_owner_dict

	def get_domain_owner_lineage_ids(self, id):
		"""
		for a given domain owner id, return the list which corresponds to its ownership lineage
		"""
		if self.domain_owners[id]['parent_id'] == None:
			return [id]
		else:
			return [id] + self.get_domain_owner_lineage_ids(self.domain_owners[id]['parent_id'])
	# get_domain_owner_lineage_ids

	def get_domain_owner_lineage_strings(self,owner_id,get_aliases=False):
		"""
		given an owner_id this function returns a list
			which is the full lineage of ownership

		optionally will also return aliases (e.g. 'Doubleclick' and 'Double Click')
		"""
		lineage_strings = []
		for owner_id in self.get_domain_owner_lineage_ids(owner_id):
			lineage_strings.append((owner_id,self.domain_owners[owner_id]['owner_name']))
			if get_aliases:
				for alias in self.domain_owners[owner_id]['aliases']:
					lineage_strings.append((owner_id,alias))
		return lineage_strings
	# get_domain_owner_lineage_strings

	def get_domain_owner_lineage_combined_string(self,owner_id):
		"""
		given an owner_id this function returns a single string
			which is the full lineage of ownership
		"""
		lineage_string = ''
		for item in self.get_domain_owner_lineage_strings(owner_id):
			lineage_string += item[1] + ' > '
		return lineage_string[:-3]
	# get_domain_owner_lineage_combined_string

	def get_domain_owner_child_ids(self,id):
		"""
		for a given owner id, get all of its children/subsidiaries
		"""
		
		# first get all the children ids if they exist
		child_ids = []
		for item in self.domain_owners:
			if self.domain_owners[item]['parent_id'] == id:
				child_ids.append(item)

		# if we have children, call recursively
		if len(child_ids) > 0:
			for child_id in child_ids:
				child_ids.extend(self.get_domain_owner_child_ids(child_id))

		# return an empty list if no children
		return child_ids
	# get_domain_owner_child_ids

	def is_url_valid(self, url):
		"""
		Performs checks to verify if the url can actually be
			scanned.
		"""

		# only do http links
		if not (re.match('^https?://.+', url)): return False

		# if we can't get the url_path it is invalid
		try:
			url_path = urlsplit(url.strip().lower()).path
		except:
			return False
		
		# if we can't do idna conversion it is invalid
		try:
			idna_fixed_netloc = urlsplit(url.strip()).netloc.encode('idna').decode('utf-8')
		except:
			return False

		# these are common file types we want to avoid
		illegal_extensions = [
			'apk',
			'dmg',
			'doc',
			'docx',
			'exe',
			'ics',
			'iso',
			'pdf',
			'ppt',
			'pptx',
			'rtf',
			'txt',
			'xls',
			'xlsx'
		]

		# if we can't parse the extension it doesn't exist and is
		#	therefore ok by our standards
		try:
			url_extension = re.search('\.([0-9A-Za-z]+)$', url_path).group(1)
			if url_extension in illegal_extensions: return False
		except:
			return True

		# it's good
		return True
	# is_url_valid

	def idna_encode_url(self, url, no_fragment=False):
		"""
		Non-ascii domains will crash some browsers, so we need to convert them to 
			idna/ascii/utf-8. This requires splitting apart the url, converting the 
			domain to idna, and pasting it all back together
		"""
		split_url = urlsplit(url.strip())
		idna_fixed_netloc = split_url.netloc.encode('idna').decode('utf-8')
		if no_fragment:
			return urlunsplit((split_url.scheme,idna_fixed_netloc,split_url.path,split_url.query,''))
		else:
			return urlunsplit((split_url.scheme,idna_fixed_netloc,split_url.path,split_url.query,split_url.fragment))
	# idna_encode_url

	def is_url_internal(self,origin_url,target_url):
		"""
		Given two urls (origin, target) determines if 
			the target is internal to the origin based on
			subsuffix+1 domain.
		"""

		origin_domain 	= self.url_parser.get_parsed_domain_info(origin_url)
		target_domain	= self.url_parser.get_parsed_domain_info(target_url)

		# we return None to signify we couldn't parse the urls
		if not origin_domain['success'] or not target_domain['success']:
			return None
		else:
			origin_domain 	= origin_domain['result']['domain']
			target_domain  	= target_domain['result']['domain']

		if origin_domain != target_domain:
			return False
		else:
			return True
	# is_url_internal

# Utilities	
