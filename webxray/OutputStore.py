# standard python libs
import os
import re
import html
import json
import random
import hashlib
import lxml.html
import lxml.etree
import unicodedata
import urllib.request
from datetime import datetime
from urllib.parse import urlparse
from urllib.parse import urlsplit

# non-standard libs which must be installed
from textstat.textstat import textstat
import lxml.html

# custom webxray classes
from webxray.ParseURL  import ParseURL
from webxray.Utilities import Utilities

class OutputStore:
	"""	
	This class receives data from the browser, processes it, and stores it in the db
	"""

	def __init__(self, db_name, db_engine):
		self.db_name	= db_name
		self.utilities	= Utilities()
		self.url_parser = ParseURL()
		self.debug		= False
		if db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			self.sql_driver = SQLiteDriver(self.db_name)
		elif db_engine == 'postgres':
			from webxray.PostgreSQLDriver import PostgreSQLDriver
			self.sql_driver = PostgreSQLDriver(self.db_name)
		else:
			print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
			quit()
		self.config 	= self.sql_driver.get_config()
	# __init__

	def close(self):
		"""
		Just to make sure we close the db connection.
		"""
		self.sql_driver.close()
	# close

	def store_scan(self, params):
		"""
		This function pre-processes data from the browser, inserts it into 
			database, and handles linking various entries across tables.
		"""

		# unpack params
		browser_output 	= params['browser_output']
		client_id 		= params['client_id']
		crawl_id 		= params['crawl_id']
		crawl_timestamp = params['crawl_timestamp']
		crawl_sequence	= params['crawl_sequence']

		# client_ip is optional
		if 'client_ip' in params:
			client_ip = params['client_ip']
		else:
			client_ip = None

		if self.debug: print('going to store scan %s' % browser_output['start_url'])

		# keep track of domains
		page_3p_cookie_domains 		= set()
		page_3p_dom_storage_domains = set()
		page_3p_request_domains 	= set()
		page_3p_response_domains 	= set()
		page_3p_websocket_domains 	= set()

		# convert from timestamp to datetime object that will go to the db
		accessed = datetime.fromtimestamp(browser_output['accessed'])

		# first make sure we don't have it already
		if self.sql_driver.page_exists(browser_output['start_url'],accessed): 
			return {'success': False, 'result': 'exists in db already'}

		# if we have no responses the page didn't load at all and we skip
		#	 unless we are using basic driver and then it's ok
		if len(browser_output['responses']) == 0 and browser_output['browser_type'] != 'basic':
			return {'success': False, 'result': 'no responses received'}

		# ignore any malformed unicode characters
		page_source = browser_output['page_source'].encode('utf-8', 'ignore').decode()

		# store source
		if self.config['store_source']:
			if self.debug: print('going to store source %s' % browser_output['start_url'])
			page_source_md5 = self.store_file(page_source, False, 'page_source')
		else:
			page_source_md5 = None

		# store readability_html
		if self.config['store_page_text'] and browser_output['page_text']:
			if self.debug: print('going to store readability_html')
			# ignore any malformed unicode characters
			readability_html 		= browser_output['readability_html'].encode('utf-8', 'ignore').decode().strip()
			readability_source_md5 	= self.store_file(readability_html, False, 'readability_html')

			# store_page_text handles some addition operations
			if self.debug: print('going to store page_text')
			page_text_id = self.store_page_text(readability_html,readability_source_md5)
		else:
			page_text_id 			= None

		# process info on the start_url domain
		if self.debug: print('going to parse start/final_url %s' % browser_output['start_url'])
		start_url = browser_output['start_url']
		start_url_domain_info = self.url_parser.get_parsed_domain_info(start_url)
		if start_url_domain_info['success'] == False:
			err_msg = 'unable to parse start_url_domain_info info for %s with error %s' % (browser_output['start_url'], start_url_domain_info['result'])
			if self.debug: print(err_msg)
			self.sql_driver.log_error({
				'client_id'		: client_id, 
				'target'		: start_url, 
				'task'			: 'output_store',
				'msg'			: err_msg
			})
			return {'success': False, 'result': 'could not parse start_url'}
		else:
			# needed for comparisons later on
			start_url_domain = start_url_domain_info['result']['domain']

			# add start_url domain and get id
			start_url_domain_id = self.sql_driver.add_domain(start_url_domain_info['result'])

		# process info on the final_url domain
		# note: we use the final_url domain as the benchmark for determine 1p/3p
		final_url = browser_output['final_url']
		final_url_domain_info = self.url_parser.get_parsed_domain_info(final_url)
		if final_url_domain_info['success'] == False:
			err_msg = 'unable to parse final_url_domain_info info for %s with error %s' % (browser_output['final_url'], final_url_domain_info['result'])
			if self.debug: print(err_msg)
			self.sql_driver.log_error({
				'client_id'		: client_id, 
				'target'		: start_url, 
				'task'			: 'output_store',
				'msg'			: err_msg
			})
			return {'success': False, 'result': 'could not parse final_url'}
		else:
			final_url_domain = final_url_domain_info['result']['domain']
			# self.sql_driver.add_domain both stores the new domain and returns its db row id
			# if it is already in db just return the existing id
			final_url_domain_id = self.sql_driver.add_domain(final_url_domain_info['result'])

		# check if the page has redirected to a new domain
		if start_url_domain != final_url_domain:
			page_domain_redirect = True
		else:
			page_domain_redirect = False

		# this is semi-redundant but ensures that any config changes made while
		#	a result is queued are followed
		if self.config['client_reject_redirects'] and page_domain_redirect:
			return {'success': False, 'result': 'rejecting redirect'}

		# if the final page is https (often after a redirect), mark it appropriately
		if browser_output['final_url'][:5] == 'https':
			page_is_ssl = True
		else:
			page_is_ssl = False

		# (optionally) process and store links, this allows us to go back later and do deeper scans
		#	as well as do more with policies
		
		# links starts as empty list
		links = []

		# keep track of link counts as helpful for filtering pages
		link_count_internal = 0
		link_count_external = 0

		if self.config['store_links']:

			if self.debug: print('going to process links %s' % browser_output['start_url'])

			# we use the list of policy_link_terms to flag that a link *might*
			# 	be for a policy, we check if it actually is policy in PolicyCollector.py
			policy_link_terms = self.utilities.get_policy_link_terms()

			# process links, duplicates get ignored by db
			for link in browser_output['all_links']:
				# skip if href not valid
				if not self.utilities.is_url_valid(link['href']): continue

				# unpack values and catch any unicode errors
				link_text = link['text'].encode('utf-8', 'ignore').decode()
				link_url  = link['href'].encode('utf-8', 'ignore').decode()

				# get rid of trailing # and /
				if link_url.strip()[-1:] == '#': link_url = link_url.strip()[:-1]
				if link_url.strip()[-1:] == '/': link_url = link_url.strip()[:-1]

				# sometimes the text will be a dict (very rarely)
				# 	so we convert to string
				link_text = str(link_text).strip()

				# clean up white space and remove line breaks
				link_text = re.sub('\n|\r|\t|\s+',' ',link_text.strip())
				link_url  = re.sub('\n|\r|\t|\s+',' ',link_url.strip())

				# catch nulls
				link_text = link_text.replace('\x00','NULL_REPLACED_FOR_PSQL')
				link_url  = link_url.replace('\x00','NULL_REPLACED_FOR_PSQL')

				# update counts
				if link['internal']:
					link_count_internal += 1
				else:
					link_count_external += 1

				# flag links that could be policies, default False
				link_is_policy = False

				# determine if a policy term appears in the link
				for policy_term in policy_link_terms:
					if policy_term in link_text.lower():
						link_is_policy = True
						break

				link_domain_info = self.url_parser.get_parsed_domain_info(link_url)
				if link_domain_info['success'] == False:
					# don't bother with storing errors
					link_domain_id = None
				else:
					# self.sql_driver.add_domain both stores the new domain and returns its db row id
					# 	if it is already in db just return the existing id
					link_domain_id = self.sql_driver.add_domain(link_domain_info['result'])

				links.append({
					'url'			: link_url, 
					'text'			: link_text, 
					'is_internal'	: link['internal'], 
					'is_policy'		: link_is_policy, 
					'domain_id'		: link_domain_id
				})

		# if we got the screen shot we get the hash and store it to the file table
		screen_shot_md5 = None
		if browser_output['screen_shot'] and self.config['store_screen_shot']:
			if self.debug: print('going to store screen shot %s' % browser_output['start_url'])
			# store file to get md5
			screen_shot_md5 = self.store_file(browser_output['screen_shot'],True,'screen_shot')

		# if we have timestamp it is also an 'accessed' field from
		#	a page load so we convert that as well
		if crawl_timestamp:
			crawl_timestamp = datetime.fromtimestamp(crawl_timestamp)

		# ignore any malformed unicode characters
		if browser_output['title']:
			browser_output['title'] = browser_output['title'].encode('utf-8', 'ignore').decode()

		if browser_output['meta_desc']:
			browser_output['meta_desc'] = browser_output['meta_desc'].encode('utf-8', 'ignore').decode()

		if browser_output['lang']:
			browser_output['lang'] = browser_output['lang'].encode('utf-8', 'ignore').decode()

		# now we know link counts we can store the page
		if self.debug: print('going to store page %s' % browser_output['start_url'])
		page_id = self.sql_driver.add_page({
			'accessed'				: accessed,
			'browser_type'			: browser_output['browser_type'],
			'browser_version'		: browser_output['browser_version'],
			'browser_prewait'		: browser_output['prewait'],
			'browser_no_event_wait'	: browser_output['no_event_wait'],
			'browser_max_wait'		: browser_output['max_wait'],
			'page_load_strategy'	: browser_output['page_load_strategy'],
			'title'					: browser_output['title'],
			'meta_desc'				: browser_output['meta_desc'],
			'lang'					: browser_output['lang'],
			'start_url'				: browser_output['start_url'],
			'final_url'				: browser_output['final_url'],
			'is_ssl'				: page_is_ssl,
			'page_domain_redirect'	: page_domain_redirect,
			'link_count_internal'	: link_count_internal,
			'link_count_external'	: link_count_external,
			'load_time'				: browser_output['load_time'],
			'start_url_domain_id'	: start_url_domain_id,
			'final_url_domain_id'	: final_url_domain_id,
			'client_id'				: client_id,
			'client_timezone'		: browser_output['client_timezone'],
			'client_ip'				: client_ip,
			'page_text_id'			: page_text_id,
			'screen_shot_md5'		: screen_shot_md5,
			'page_source_md5'		: page_source_md5,
			'crawl_id'				: crawl_id,
			'crawl_timestamp'		: crawl_timestamp,
			'crawl_sequence'		: crawl_sequence
		})

		# STORE LINKS
		if self.config['store_links']:
			if self.debug: print('going to store links %s' % browser_output['start_url'])
			for link in links:
				link_id = self.sql_driver.add_link(link)
				if link_id: self.sql_driver.join_link_to_page(page_id,link_id)

		# PROCESS DOM_STORAGE
		if self.config['store_dom_storage']:
			if self.debug: print('going to process dom storage %s' % browser_output['start_url'])
			for dom_storage in browser_output['dom_storage']:
				# parse domain from the security_origin, which is equivalent to a url
				domain_info = self.url_parser.get_parsed_domain_info(dom_storage['security_origin'])
				if domain_info['success'] == False:
					err_msg = 'unable to parse domain info for %s with error %s' % (dom_storage['security_origin'], domain_info['result'])
					if self.debug: print(err_msg)
					self.sql_driver.log_error({
						'client_id'		: client_id, 
						'target'		: start_url, 
						'task'			: 'output_store',
						'msg'			: err_msg
					})
					continue
				else:
					# self.sql_driver.add_domain both stores the new domain and returns its db row id
					# if it is already in db just return the existing id
					dom_storage['domain_id'] = self.sql_driver.add_domain(domain_info['result'])

				# mark if third-party storage
				if final_url_domain != domain_info['result']['domain']:
					dom_storage['is_3p'] = True
				else:
					dom_storage['is_3p'] = False

				# key to page
				dom_storage['page_id'] = page_id

				# replace null b/c postgres will die otherwise
				dom_storage['key']		= dom_storage['key'].replace('\x00','NULL_REPLACED_FOR_PSQL')
				dom_storage['value']	= dom_storage['value'].replace('\x00','NULL_REPLACED_FOR_PSQL')

				# there types of illegal utf-8 characters that psql doesn't like, eg trying to store
				#	'\uded5' gives this error when storing in psql: 
				#	'UnicodeEncodeError: 'utf-8' codec can't encode character '\uded5' in position 0: surrogates not allowed'
				#
				# to overcome the above, we use python's backslashreplace to keep the original data in 
				#	a way that won't cause our queries to die
				# see https://docs.python.org/3/library/codecs.html#error-handlers
				dom_storage['key']		= dom_storage['key'].encode('utf-8','backslashreplace')
				dom_storage['value']	= dom_storage['value'].encode('utf-8','backslashreplace')

				# now that we've encoded with backslashes we decode to get the semi-original data
				dom_storage['key']		= dom_storage['key'].decode('utf-8')
				dom_storage['value']	= dom_storage['value'].decode('utf-8')

				# all done with this item
				self.sql_driver.add_dom_storage(dom_storage)

				# update domains
				if dom_storage['is_3p']:
					page_3p_dom_storage_domains.add((domain_info['result']['domain'],domain_info['result']['domain_owner_id']))

		# PROCESS LOAD FINISH
		if self.debug: print('going to process load finish data %s' % browser_output['start_url'])
		load_finish_data = {}
		for load_finish_event in browser_output['load_finish_events']:
			load_finish_data[load_finish_event['request_id']] = load_finish_event['encoded_data_length']

		# RESPONSE EXTRA HEADERS
		if self.debug: print('going to process response extra header data %s' % browser_output['start_url'])
		http_cookies = []
		internal_id_to_resp_ex_headers = {}
		for response_extra_header in browser_output['response_extra_headers']:
			response_extra_header['page_id'] 		= page_id
			response_extra_header['cookies_set']	= None
			
			# to check for domain leakage in headers we make a big string keyed to the internal id
			if response_extra_header['request_id'] not in internal_id_to_resp_ex_headers:
				internal_id_to_resp_ex_headers[response_extra_header['request_id']] = str(response_extra_header['headers'])
			else:
				internal_id_to_resp_ex_headers[response_extra_header['request_id']] += str(response_extra_header['headers'])

			for item in response_extra_header['headers']:
				if item.lower() == 'set-cookie':
					response_extra_header['cookies_set'] = response_extra_header['headers'][item]

					# when we add cookies later on we mark those that came from response headers,
					#	note we try/pass on this in case we can't parse
					for cookie in response_extra_header['cookies_set'].split('\n'):
						if 'domain' in cookie.lower():
							try:
								name = re.match('^(.+?)=',cookie)[0][:-1]
								domain = re.match('^.+domain=(.+?)(;|$)',cookie.lower())[1]
								if domain[0] == '.': domain = domain[1:]
								http_cookies.append((domain,name))
							except:
								pass

			if self.config['store_response_xtra_headers']:
				self.sql_driver.add_response_extra_header(response_extra_header)

		# PROCESS RESPONSES
		response_received_req_ids = []
		
		if self.debug: print('going to process response data %s' % browser_output['start_url'])
		
		for response in browser_output['responses']:
			
			# defaut values that may get over-written
			response['file_md5'] 				= None
			response['is_data']  				= False
			response['is_3p'] 					= None
			response['is_ssl']					= None
			response['page_domain_in_headers'] 	= False

			# first handle non-http urls and optionally store content
			if re.match('^(data|about|chrome|blob|javascript).+', response['url']):
				if 'base64' in response['url'].lower() or 'image' in response['type'].lower():
					is_base64 = True
				else:
					is_base64 = False
					
				# store_file follows the config as far as actually storing the file goes 
				#	and will either return the md5 or None
				# make sure we're following our configuration
				if self.config['store_files'] and (self.config['store_base64'] or is_base64 == False):
					response['file_md5'] = self.store_file(response['url'],is_base64,response['type'])
				else:
					response['file_md5'] = None

				response['url']	      = None
				response['is_data']   = True
				response['domain_id'] = None
			else:
				# parse, store, and get id of domain; if fails skip
				domain_info = self.url_parser.get_parsed_domain_info(response['url'])
				if domain_info['success'] == False:
					err_msg = 'unable to parse domain info for %s with error %s' % (response['url'], domain_info['result'])
					if self.debug: print(err_msg)
					self.sql_driver.log_error({
						'client_id'		: client_id, 
						'target'		: start_url, 
						'task'			: 'output_store',
						'msg'			: err_msg
					})
					continue
				else:
					response_domain = domain_info['result']['domain']
					response['domain_id'] = self.sql_driver.add_domain(domain_info['result'])

				# now add ip
				if response['remote_ip_address']:
					self.sql_driver.add_domain_ip_addr(response['domain_id'],response['remote_ip_address'])

				# mark third-party responses based on final_url domain
				if response_domain != final_url_domain:
					response['is_3p'] = True
				else:
					response['is_3p'] = False

				# determine if encrypted
				if response['url'][:5] == 'https' or response['url'][:3] == 'wss':
					response['is_ssl']  = True
				else:
					response['is_ssl']  = False


			# keep track of the request ids of each reponse to mark as received
			response_received_req_ids.append(response['request_id'])

			# we do no more processing at this point
			if not self.config['store_responses']:
				continue

			# lower case the type, simplifies db queries
			response['type'] = response['type'].lower()

			# store the security details if they exist
			if response['security_details'] and self.config['store_security_details']:
				response['security_details_id'] = self.sql_driver.add_security_details(response['security_details'])
			else:
				response['security_details_id'] = None

			# store the size of the request
			if response['request_id'] in load_finish_data:
				response['final_data_length'] = load_finish_data[response['request_id']]
			else:
				response['final_data_length'] = None

			# parse off args/etc

			# consider anything before the "?" to be the element_url
			try:
				response['base_url'] = re.search('^(.+?)\?.+$', response['url']).group(1)
			except:
				response['base_url'] = response['url']

			# attempt to parse off the extension
			try:
				response['extension'] = re.search('\.([0-9A-Za-z]+)$', response['base_url']).group(1).lower()
			except:
				response['extension'] = None
			
			# First see if this request_id is present in response_bodies, and if
			#	the entry is not None, then we store it to the db if config says to.
			if response['request_id'] in browser_output['response_bodies']:
				if browser_output['response_bodies'][response['request_id']]:
					# make sure we're following our configuration
					is_base64 = browser_output['response_bodies'][response['request_id']]['is_base64']
					if self.config['store_files'] and (self.config['store_base64'] or is_base64 == False):
						response['file_md5'] = self.store_file(
							browser_output['response_bodies'][response['request_id']]['body'],
							is_base64,
							response['type']
						)
					else:
						response['file_md5'] = None

			# link to page
			response['page_id'] = page_id

			# parse data headers, accounts for upper/lower case variations (eg 'set-cookie', 'Set-Cookie')
			response['content_type'] = None
			response['cookies_set'] = None
			
			for item in response['response_headers']:
				if item.lower() == 'content-type':
					response['content_type'] = response['response_headers'][item]
				
				if item.lower() == 'set-cookie':
					response['cookies_set']  = response['response_headers'][item]

			# if we have request_headers look for cookies sent
			response['cookies_sent']  = None
			if response['request_headers']:
				for item in response['request_headers']:
					if item.lower() == 'cookie':
						response['cookies_sent']  = response['request_headers'][item]

			# parse referer header
			response['referer'] = None
			for item in response['response_headers']:
				if item.lower() == 'referer':
					response['referer'] = response['response_headers'][item]

			# check if domain leaked in referer
			if response['request_id'] in internal_id_to_resp_ex_headers:
				if final_url_domain in internal_id_to_resp_ex_headers[response['request_id']]:
					response['page_domain_in_headers'] = True

			# convert from timestamp to datetime object that will go to the db
			response['timestamp'] = datetime.fromtimestamp(response['timestamp'])

			# store
			self.sql_driver.add_response(response)

			# update domains
			if response['is_3p']:
				page_3p_response_domains.add((domain_info['result']['domain'],domain_info['result']['domain_owner_id']))

		# REQUEST EXTRA HEADERS
		if self.debug: print('going to process request extra headers data %s' % browser_output['start_url'])
		internal_id_to_req_ex_headers = {}
		for request_extra_header in browser_output['request_extra_headers']:
			request_extra_header['page_id'] 		= page_id
			request_extra_header['cookies_sent']	= None

			# to check for domain leakage in headers we make a big string keyed to the internal id
			if request_extra_header['request_id'] not in internal_id_to_req_ex_headers:
				internal_id_to_req_ex_headers[request_extra_header['request_id']] = str(request_extra_header['headers'])
			else:
				internal_id_to_req_ex_headers[request_extra_header['request_id']] += str(request_extra_header['headers'])
			
			for item in request_extra_header['headers']:
				if item.lower() == 'cookie':
					request_extra_header['cookies_sent'] = request_extra_header['headers'][item]
			
			if self.config['store_request_xtra_headers']:
				self.sql_driver.add_request_extra_header(request_extra_header)

		# PROCESS REQUESTS
		if self.config['store_requests']:
			if self.debug: print('going to process request data %s' % browser_output['start_url'])
			for request in browser_output['requests']:
				# defaut values that may get over-written
				request['file_md5'] 				= None
				request['is_data']  				= False
				request['is_3p'] 					= None
				request['is_ssl']					= None
				request['page_domain_in_headers'] 	= False

				# first handle non-http urls and optionally store content
				if re.match('^(data|about|chrome|blob|javascript).+', request['url']):
					if 'base64' in request['url'].lower() or 'image' in request['url'].lower():
						is_base64 = True
					else:
						is_base64 = False
					
					# store_file follows the config as far as actually storing the file goes 
					#	and will either return the md5 or None
					# make sure we're following our configuration
					if self.config['store_files'] and (self.config['store_base64'] or is_base64 == False):
						request['file_md5'] = self.store_file(request['url'],is_base64,request['type'])
					else:
						request['file_md5'] = None

					request['url']	     = None
					request['is_data']   = True
					request['domain_id'] = None
				else:
					# parse, store, and get id of domain; if fails skip
					domain_info = self.url_parser.get_parsed_domain_info(request['url'])
					if domain_info['success'] == False:
						err_msg = 'unable to parse domain info for %s with error %s' % (request['url'], domain_info['result'])
						if self.debug: print(err_msg)
						self.sql_driver.log_error({
							'client_id'		: client_id, 
							'target'		: start_url, 
							'task'			: 'output_store',
							'msg'			: err_msg
						})
						continue
					else:
						request_domain = domain_info['result']['domain']
						request['domain_id'] = self.sql_driver.add_domain(domain_info['result'])

					# mark third-party requests based on final_url domain
					if request_domain != final_url_domain:
						request['is_3p'] = True
					else:
						request['is_3p'] = False

					# determine if encrypted
					if request['url'][:5] == 'https' or request['url'][:3] == 'wss':
						request['is_ssl']  = True
					else:
						request['is_ssl']  = False

				# replace null b/c postgres will die otherwise
				if request['post_data']:
					request['post_data'] = request['post_data'].replace('\x00','NULL_REPLACED_FOR_PSQL')

				# consider anything after the "?" to be the GET data
				try:
					get_string = re.search('^.+\?(.+)$', request['url']).group(1)
					get_string = get_string.replace('\x00','NULL_REPLACED_FOR_PSQL')
					get_data = {}
					for key_val in get_string.split('&'):
						get_data[key_val.split('=')[0]] = key_val.split('=')[1]
					request['get_data'] = json.dumps(get_data)
				except:
					request['get_data'] = None

				# mark if response received
				if request['request_id'] in response_received_req_ids:
					request['response_received'] = True
				else:
					request['response_received'] = None

				# mark if the loading finished
				if request['request_id'] in load_finish_data:
					request['load_finished'] = True
				else:
					request['load_finished'] = None

				# lower case the type, simplifies db queries
				if request['type']: request['type'] = request['type'].lower()

				# parse off args/etc

				# consider anything before the "?" to be the element_url
				try:
					request['base_url'] = re.search('^(.+?)\?.+$', request['url']).group(1)
				except:
					request['base_url'] = request['url']

				# attempt to parse off the extension
				try:
					request['extension'] = re.search('\.([0-9A-Za-z]+)$', request['base_url']).group(1).lower()
				except:
					request['extension'] = None

				# link to page
				request['page_id'] = page_id

				# parse referer header
				request['referer'] = None
				for item in request['headers']:
					if item.lower() == 'referer':
						request['referer'] 	 = request['headers'][item]

				# check if domain leaked in headers
				if request['request_id'] in internal_id_to_req_ex_headers:
					if final_url_domain in internal_id_to_req_ex_headers[request['request_id']]:
						request['page_domain_in_headers'] = True

				# convert from timestamp to datetime object that will go to the db
				request['timestamp'] = datetime.fromtimestamp(request['timestamp'])

				# all done
				self.sql_driver.add_request(request)

				# update domains
				if request['is_3p']:
					page_3p_request_domains.add((domain_info['result']['domain'],domain_info['result']['domain_owner_id']))

		# PROCESS WEBSOCKETS
		if self.config['store_websockets']:
			if self.debug: print('going to process websocket data %s' % browser_output['start_url'])
			ws_id_map = {}
			for websocket in browser_output['websockets']:
				domain_info = self.url_parser.get_parsed_domain_info(websocket['url'])
				if domain_info['success'] == False:
					err_msg = 'unable to parse domain info for %s with error %s' % (websocket['url'], domain_info['result'])
					if self.debug: print(err_msg)
					self.sql_driver.log_error({
						'client_id'		: client_id, 
						'target'		: start_url, 
						'task'			: 'output_store',
						'msg'			: err_msg
					})
					continue
				else:
					# self.sql_driver.add_domain both stores the new domain and returns its db row id
					# if it is already in db just return the existing id
					websocket['domain_id'] = self.sql_driver.add_domain(domain_info['result'])

				# mark if third-party connection
				if final_url_domain != domain_info['result']['domain']:
					websocket['is_3p'] = True
				else:
					websocket['is_3p'] = False

				websocket['page_id'] = page_id
				this_websocket_id = self.sql_driver.add_websocket(websocket)

				# update domains
				if websocket['is_3p']:
					page_3p_websocket_domains.add((domain_info['result']['domain'],domain_info['result']['domain_owner_id']))

				if websocket['request_id'] not in ws_id_map:
					ws_id_map[websocket['request_id']] = this_websocket_id
				else:
					print('ERROR WS_REQ_ID ALREADY IN MAP')

		# PROCESS WEBSOCKET EVENTS
		if self.config['store_websockets'] and self.config['store_websocket_events']:
			for websocket_event in browser_output['websocket_events']:
				websocket_event['page_id'] = page_id
				if websocket_event['request_id'] in ws_id_map:
					websocket_event['websocket_id'] = ws_id_map[websocket_event['request_id']]
				else:
					websocket_event['websocket_id'] = None

				# convert from timestamp to datetime object that will go to the db
				websocket_event['timestamp'] = datetime.fromtimestamp(websocket_event['timestamp'])

				self.sql_driver.add_websocket_event(websocket_event)

		# PROCESS EVENT SOURCE MSGS
		if self.config['store_event_source_msgs']:
			if self.debug: print('going to process event source data %s' % browser_output['start_url'])
			for event_source_msg in browser_output['event_source_msgs']:
				event_source_msg['page_id'] = page_id

				# convert from timestamp to datetime object that will go to the db
				event_source_msg['timestamp'] = datetime.fromtimestamp(event_source_msg['timestamp'])

				self.sql_driver.add_event_source_msg(event_source_msg)

		# PROCESS COOKIES
		if self.config['store_cookies']:
			if self.debug: print('going to process cookies %s' % browser_output['start_url'])
			for cookie in browser_output['cookies']:
				# get the ip, fqdn, domain, pubsuffix, and tld
				# we need the domain to figure out if cookies/elements are third-party
				# note:
				#	url_parser fails on non-http, we should fix this, right now a lame hack is to prepend http://

				# parse domain from the security_origin, which is equivalent to a url
				domain_info = self.url_parser.get_parsed_domain_info('http://'+cookie['domain'])

				if domain_info['success'] == False:
					err_msg = 'unable to parse domain info for %s with error %s' % (cookie['domain'], domain_info['result'])
					if self.debug: print(err_msg)
					self.sql_driver.log_error({
						'client_id'		: client_id, 
						'target'		: start_url, 
						'task'			: 'output_store',
						'msg'			: err_msg
					})
					continue
				else:
					# self.sql_driver.add_domain both stores the new domain and returns its db row id
					# if it is already in db just return the existing id
					cookie['domain_id'] = self.sql_driver.add_domain(domain_info['result'])

				# mark if third-party cookie
				if final_url_domain != domain_info['result']['domain']:
					cookie['is_3p'] = True
				else:
					cookie['is_3p'] = False

				# key to page
				cookie['page_id'] = page_id

				# fix var names
				cookie['http_only'] = cookie['httpOnly']

				# attempt to convert cookie expiry from timestamp to datetime object, note we 
				#	need try/except as python datetime object cannot have year > 9999 and some 
				#	cookies do that
				cookie['expires_timestamp'] = None
				if cookie['expires']: 
					try:
						cookie['expires_timestamp'] = datetime.fromtimestamp(cookie['expires'])
					except:
						pass

				# this is optional, do fall-back
				if 'sameSite' in cookie:
					cookie['same_site'] = cookie['sameSite']
				else:
					cookie['same_site'] = None

				# see if this cookie was set via http response
				if cookie['domain'][0] == '.': 
					cookie_tuple = (cookie['domain'][1:],cookie['name'])
				else:
					cookie_tuple = (cookie['domain'],cookie['name'])
				
				if cookie_tuple in http_cookies:
					cookie['is_set_by_response'] = True
				else:
					cookie['is_set_by_response'] = False

				# all done with this cookie
				self.sql_driver.add_cookie(cookie)

				# update domains
				if cookie['is_3p']:
					page_3p_cookie_domains.add((domain_info['result']['domain'],domain_info['result']['domain_owner_id']))

		if self.debug: print('done storing scan %s' % browser_output['start_url'])
		return {
			'success'						: True,
			'page_id'						: page_id,
			'page_3p_request_domains'		: page_3p_request_domains,
			'page_3p_response_domains'		: page_3p_response_domains,
			'page_3p_websocket_domains'		: page_3p_websocket_domains,
			'page_3p_dom_storage_domains'	: page_3p_dom_storage_domains,
			'page_3p_cookie_domains'		: page_3p_cookie_domains
		}
	# store_scan

	def store_file(self,body,is_base64,type):
		"""
		Hashes and stores file, returns file_md5.
		"""

		# in theory we shouldn't get here if it is base64, so this is a fail-safe check
		if not self.config['store_base64']:
			if is_base64 or type.lower()=='image':
				return None

		# note hash is on original data, which we modify to remove \x00 before we store
		file_md5 = hashlib.md5(body.encode()).hexdigest()

		# store to db, note query will be ignored on conflict
		#	but since we calculate the md5 as above that is fine
		self.sql_driver.add_file({
			'md5'		: file_md5,
			'body'		: body.replace('\x00','NULL_REPLACED_FOR_PSQL'),
			'type'		: type.lower(),
			'is_base64'	: is_base64
		})

		return file_md5
	# store_file

	def store_policy(self, browser_output, client_id, client_ip=None):
		"""
		We attempt to figure out if the text provided is a policy, if so
			we store it to the database.
		"""

		# keep values in a dict here
		policy = {}

		# attempt to get_policy was a success, extract data from
		#	dict, since postgres cannot handle '\x00' we convert to 
		#	string for several fields and use .replace('\x00',' ') to 
		# 	clean the input
		policy['client_id']			= client_id
		policy['client_ip']			= client_ip
		policy['browser_type']		= browser_output['browser_type']
		policy['browser_version']	= browser_output['browser_version']
		policy['browser_prewait']	= browser_output['prewait']
		policy['start_url']			= browser_output['start_url']
		policy['final_url']			= browser_output['final_url']
		policy['title']				= browser_output['title']
		policy['meta_desc']			= browser_output['meta_desc']
		policy['lang']				= browser_output['lang']
		policy['fk_score']			= None
		policy['fre_score']			= None
		policy['word_count']		= None
		policy['type']				= None
		policy['match_term']		= None
		policy['match_text']		= None
		policy['match_text_type']	= None
		policy['confidence']		= None
		policy['page_text_id']		= None
		policy['page_source_md5']	= None

		# if readability failed we bail
		if not browser_output['readability_html'] or not browser_output['page_text']:
			self.sql_driver.close()
			return {
				'success'	: False,
				'result'	: 'No readability result'
			}

		# ignore any malformed unicode characters
		readability_html 	= browser_output['readability_html'].encode('utf-8', 'ignore').decode().strip()
		page_text 			= browser_output['page_text'].encode('utf-8', 'ignore').decode().strip()
		page_source 		= browser_output['page_source'].encode('utf-8', 'ignore').decode()

		# bail on empty text
		if len(page_text) == 0:
			self.sql_driver.close()
			return {
				'success'	: False,
				'result'	: 'Empty page text'
			}

		# load the source into lxml so we can do additional processing, 
		#	if we fail we bail
		try:
			lxml_doc = lxml.html.fromstring(readability_html)
		except:
			return ({
				'success': False,
				'result': 'Could not parse readability_html with lxml'
			})

		# if the text is less than 500 words we ignore it
		if len(page_text.split(' ')) < 500:
			self.sql_driver.close()
			return {
				'success'	: False,
				'result'	: 'Page text < 500 words'
			}

		# once we have the text we figure out if it is 
		#	a policy, start false, override on match
		is_policy = False

		# first look for matches on page title
		# 	we give this confidence of 100 as it is
		#	definitely a match
		if policy['title']:
			policy_type_result = self.determine_policy_type_from_text(policy['title'])
			if policy_type_result['success'] == True:
				is_policy 		= True
				policy['type']				= policy_type_result['result']['policy_type']
				policy['match_term']		= policy_type_result['result']['match_term']
				policy['match_text']		= policy_type_result['result']['match_text']
				policy['match_text_type']	= 'title'
				policy['confidence']		= 100

		# deep checks may generate false positives so
		#	they have confidence of 0 until they can
		#	be verified, note we may do this here
		#	or later on
		deep_checks = True
		if deep_checks:
			policy['confidence'] = 0
			# convert the url path to a sentence by replacing
			#	common delimiters with spaces and attempt matches	
			if self.debug: print('going to do checks on url path')
			if not is_policy:
				url_path_string = re.sub('[-|_|/|\.]',' ',urlsplit(policy['start_url']).path)
				if len(url_path_string) > 0:
					policy_type_result = self.determine_policy_type_from_text(url_path_string)
					if policy_type_result['success'] == True:
						is_policy 					= True
						policy['type']				= policy_type_result['result']['policy_type']
						policy['match_term']		= policy_type_result['result']['match_term']
						policy['match_text']		= policy_type_result['result']['match_text']
						policy['match_text_type']	= 'url_path'

			if self.debug: print('going to do checks on meta desc')
			if not is_policy and policy['meta_desc']:
				policy_type_result = self.determine_policy_type_from_text(policy['meta_desc'])
				if policy_type_result['success'] == True:
					is_policy 					= True
					policy['type']				= policy_type_result['result']['policy_type']
					policy['match_term']		= policy_type_result['result']['match_term']
					policy['match_text']		= policy_type_result['result']['match_text']
					policy['match_text_type']	= 'meta_desc'

			# iterate over all types of heading tags to extract text 
			#	and check for policy matches.  note we go in order of
			#	importance (eg h1->h7->span,etc)
			if self.debug: print('going to do checks on heading tags')
			if not is_policy:
				for tag_type in ['h1','h2','h3','h4','h5','h6','h7','span','strong','em']:
					if is_policy: break
					tags = lxml_doc.cssselect(tag_type)
					if len(tags) > 0:
						for tag in tags:
							tag_text = tag.text_content()
							# if it is > 15 words it is likely not a heading
							if len(tag_text.split(' ')) > 15: break
							policy_type_result = self.determine_policy_type_from_text(tag_text)
							if policy_type_result['success'] == True:
								is_policy 					= True
								policy['type']				= policy_type_result['result']['policy_type']
								policy['match_term']		= policy_type_result['result']['match_term']
								policy['match_text']		= policy_type_result['result']['match_text']
								policy['match_text_type']	= tag_type

		# if it is a policy we do additional processing
		#	before storing in db, otherwise we fail
		#	gracefully
		if is_policy:
			if self.debug: print('going to store readability_html')
			readability_source_md5 = self.store_file(readability_html, False, 'readability_html')

			if self.debug: print('going to store page_text')

			# store_page_text handles some addition operations
			if self.debug: print('going to store page_text')
			policy['page_text_id'] = self.store_page_text(readability_html, readability_source_md5)

			if self.debug: print(f"page_text_id is {policy['page_text_id']}")

			if self.debug: print('going to store page_source')
			policy['page_source_md5'] 	= self.store_file(page_source, False, 'page_source')

			if self.debug: print('going to do reading ease scores')
			# get readability scores, scores below zero are
			#	invalid so we null them
			policy['fre_score'] = textstat.flesch_reading_ease(page_text)
			if policy['fre_score'] <= 0:
				policy['fre_score'] = None

			policy['fk_score']  = textstat.flesch_kincaid_grade(page_text)
			if policy['fk_score'] <= 0:
				policy['fk_score'] = None

			if self.debug: print('going to store policy')
			# add to db and get id for this policy
			policy_id  = self.sql_driver.add_policy(policy)

			if self.debug: print('going to link policy to pages')
			# attach policy to all links with this url, not we can filter
			#	do only do internal links
			for page_id, crawl_id in self.sql_driver.get_page_ids_from_link_url(policy['start_url'],internal_links_only=True):
				self.sql_driver.attach_policy_to_page(policy_id,page_id)
				self.sql_driver.attach_policy_to_crawl(policy_id,crawl_id)

			if self.debug: 
				print(f'\t👍 Success: {policy["start_url"]}')
			self.sql_driver.close()
			return {'success': True}
		else:
			if self.debug: 
				print(f'\t👎 Fail: {policy["start_url"]}')
			self.sql_driver.close()
			return {
				'success': False,
				'result': 'Not policy'
			}
	# store_policy

	def determine_policy_type_from_text(self, text):
		"""
		Determine if a given text fragment indicates
			a given type of policy.

		Returns dict.

		"""

		# clear whitespace
		text = re.sub('\s+',' ',text)

		# retrieve values from policy_terms.json
		policy_verification_terms = self.utilities.get_policy_verification_terms()

		policy_type_keys = []
		for key in policy_verification_terms:
			policy_type_keys.append(key)

		# randomize the order we do our checks
		random.shuffle(policy_type_keys)

		# look for matches against verification terms
		for policy_type in policy_type_keys:
			for term in policy_verification_terms[policy_type]:
				if term in text.lower():
					return({
						'success': True,
						'result' :{
							'policy_type':	policy_type,
							'match_term':	term,
							'match_text':	text
						}
					})

		# no match
		return ({'success': False})
	# determine_policy_type_from_text

	def store_page_text(self,readability_html,readability_source_md5):
		# the actual 'page_text' output from readability doesn't properly seperate words
		#	that use markup as a space.  eg '<h3>this</h3><p>that</p>' becomes 'thisthat'
		#	whereas 'this that' is what a user would see in the browser
		# to overcome the above issue we have to manually strip out html and do some 
		#	cleaning of our own.
		page_text = re.sub('<!--.+-->',' ', readability_html)
		page_text = re.sub('<svg.+</svg>',' ', page_text)
		page_text = re.sub('<.+?>', ' ', page_text)
		page_text = re.sub('[\n|\r]', ' ', page_text)
		page_text = re.sub('\s+', ' ', page_text)
		page_text = unicodedata.normalize('NFKD',html.unescape(page_text.strip()))

		# postgres can't handle nulls
		page_text = page_text.replace('\x00','NULL_REPLACED_FOR_PSQL')

		# return the id
		return self.sql_driver.add_page_text({
			'text'						: page_text.replace('\x00',' '),
			'word_count'				: len(page_text.split()),
			'readability_source_md5' 	: readability_source_md5
		})
	# store_page_text

# OutputStore
