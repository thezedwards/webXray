# standard python libs
import os
import re
import json
import hashlib
import urllib.request
from urllib.parse import urlparse

# custom webxray classes
from webxray.ParseURL import ParseURL
from webxray.Utilities import Utilities

class OutputStore:
	"""	
		This class receives data from the browser, processes it, and stores it in the db
	"""

	def __init__(self, db_engine, db_name):
		self.db_engine	= db_engine
		self.db_name	= db_name
		self.utilities	= Utilities()
		self.url_parser = ParseURL()
	# init

	def store(self, url, browser_output, store_source=False, store_1p=True, get_file_hashes=False, hash_3p_only=False):
		"""
		this is the primary function of this class,
		
		it takes the url of the given page and the request and cookie data generated
			by the browser

		data is cleaned up with some minor analysis (eg file types) and stored 
			for later in-depth analysis.
		
		there is an option to store first party requests as well as third, turned on by default
			to save disk space turn off store_1p

		there is also an option to get file hashes, this introduces serious overhead
			and is turned off by default
		"""

		# open up a sql connection
		if self.db_engine == 'mysql':
			from webxray.MySQLDriver import MySQLDriver
			sql_driver = MySQLDriver(self.db_name)
		elif self.db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			sql_driver = SQLiteDriver(self.db_name)
		elif self.db_engine == 'postgres':
			from webxray.PostgreSQLDriver import PostgreSQLDriver
			sql_driver = PostgreSQLDriver(self.db_name)
		else:
			print('INVALED DB ENGINE FOR %s, QUITTING!' % db_engine)
			exit()

		# get the ip, fqdn, domain, pubsuffix, and tld
		# we need the domain to figure out if cookies/elements are third-party
		origin_ip_fqdn_domain_pubsuffix_tld	= self.url_parser.get_ip_fqdn_domain_pubsuffix_tld(url)

		# if we can't get page domain info we fail gracefully
		if origin_ip_fqdn_domain_pubsuffix_tld is None:
			sql_driver.log_error(url, 'Could not parse TLD for %s' % url)
			return False

		origin_ip 			= origin_ip_fqdn_domain_pubsuffix_tld[0]
		origin_fqdn 		= origin_ip_fqdn_domain_pubsuffix_tld[1]
		origin_domain 		= origin_ip_fqdn_domain_pubsuffix_tld[2]
		origin_pubsuffix 	= origin_ip_fqdn_domain_pubsuffix_tld[3]
		origin_tld 			= origin_ip_fqdn_domain_pubsuffix_tld[4]
		
		# sql_driver.add_domain both stores the new domain and returns its db row id
		# if it is already in db just return the existing id
		page_domain_id = sql_driver.add_domain(origin_ip, origin_fqdn, origin_domain, origin_pubsuffix, origin_tld)

		# figure out the privacy policy url and text, starts null
		priv_policy_url = None
		priv_policy_url_text = None

		# read in our list of privacy link terms from the json file in webxray/resources/policyxray
		privacy_policy_term_list = self.utilities.get_privacy_policy_term_list()

		# we reverse links return from browser to check footer links first as that is where policy links tend to be
		all_links = browser_output['all_links']
		all_links.reverse()

		# if we have links search for privacy policy
		if len(all_links) > 0:
			# links are tuple
			for link_text,link_url in all_links:
				# makes sure we have text, skip links without
				if link_text:
					# need lower for string matching
					link_text = link_text.lower().strip()
					# not a link we can use
					if 'javascript' in link_text: continue
					# see if the link_text is in our term list
					if link_text in privacy_policy_term_list:
							# if the link_url is relative this will convert to absolute
							priv_policy_url = self.utilities.get_absolute_url_from_page_link(url,link_url)
							priv_policy_url_text = link_text
							break

		# if the final page is https (often after a redirect), mark it appropriately
		if browser_output['final_url'][:5] == 'https':
			page_is_ssl = True
		else:
			page_is_ssl = False

		if store_source:
			# handles issue where postgres will crash on inserting null character
			source = browser_output['source'].replace('\x00',' ')
		else:
			source = None

		# add page
		page_id = sql_driver.add_page(
			browser_output['browser_type'],
			browser_output['browser_version'],
			browser_output['browser_wait'],
			browser_output['title'],
			browser_output['meta_desc'],
			url, 
			browser_output['final_url'],
			priv_policy_url,
			priv_policy_url_text,
			page_is_ssl,
			source,
			browser_output['load_time'],
			page_domain_id
		)

		# store cookies
		for cookie in browser_output['cookies']:
			# get the ip, fqdn, domain, pubsuffix, and tld
			# we need the domain to figure out if cookies/elements are third-party
			# note:
			#	url_parser fails on non-http, we should fix this, right now a lame hack is to prepend http://
			cookie_ip_fqdn_domain_pubsuffix_tld	= self.url_parser.get_ip_fqdn_domain_pubsuffix_tld('http://'+cookie['domain'])
			
			# something went wrong, log and fail gracefully
			if cookie_ip_fqdn_domain_pubsuffix_tld is None:
				sql_driver.log_error(url, 'Error parsing cookie with domain: '+cookie['domain'])
				continue

			# otherwise, everything went fine
			cookie_ip 			= cookie_ip_fqdn_domain_pubsuffix_tld[0]
			cookie_fqdn 		= cookie_ip_fqdn_domain_pubsuffix_tld[1]
			cookie_domain 		= cookie_ip_fqdn_domain_pubsuffix_tld[2]
			cookie_pubsuffix 	= cookie_ip_fqdn_domain_pubsuffix_tld[3]
			cookie_tld 			= cookie_ip_fqdn_domain_pubsuffix_tld[4]

			# mark third-party cookies
			if origin_domain != cookie_domain:
				is_3p_cookie = True
			else:
				is_3p_cookie = False

			# this is a first party cookie, see if we want to store it
			if is_3p_cookie is False and store_1p is False:
				continue

			# sql_driver.add_domain both stores the new domain and returns its id
			cookie_domain_id = sql_driver.add_domain(cookie_ip, cookie_fqdn, cookie_domain, cookie_pubsuffix, cookie_tld)
		
			# name and domain are required, so if they fail we just continue
			try: name = cookie['name']
			except: continue
		
			try: domain = cookie_domain
			except: continue
		
			# these are optional, fill with null values if fail
			try: secure = cookie['secure']
			except: secure = None
		
			try: path = cookie['path']
			except: path = None
		
			try: httponly = cookie['httponly']
			except: httponly = None
		
			try: expiry = cookie['expiry']
			except: expiry = None
		
			try: value = cookie['value']
			except: value = None
		
			# all done with this cookie
			sql_driver.add_cookie(
				page_id,
				name, secure, path, domain, 
				httponly, expiry, value, 
				is_3p_cookie, cookie_domain_id
			)

		# process requests now
		for request in browser_output['processed_requests']:
			# if the request starts with the following we can't parse anyway, so skip
			if re.match('^(data|about|chrome|blob).+', request):
				continue

			# get the ip, fqdn, domain, pubsuffix, and tld
			# we need the domain to figure out if cookies/elements are third-party
			element_ip_fqdn_domain_pubsuffix_tld	= self.url_parser.get_ip_fqdn_domain_pubsuffix_tld(request)

			# problem with this request, log and fail gracefully
			if element_ip_fqdn_domain_pubsuffix_tld is None:
				sql_driver.log_error(url, 'Error parsing element request: '+request)
				continue

			element_ip 			= element_ip_fqdn_domain_pubsuffix_tld[0]
			element_fqdn 		= element_ip_fqdn_domain_pubsuffix_tld[1]
			element_domain 		= element_ip_fqdn_domain_pubsuffix_tld[2]
			element_pubsuffix 	= element_ip_fqdn_domain_pubsuffix_tld[3]
			element_tld 		= element_ip_fqdn_domain_pubsuffix_tld[4]

			# sql_driver.add_domain both stores the new domain and returns its db row id
			element_domain_id = sql_driver.add_domain(element_ip, element_fqdn, element_domain, element_pubsuffix, element_tld)

			# mark third-party elements based on domain
			if origin_domain != element_domain:
				is_3p_element = True
			else:
				is_3p_element = False

			# if we are not storing 1p elements continue
			if is_3p_element is False and store_1p is False:
				continue
			
			if request[:5] == 'https' or request[:3] == 'wss':
				element_is_ssl = True
			else:
				element_is_ssl = False

			try:
				received = browser_output['processed_requests'][request]['received']
			except:
				received = None

			# get domain of referer and determine if page leaked by referer
			try:
				referer = browser_output['processed_requests'][request]['referer']
			except:
				referer = None

			if referer and len(referer) != 0:
				referer_ip_fqdn_domain_pubsuffix_tld = self.url_parser.get_ip_fqdn_domain_pubsuffix_tld(referer)

				if referer_ip_fqdn_domain_pubsuffix_tld:
					if referer_ip_fqdn_domain_pubsuffix_tld[2] == origin_domain:
						page_domain_in_referer = True
					else:
						page_domain_in_referer = False
				else:
					page_domain_in_referer = None
					sql_driver.log_error(url, 'Error parsing referer header: '+referer)
			else:
				page_domain_in_referer = None

			try:
				start_time_offset = browser_output['processed_requests'][request]['start_time_offset']
			except:
				start_time_offset = None

			try:
				load_time = browser_output['processed_requests'][request]['load_time']
			except:
				load_time = None

			try:
				status = browser_output['processed_requests'][request]['status']
			except:
				status = None

			try:
				status_text = browser_output['processed_requests'][request]['status_text']
			except:
				status_text = None

			try:
				content_type = browser_output['processed_requests'][request]['content_type']
			except:
				content_type = None
			
			try:
				body_size = browser_output['processed_requests'][request]['body_size']
			except:
				body_size = None

			try:
				request_headers = str(browser_output['processed_requests'][request]['request_headers'])
			except:
				request_headers = None

			try:
				response_headers = str(browser_output['processed_requests'][request]['response_headers'])
			except:
				response_headers = None

			# consider anything before the "?" to be the element_url
			try:
				element_url = re.search('^(.+?)\?.+$', request).group(1)
			except:
				element_url = request

			# consider anything after the "?" to be the args
			try:
				element_args = re.search('^.+(\?.+)$', request).group(1) # start url args
			except:
				element_args = None

			# attempt to parse off the extension
			try:
				element_extension = re.search('\.([0-9A-Za-z]+)$', element_url).group(1).lower()
			except:
				element_extension = None
			
			# lists of common extensions, can be expanded
			image_extensions 	= ['png', 'jpg', 'jpgx', 'jpeg', 'gif', 'svg', 'bmp', 'tif', 'tiff', 'webp', 'srf']
			script_extensions 	= ['js', 'javascript']
			data_extensions 	= ['json', 'jsonp', 'xml']
			font_extentions 	= ['woff', 'ttf', 'otf']
			static_extentions 	= ['html', 'htm', 'shtml']
			dynamic_extentions	= ['php', 'asp', 'jsp', 'aspx', 'ashx', 'pl', 'cgi', 'fcgi']

			# figure out what type of element it is
			if element_extension in image_extensions:
				element_type = 'image'
			elif element_extension in script_extensions:
				element_type = 'javascript'
			elif element_extension in data_extensions:
				element_type = 'data_structured'
			elif element_extension == 'css':
				element_type = 'style_sheet'
			elif element_extension in font_extentions:
				element_type = 'font'
			elif element_extension in static_extentions:
				element_type = 'page_static'
			elif element_extension == dynamic_extentions:
				element_type = 'page_dynamic'
			elif element_extension == 'swf' or element_extension == 'fla':
				element_type = 'Shockwave Flash'
			else:
				element_type = None

			# file hashing has non-trivial overhead and off by default
			#
			# what this does is uses the same ua/referer as the actual request
			# 	so we are just replaying the last one to get similar response
			# 	note that we aren't sending the same cookies so that could be an issue
			# 	otherwise it is equivalent to a page refresh in theory

			# option to hash only 3p elements observed here
			if (get_file_hashes and hash_3p_only and is_3p_element) or (get_file_hashes and hash_3p_only == False):
				replay_element_request = urllib.request.Request(
					request,
					headers = {
						'User-Agent' : browser_output['processed_requests'][request]['user_agent'],
						'Referer' : referer,
						'Accept' : '*/*'
					}
				)
				try:
					file_md5 = hashlib.md5(urllib.request.urlopen(replay_element_request,timeout=10).read()).hexdigest()
				except:
					file_md5 = None
			else:
				file_md5 = None

			# final tasks is to truncate the request if it is 
			#	over 2k characters as it is likely
			#	binary data and may cause problems inserting
			#	into TEXT fields in database
			#
			#  TODO:
			#	better handle binary data in general
			if len(request) >= 2000: request = request[:2000]
			if len(element_url) >= 2000: element_url = element_url[:2000]

			# store request
			sql_driver.add_element(
				page_id,
				request, element_url,
				is_3p_element, element_is_ssl,
				received,
				referer,
				page_domain_in_referer,
				start_time_offset,
				load_time,
				status,
				status_text,
				content_type,
				body_size,
				request_headers,
				response_headers,
				file_md5,
				element_extension,
				element_type,
				element_args,
				element_domain_id
			)

		# close db connection
		sql_driver.close()

		return True
	# store
# OutputStore
