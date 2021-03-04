# standard python libraries
import os
import json
import datetime
import statistics
import collections

# custom libraries
from webxray.Utilities import Utilities

class Analyzer:
	"""
	This class performs analysis of our data.
	"""

	def __init__(self,db_name,db_engine):

		# set up global db connection
		if db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			self.sql_driver = SQLiteDriver(db_name)
		elif db_engine == 'postgres':
			from webxray.PostgreSQLDriver import PostgreSQLDriver
			self.sql_driver = PostgreSQLDriver(db_name)
		else:
			print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
			quit()

		# these gets reused frequently, minimize db calls by doing it up here
		self.total_pages 	= self.sql_driver.get_complex_page_count()
		self.total_crawls 	= self.sql_driver.get_crawl_count()

		# pass utilities the database info
		self.utilities = Utilities(db_name,db_engine)

		# initialize the domain owner dict
		self.domain_owners = self.utilities.get_domain_owner_dict()

		# load to memory for faster processing, make sure you
		#	have enough RAM!
		self.get_crawl_id_to_3p_domain_info()
	# __init__

	def get_crawl_id_to_3p_domain_info(self):
		"""
		Many operations needed to access a mapping of crawl_ids to the
			domain name and domain_owner_ids of all types of data
			(requests, responses, cookies, and websockets).  To save
			db calls we set up a massive dictionary once to be reused
			later.
		"""

		print('\tFetching crawl 3p domain lookup info...', end='', flush=True)

		# this is a class global
		self.crawl_id_to_3p_domain_info = {}
		for crawl_id,domain,domain_owner_id in self.sql_driver.get_crawl_id_3p_domain_info():
			if crawl_id not in self.crawl_id_to_3p_domain_info:
				self.crawl_id_to_3p_domain_info[crawl_id] = [{'domain':domain,'owner_id':domain_owner_id}]
			else:
				self.crawl_id_to_3p_domain_info[crawl_id] = self.crawl_id_to_3p_domain_info[crawl_id] + [{'domain':domain,'owner_id':domain_owner_id}]

		print('done!')
	# get_crawl_id_to_3p_domain_info

	def patch_domain_owners(self):
		"""
		in order to analyze what entities receive user data, we need to update
		  the database with domain ownership records we have stored previously
		"""

		# temporary
		return

		# we first clear out what is the db in case the new data has changed, 
		# 	on big dbs takes a while
		print('\tFlushing extant domain owner data...', end='', flush=True)
		self.sql_driver.reset_domain_owners()
		print('done!')

		# next we pull the owner/domain pairings from the json file in 
		# 	the resources dir and add to the db
		print('\tPatching with new domain owner data...', end='', flush=True)
		domain_owner_data = json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/domain_owners/domain_owners.json', 'r', encoding='utf-8'))
		for item in domain_owner_data:
			# skipping for now, but perhaps find a way to enter this in db?
			if 'revision_date' in item: continue

			self.sql_driver.add_domain_owner(
				item['id'], 
				item['parent_id'],
				item['name'],
				json.dumps(item['aliases']),
				item['homepage_url'],
				json.dumps(item['site_privacy_policy_urls']),
				json.dumps(item['service_privacy_policy_urls']),
				json.dumps(item['gdpr_statement_urls']),
				json.dumps(item['terms_of_use_urls']),
				json.dumps(item['platforms']),
				json.dumps(item['uses']),
				item['notes'], 
				item['country']
			)

			for domain in item['domains']:
				self.sql_driver.update_domain_owner(item['id'], domain)

		# update the domain owner dict
		self.domain_owners = self.utilities.get_domain_owner_dict()

		print('done!')
	# patch_domain_owners

	def get_top_tlds(self, limit):
		"""
		finds the most common tlds from all the pages
		type is default to tld, but pubsuffix also works

		returns list of tlds
		"""

		# first we put all the tlds for each page into a list
		tlds = []
		for row in self.sql_driver.get_all_tlds():
			tlds.append(row[0])

		# use this to hold the top tlds
		# it starts with "None" as that means we process all the pages
		top_tlds = [None]

		# set up a global var which has the counts for each tld
		self.page_counts_by_tld = {}
		
		# cut the list to the limit to return only top tlds
		for tld,count in collections.Counter(tlds).most_common()[0:limit]:
			top_tlds.append(tld)
			self.page_counts_by_tld[tld] = count
		
		return top_tlds
	# get_top_tlds

	def get_per_crawl_3p_domain_counts(self, tld_filter = None):
		"""
		determines basic stats for the number of 3p domains contacted per-crawl
		
		note this is distinct domain+pubsuffix, not fqdns (e.g. 'sub.example.com' 
			and sub2.example.com' only count as 'example.com')
		"""

		# now we determine the number of domains each page is connected to by looking at len of list of 3p domains
		per_crawl_3p_request_counts = []
		for crawl_id,count in self.sql_driver.get_crawl_3p_domain_counts():
			per_crawl_3p_request_counts.append(count)

		# crawls that have no 3p requests are not yet in our counts
		# 	so for all uncounted pages we add in zeros
		uncounted_crawls = self.total_crawls - len(per_crawl_3p_request_counts)
		for i in range(0,uncounted_crawls):
			per_crawl_3p_request_counts.append(0)

		return per_crawl_3p_request_counts
	# get_per_crawl_3p_domain_counts

	def get_3p_domain_distribution(self, tld_filter=None):
		"""
		Determines the number of pages which have a given number of 3p domains.
		"""
		per_crawl_3p_request_counts = self.get_per_crawl_3p_domain_counts()
		domain_count_to_page_count = collections.Counter(per_crawl_3p_request_counts)
		domain_count_to_page_distribution = {}
		max_value = 0
		for domain_count in domain_count_to_page_count:
			domain_count_to_page_distribution[domain_count] = domain_count_to_page_count[domain_count]
			if domain_count > max_value:
				max_value = domain_count
		
		full_dist = []
		for domain_count in range(max_value+1):
			if domain_count in domain_count_to_page_distribution:
				full_dist.append({
					'domain_count': domain_count,
					'page_count':	domain_count_to_page_distribution[domain_count]
				})
			else:
				full_dist.append({
					'domain_count': domain_count,
					'page_count':	0
				})

		return full_dist
	# get_3p_domain_distribution

	def get_3p_cookie_distribution(self, tld_filter=None):
		"""
		Determines the number of pages which have a given number of cookies.
		"""
		per_page_3p_cookie_counts = self.get_per_crawl_3p_cookie_counts(tld_filter)
		cookie_count_to_page_count = collections.Counter(per_page_3p_cookie_counts)
		cookie_count_to_page_distribution = {}
		max_value = 0
		for cookie_count in cookie_count_to_page_count:
			cookie_count_to_page_distribution[cookie_count] = cookie_count_to_page_count[cookie_count]
			if cookie_count > max_value:
				max_value = cookie_count
		
		full_dist = []
		for cookie_count in range(max_value+1):
			if cookie_count in cookie_count_to_page_distribution:
				full_dist.append({
					'cookie_count': cookie_count,
					'page_count':	cookie_count_to_page_distribution[cookie_count]
				})
			else:
				full_dist.append({
					'cookie_count': cookie_count,
					'page_count':	0
				})

		return full_dist
	# get_3p_cookie_distribution

	def get_3p_domain_stats(self, tld_filter=None):
		"""
		Returns high-level 3p domain stats.
		"""

		# this is the data we will be getting stats for
		per_crawl_3p_request_counts = self.get_per_crawl_3p_domain_counts(tld_filter)

		# mean and median should always be ok
		mean 	= statistics.mean(per_crawl_3p_request_counts)
		median 	= statistics.median(per_crawl_3p_request_counts)

		# but mode can throw an error, so catch here
		try:
			mode = statistics.mode(per_crawl_3p_request_counts)
		except:
			mode = None

		return({
			'mean': 	mean, 
			'median':	median, 
			'mode':		mode
		})
	# get_3p_domain_stats

	def get_per_crawl_3p_cookie_counts(self, tld_filter = None):
		"""
		determines basic stats for the number of 3p cookies contacted per-crawl
			note that a single 3p many set more than one cookie
		"""
		# each page id corresponds to a list of cookie ids
		crawl_id_to_unique_cookies = {}

		# run query to get all page id, 3p cookie id, 3p cookie domain entries
		for crawl_id,cookie_name,cookie_domain in self.sql_driver.get_crawl_id_3p_cookie_id_3p_cookie_domain(tld_filter):
			# if the page id is not yet seen enter the current cookie id as a fresh list
			#	otherwise, we add to the existing list
			if crawl_id not in crawl_id_to_unique_cookies:
				crawl_id_to_unique_cookies[crawl_id] = [(cookie_name,cookie_domain)]
			else:
				if (cookie_name,cookie_domain) not in crawl_id_to_unique_cookies[crawl_id]:
					crawl_id_to_unique_cookies[crawl_id] = crawl_id_to_unique_cookies[crawl_id] + [(cookie_name,cookie_domain)]

		# determine the number of 3p cookies each crawl has by looking at len of list of cookies
		per_crawl_3p_cookie_counts = []
		for crawl_id in crawl_id_to_unique_cookies:
			per_crawl_3p_cookie_counts.append(len(crawl_id_to_unique_cookies[crawl_id]))

		# crawls that have no 3p cookies are not yet in our counts
		# 	so for all uncounted crawls we add in zeros
		uncounted_crawls = self.total_crawls - len(per_crawl_3p_cookie_counts)
		for i in range(0,uncounted_crawls):
			per_crawl_3p_cookie_counts.append(0)

		return per_crawl_3p_cookie_counts
	# get_per_crawl_3p_cookie_counts

	def get_3p_cookie_stats(self,tld_filter=None):
		"""
		Returns high-level cookie stats.
		"""

		# this is the data we will be getting stats for
		per_page_3p_cookie_counts = self.get_per_crawl_3p_cookie_counts(tld_filter)

		# mean and median should always be ok
		mean 	= statistics.mean(per_page_3p_cookie_counts)
		median 	= statistics.median(per_page_3p_cookie_counts)

		# but mode can throw an error, so catch here
		try:
			mode = statistics.mode(per_page_3p_cookie_counts)
		except:
			mode = None

		return({
			'mean': 	mean, 
			'median':	median, 
			'mode':		mode
		})
	# get_3p_cookie_stats

	def get_db_summary(self):
		"""
		Get basic data about what is in our database.
		"""

		# some of these take longer than others
		total_tasks_fail 			= self.sql_driver.get_pending_task_count()
		total_tasks_attempted 		= self.total_crawls + total_tasks_fail
		percent_tasks_ok 			= (self.total_crawls/total_tasks_attempted)*100
		total_errors 				= self.sql_driver.get_total_errors_count()
		total_cookies 				= self.sql_driver.get_total_cookie_count()
		total_3p_cookies 			= self.sql_driver.get_total_cookie_count(is_3p = True)
		total_dom_storage			= self.sql_driver.get_dom_storage_count()
		total_websockets			= self.sql_driver.get_websocket_count()
		total_websocket_events		= self.sql_driver.get_websocket_event_count()
		total_requests				= self.sql_driver.get_total_request_count()
		total_responses 			= self.sql_driver.get_total_response_count()
		total_requests_received 	= self.sql_driver.get_total_request_count(received = True)
		percent_requests_received 	= (total_requests_received/total_requests)*100
		total_3p_requests			= self.sql_driver.get_total_request_count(party='third')
		total_3p_responses			= self.sql_driver.get_total_response_count(is_3p = True)
		
		# avoid divide-by-zero
		if total_3p_requests > 0:
			total_3p_requests_received 	= self.sql_driver.get_total_request_count(received = True, party='third')
			percent_3p_requests_received = (total_3p_requests_received/total_3p_requests)*100
		else:
			percent_3p_requests_received = 0
		
		# ship it back
		return({
			'total_crawls_ok'				: self.total_crawls,
			'total_pages_ok'				: self.total_pages,
			'total_tasks_fail'				: total_tasks_fail,
			'total_tasks_attempted'			: total_tasks_attempted,
			'percent_tasks_ok'				: percent_tasks_ok,
			'total_errors'					: total_errors,
			'total_cookies'					: total_cookies,
			'total_3p_cookies'				: total_3p_cookies,
			'total_dom_storage'				: total_dom_storage,
			'total_websockets'				: total_websockets,
			'total_websocket_events'		: total_websocket_events,
			'total_requests'				: total_requests,
			'total_responses'				: total_responses,
			'percent_requests_received'		: percent_requests_received,
			'total_3p_requests'				: total_3p_requests,
			'total_3p_responses'			: total_3p_responses,
			'percent_3p_requests_received'	: percent_3p_requests_received,
		})
	# get_db_summary

	def get_high_level_stats(self, tld_filter=None):
		"""
		Get high level stats about what we found.
		"""

		crawls_w_3p_req 		= self.sql_driver.get_crawl_w_3p_req_count()
		percent_w_3p_request 	= (crawls_w_3p_req/self.total_crawls)*100
		total_crawls_cookies 	= self.sql_driver.get_crawl_w_3p_cookie_count()
		percent_w_3p_cookie 	= (total_crawls_cookies/self.total_crawls)*100
		crawls_w_3p_script 		= self.sql_driver.get_crawl_w_3p_script_count()
		percent_w_3p_script		= (crawls_w_3p_script/self.total_crawls)*100
		total_pages_ssl 		= self.sql_driver.get_ssl_page_count()
		percent_pages_ssl		= (total_pages_ssl/self.total_pages)*100

		# request info
		total_requests_received 		= self.sql_driver.get_total_request_count(received = True)
		total_requests_received_ssl		= self.sql_driver.get_total_request_count(received = True, is_ssl = True)

		total_requests_received_1p 		= self.sql_driver.get_total_request_count(received = True, party='first')
		total_requests_received_1p_ssl	= self.sql_driver.get_total_request_count(received = True, party='first', is_ssl = True)

		total_requests_received_3p 		= self.sql_driver.get_total_request_count(received = True, party='third')
		total_requests_received_3p_ssl	= self.sql_driver.get_total_request_count(received = True, party='third', is_ssl = True)

		# ssl
		if total_requests_received > 0:
			percent_requests_ssl 	= (total_requests_received_ssl/total_requests_received)*100
			percent_1p_requests_ssl	= (total_requests_received_1p_ssl/total_requests_received_1p)*100
		else:
			percent_requests_ssl 	= 0
			percent_1p_requests_ssl	= 0

		if total_requests_received_3p:
			percent_3p_requests_ssl	= (total_requests_received_3p_ssl/total_requests_received_3p)*100
		else:
			percent_3p_requests_ssl	= 0

		# load time is seconds
		average_page_load_time = self.sql_driver.get_page_ave_load_time()

		# domains and cookies
		domain_stats	= self.get_3p_domain_stats(tld_filter)
		cookie_stats 	= self.get_3p_cookie_stats(tld_filter)

		return ({
			'total_crawls'					: self.total_crawls,
			'total_pages'					: self.total_pages,
			'percent_pages_ssl'				: percent_pages_ssl,
			'total_requests_received'		: total_requests_received,
			'percent_requests_ssl'			: percent_requests_ssl,
			'total_requests_received_1p'	: total_requests_received_1p,
			'percent_1p_requests_ssl'		: percent_1p_requests_ssl,
			'total_requests_received_3p'	: total_requests_received_3p,
			'percent_3p_requests_ssl'		: percent_3p_requests_ssl,
			'average_page_load_time'		: average_page_load_time,
			'percent_w_3p_request'			: percent_w_3p_request,
			'percent_w_3p_cookie'			: percent_w_3p_cookie,
			'percent_w_3p_script'			: percent_w_3p_script,
			'3p_domains_mean'				: domain_stats['mean'],
			'3p_domains_median'				: domain_stats['median'],
			'3p_domains_mode'				: domain_stats['mode'],
			'3p_cookies_mean'				: cookie_stats['mean'],
			'3p_cookies_median'				: cookie_stats['median'],
			'3p_cookies_mode'				: cookie_stats['mode'],
		})
	# get_high_level_stats

	def get_aggregated_tracking_attribution(self, tld_filter=None):
		"""
		generates ranked list of which entities collect data 
			from the greatest number of crawls

		- entities which have subsidiaries are ranked according 
			to the crawls their subsidiaries get data from as well
		- however, parent entities only get one hit on 
			a crawl which has multiple subsidiaries present
		- for example, if a crawl has 'google analytics' and 'doubleclick' 
			that is only one hit for 'google'

		"""

		# list will have entries for each hit on a given entity
		all_owner_occurances = []

		# each crawl_id is a key which corresponds to a list of 
		#	ids for entities which own the 3p domains
		crawl_to_3p_owners = {}

		# iterate through the entire set of 3p domains for each
		#	crawl
		for crawl_id in self.crawl_id_to_3p_domain_info:

			# this is a set so items which appear more than once only get counted once
			# reset this for each crawl
			crawl_domain_owners = set()

			for item in self.crawl_id_to_3p_domain_info[crawl_id]:
				if item['owner_id']:
					for lineage_id in self.utilities.get_domain_owner_lineage_ids(item['owner_id']):
						crawl_domain_owners.add(lineage_id)

			# we have finished processing for this crawl so we add the owner ids to the full list
			for owner_id in crawl_domain_owners:
				all_owner_occurances.append(owner_id)

		# return a list of dicts
		ranked_aggregated_tracking_attribution = []
		for owner_id, total_crawl_occurances in collections.Counter(all_owner_occurances).most_common():
			ranked_aggregated_tracking_attribution.append({
				'owner_id':			owner_id,
				'owner_name':		self.domain_owners[owner_id]['owner_name'],
				'owner_country':	self.domain_owners[owner_id]['country'],
				'percent_crawls':	(total_crawl_occurances/self.total_crawls)*100,
			})

		return ranked_aggregated_tracking_attribution

		# # get the crawl count for each domain + its children
		# domain_owner_to_crawl_count = {}
		# for domain_owner_id in self.domain_owners:
		# 	# this it the owner + children
		# 	domain_owner_id_list = [domain_owner_id]+self.utilities.get_domain_owner_child_ids(domain_owner_id)
		# 	domain_owner_to_crawl_count[domain_owner_id] = self.sql_driver.get_crawl_count_by_domain_owners(domain_owner_id_list)
		
		# # now figure out the ranking		
		# domain_owners_ranked_high_low = []
		# for domain_owner_id, count in sorted(domain_owner_to_crawl_count.items(), key=lambda item: item[1],reverse=True):
		# 	domain_owners_ranked_high_low.append(domain_owner_id)

		# # return a list of dicts
		# ranked_aggregated_tracking_attribution = []
		# for domain_owner_id in domain_owners_ranked_high_low:
		# 	ranked_aggregated_tracking_attribution.append({
		# 		'owner_id':			domain_owner_id,
		# 		'owner_name':		self.domain_owners[domain_owner_id]['owner_name'],
		# 		'owner_country':	self.domain_owners[domain_owner_id]['country'],
		# 		'percent_crawls':	(domain_owner_to_crawl_count[domain_owner_id]/self.total_crawls)*100,
		# 	})

		# return ranked_aggregated_tracking_attribution
	# get_aggregated_tracking_attribution

	def get_aggregated_3p_ssl_use(self, tld_filter=None):
		"""
		For each request where we know the owner we determine if it is SSL,
			then we figure out the aggregated (owner+children) SSL
			usage percentage
		"""

		# do processing here
		owner_id_ssl_use = {}

		# we iterate over every received request
		# this is a potentially large query b/c we must look at each request on the page
		# since a single domain owner may have more than one requests and these may or may not be with ssl
		for domain,domain_owner_id,is_ssl in self.sql_driver.get_3p_request_domain_owner_id_ssl_use(tld_filter):
			for domain_owner_id in self.utilities.get_domain_owner_lineage_ids(domain_owner_id):
				if domain_owner_id not in owner_id_ssl_use:
					owner_id_ssl_use[domain_owner_id] = [is_ssl]
				else:
					owner_id_ssl_use[domain_owner_id] = owner_id_ssl_use[domain_owner_id] + [is_ssl]

		# output list of dicts
		aggregated_3p_ssl_use = []
		for owner_id in owner_id_ssl_use:
			aggregated_3p_ssl_use.append({
				'owner_id'			: owner_id,
				'owner_name'		: self.domain_owners[owner_id]['owner_name'],
				'owner_country'		: self.domain_owners[owner_id]['country'],
				'ssl_use'			: 100*(sum(owner_id_ssl_use[owner_id])/len(owner_id_ssl_use[owner_id]))
		})

		return aggregated_3p_ssl_use
	# get_aggregated_3p_ssl_use

	def get_site_to_3p_network(self, domain_owner_is_known=False):
		"""
			sql_driver.get_network_ties returns a set of tuples in the format
			(page domain, request domain, request domain owner id)
			we just go through this data to produce the report
		"""
		network = []

		for page_domain,request_domain,request_owner_id in self.sql_driver.get_3p_network_ties():
			# if we know the owner get name and country, otherwise None
			if request_owner_id != None:
				request_owner_name 		= self.domain_owners[request_owner_id]['owner_name']
				request_owner_country	= self.domain_owners[request_owner_id]['country']
			else:
				request_owner_name 		= None
				request_owner_country	= None

			network.append({
				'page_domain'			: page_domain,
				'request_domain'		: request_domain,
				'request_owner_id'		: request_owner_id,
				'request_owner_name'	: request_owner_name,
				'request_owner_country'	: request_owner_country
			})
		return network
	# get_3p_network

	def get_page_to_3p_network(self):
		"""
		Returns the network of all pages between third-party domains.

		Additionally returns information on page redirects and owners.
		"""
		network = []

		for page_start_url,page_final_url,page_accessed,request_domain,request_owner_id in self.sql_driver.get_all_pages_3p_domains_and_owners():
			# if we know the owner get name and country, otherwise None
			if request_owner_id != None:
				request_owner_name 		= self.domain_owners[request_owner_id]['owner_name']
				request_owner_country	= self.domain_owners[request_owner_id]['country']
			else:
				request_owner_name 		= None
				request_owner_country	= None

			network.append({
				'page_start_url'		: page_start_url,
				'page_final_url'		: page_final_url,
				'page_accessed'			: page_accessed,
				'request_domain'		: request_domain,
				'request_owner_id'		: request_owner_id,
				'request_owner_name'	: request_owner_name,
				'request_owner_country'	: request_owner_country
			})
		return network
	# get_page_to_3p_network

	def get_3p_domain_percentages(self,tld_filter=None):
		"""
		Determines what percentage of crawls a given third-party domain is found on and
			owner information.
		"""

		# total crawls for this tld, used to calculate percentages
		if tld_filter:
			total_crawls = self.crawl_counts_by_tld[tld_filter]
		else:
			total_crawls = self.total_crawls

		all_3p_domains = []
		for crawl_id in self.crawl_id_to_3p_domain_info:
			for item in self.crawl_id_to_3p_domain_info[crawl_id]:
				all_3p_domains.append((item['domain'],item['owner_id']))

		domain_percentages = []
		for item, domain_crawl_count in self.utilities.get_most_common_sorted(all_3p_domains):
			domain 		= item[0]
			owner_id 	= item[1]

			# if we know the owner get name and country, otherwise None
			if owner_id != None:
				owner_name 		= self.domain_owners[owner_id]['owner_name']
				owner_country 	= self.domain_owners[owner_id]['country']
			else:
				owner_name 		= None
				owner_country 	= None

			domain_percentages.append({
				'percent_crawls': 100*(domain_crawl_count/total_crawls),
				'domain'		: domain,
				'owner_id'		: owner_id,
				'owner_name'	: owner_name,
				'owner_country'	: owner_country
			})
		return domain_percentages
	# get_3p_domain_percentages

	def get_3p_request_percentages(self,tld_filter=None,request_type=None):
		"""
		Determine what percentage of pages a given request is found on.  
		
		This is based on the "request_url" which is the url for a given request
			stripped of arguments.
			ex: "https://example.com/track.js?abc=123" would become "https://example.com/track.js"

		Additionally returns relevant owner information.
		"""

		all_3p_requests = []
		
		# total crawls for this tld, used to calculate percentages
		if tld_filter:
			total_crawls = self.crawl_counts_by_tld[tld_filter]
		else:
			total_crawls = self.total_crawls

		for page_id,request_url,request_type,request_domain,request_domain_owner in self.sql_driver.get_3p_requests(tld_filter, request_type):
			all_3p_requests.append((request_url,request_type,request_domain,request_domain_owner))

		request_percentages =[]
		
		for item, request_crawl_count in self.utilities.get_most_common_sorted(all_3p_requests):
			# if we know the owner get name and country, otherwise None
			request_owner_id = item[3]
			if request_owner_id != None:
				request_owner_name 		= self.domain_owners[request_owner_id]['owner_name']
				request_owner_country 	= self.domain_owners[request_owner_id]['country']
			else:
				request_owner_name 		= None
				request_owner_country 	= None

			request_percentages.append({
				'percent_crawls'		: 100*(request_crawl_count/total_crawls),
				'request_url'			: item[0],
				'request_type'			: item[1],
				'request_domain'		: item[2],
				'request_owner_id'		: request_owner_id,
				'request_owner_name'	: request_owner_name,
				'request_owner_country'	: request_owner_country
			})
		return request_percentages
	# get_3p_domain_percentages

	def get_3p_use_data(self,tld_filter=None):
		""""
		For some domains we know what they are used for on a first-party basis (eg marketing).
			This function examines the data we have collected in order to determine what percentage
			of crawls include a request to a third-party domain with a given use, how many
			such requests are made on a per-use basis per-crawl, and finally, what percentage
			of requests per-crawl set a third-party cookie.

		Data is returned as a dict, the first field of which is a set of all the
			uses we know of.
		"""

		# we first need to create a dict whereby each domain 
		#	corresponds to a list of known uses
		# domains with no known uses are not in the list
		#
		# IMPORTANT NOTE:
		#	some domains may have several uses!
		domain_to_use_map = {}

		# a list of all known uses
		all_uses = set()

		for domain,owner_id in self.sql_driver.get_domain_owner_ids():
			if len(self.domain_owners[owner_id]['uses']) > 0:
				domain_to_use_map[domain] = self.domain_owners[owner_id]['uses']
				for use in self.domain_owners[owner_id]['uses']:
					all_uses.add(use)

		# for each crawl, create a list of the set of domains 
		#	which set a cookie
		#
		# note that due to currently unresolved chrome issues we sometimes 
		# 	can get cookies which don't have a corresponding 3p request
		# 	this approach handles that gracefully
		crawl_cookie_domains = {}
		for crawl_id, cookie_domain in self.sql_driver.get_crawl_id_3p_cookie_domain_pairs():
			if crawl_id not in crawl_cookie_domains:
				crawl_cookie_domains[crawl_id] = [cookie_domain]
			else:
				crawl_cookie_domains[crawl_id] = crawl_cookie_domains[crawl_id] + [cookie_domain]

		# next, for each crawl we want a list of uses for domains and if
		#	that domain corresponds to a cookie being set
		# NOTE: the same use may occur many times, this is desired
		# 	as it gives us our counts later on
		crawl_3p_uses = {}

		# for crawl_id, request_domain in self.sql_driver.get_crawl_id_3p_request_domain_pairs(tld_filter):
		for crawl_id in self.crawl_id_to_3p_domain_info:
			for item in self.crawl_id_to_3p_domain_info[crawl_id]:
				domain = item['domain']

				# if this 3p domain has a known use we add it to a list of uses keyed to crawl id
				if domain in domain_to_use_map:
					# check if the domain of this request has a cookie for this crawl
					if crawl_id in crawl_cookie_domains and domain in crawl_cookie_domains[crawl_id]: 
						sets_cookie = True
					else:
						sets_cookie = False

					# add in a tuple of (use,sets_cookie) to a list for this crawl_id
					for use in domain_to_use_map[domain]:
						if crawl_id not in crawl_3p_uses:
							crawl_3p_uses[crawl_id] = [(use,sets_cookie)]
						else:
							crawl_3p_uses[crawl_id] = crawl_3p_uses[crawl_id] + [(use,sets_cookie)]

		# determine how often requests for a give use are encrypted with ssl
		# 	- note that on the same crawl multiple requests for a single use may be made
		# 		and each request may or may not be ssl
		use_ssl 	= {}
		use_total 	= {}
		total_classified = 0
		for domain,domain_owner_id,is_ssl in self.sql_driver.get_3p_request_domain_owner_id_ssl_use(tld_filter):
			# only analyze domains we know the use for
			if domain in domain_to_use_map:
				total_classified += 1
				# each domain may have several uses, add for all
				for use in domain_to_use_map[domain]:
					# increment count of ssl usage
					if is_ssl:
						if use not in use_ssl:
							use_ssl[use] = 1
						else:
							use_ssl[use] = use_ssl[use] + 1
					
					# keep track of total occurances of this use
					if use not in use_total:
						use_total[use] = 1
					else:
						use_total[use] = use_total[use] + 1

		# for each use we will produce summary counts, we 
		#	initialize everyting to zero here
		total_crawls_w_use 				= {}
		total_use_occurances 			= {}
		total_use_occurances_w_cookie 	= {}

		for use in all_uses:
			total_crawls_w_use[use] 				= 0
			total_use_occurances[use] 			= 0
			total_use_occurances_w_cookie[use] 	= 0

		# process each crawl and update the relevant counts
		for crawl_id in crawl_3p_uses:
			# we only want to count use once per-crawl, so
			#	create a set and add to it as we go along
			this_crawl_use_set = set()

			# upate the use occurance counters
			for use, has_cookie in crawl_3p_uses[crawl_id]:
				this_crawl_use_set.add(use)
				total_use_occurances[use] = total_use_occurances[use] + 1
				if has_cookie == True:
					total_use_occurances_w_cookie[use] = total_use_occurances_w_cookie[use] + 1
			
			# each use in the set adds one to the total crawl count
			for use in this_crawl_use_set:
				total_crawls_w_use[use] = total_crawls_w_use[use] + 1

		# the last step is to calculate the relevant percentages and averages

		# used to get percentage by use
		if tld_filter:
			total_crawls = self.crawl_counts_by_tld[tld_filter]
		else:
			total_crawls = self.total_crawls

		percentage_by_use 				= {}
		average_use_occurance_per_crawl 	= {}
		percentage_use_w_cookie 		= {}
		percentage_use_ssl 				= {}
		
		for use in all_uses:
			percentage_by_use[use] 				= 0
			average_use_occurance_per_crawl[use] = 0
			percentage_use_w_cookie[use] 		= 0

		for use in total_crawls_w_use:
			if total_crawls_w_use[use] > 0:
				percentage_by_use[use] 				= 100*(total_crawls_w_use[use]/total_crawls)
				average_use_occurance_per_crawl[use] = total_use_occurances[use]/total_crawls_w_use[use]
				percentage_use_w_cookie[use]		= 100*(total_use_occurances_w_cookie[use]/total_use_occurances[use])
			else:
				percentage_by_use[use] 				= None
				average_use_occurance_per_crawl[use] = None
				percentage_use_w_cookie[use]		= None

			# conditional to account for cases where no instance of a given use is ssl
			if use in use_ssl:
				percentage_use_ssl[use] 			= 100*(use_ssl[use]/use_total[use])
			else:
				percentage_use_ssl[use] 			= 0

		# send back everyting as a keyed dict
		return({
			'all_uses'							: all_uses,
			'percentage_by_use'					: percentage_by_use,
			'average_use_occurance_per_crawl'	: average_use_occurance_per_crawl,
			'percentage_use_w_cookie' 			: percentage_use_w_cookie,
			'percentage_use_ssl'				: percentage_use_ssl
			})
	# get_3p_use_data

	def get_all_pages_requests(self):
		"""
		For all pages get all of the requests associated with each page 
			load.  Default is only_3p, but this can be overridden to get
			1p as well.
		"""
		records = []
		for result in self.sql_driver.get_all_pages_requests():
			try:
				domain_owner = self.utilities.get_domain_owner_lineage_combined_string(result[4])
			except:
				domain_owner = None

			records.append({
				'accessed'				: result[0].isoformat(),
				'start_url'				: result[1],
				'final_url'				: result[2],
				'request_domain'		: result[3],
				'request_domain_owner'	: domain_owner,
				'request_url'			: result[5],
			})
		return records
	# get_all_pages_requests

	def get_all_pages_cookies(self):
		"""
		For all pages get all of the cookies associated with each page 
			load.  Default is 1p and 3p, but this can be overridden to get
			3p only.
		"""
		records = []
		for result in self.sql_driver.get_all_pages_cookies():
			try:
				cookie_owner = self.utilities.get_domain_owner_lineage_combined_string(result[4])
			except:
				cookie_owner = None

			records.append({
				'accessed'		: result[0].isoformat(),
				'start_url'		: result[1],
				'final_url'		: result[2],
				'cookie_domain'	: result[3],
				'cookie_owner'	: cookie_owner,
				'cookie_name'	: result[5],
				'cookie_value'	: result[6],
			})
		return records
	# get_all_pages_cookies

	def get_single_page_request_dump(self,page_start_url):
		"""
		For a given page (defined as unique start_url) get all of the requests associated
			with every page load.  Default is only_3p, but this can be overridden to get
			1p as well.
		"""
		records = []
		for result in self.sql_driver.get_single_page_requests(page_start_url):
			try:
				domain_owner = self.utilities.get_domain_owner_lineage_combined_string(result[6])
			except:
				domain_owner = None

			records.append({
				'page_accessed'			: result[0].isoformat(),
				'start_url'				: result[1],
				'final_url'				: result[2],
				'request_url'			: result[4],
				'request_domain'		: result[5],
				'request_domain_owner'	: domain_owner
			})
		return records
	# get_single_page_request_dump

	def get_single_page_cookie_dump(self,page_start_url):
		"""
		For a given page (defined as unique start_url) get all of the cookies associated
			with every page load.  Default is only_3p, but this can be overridden to get
			1p as well.
		"""
		records = []
		for result in self.sql_driver.get_single_page_cookies(page_start_url):
			try:
				domain_owner = self.utilities.get_domain_owner_lineage_combined_string(result[6])
			except:
				domain_owner = None

			records.append({
				#'page_accessed'			: result[0].isoformat(),
				'page_accessed'			: 'blah',
				'start_url'				: result[1],
				'final_url'				: result[2],
				'is_ssl'				: result[3],
				'cookie_domain'			: result[4],
				'cookie_name'			: result[5],
				'cookie_value'			: result[6],
				'cookie_domain_owner'	: domain_owner
			})
		return records
	# get_single_page_cookie_dump

	def update_site_hosts(self):
		"""
		For each FDQN corresponding to a page we find the
			owner of the associated ip_addr.

		"""

		# required, non-standard
		try:
			from ipwhois import IPWhois
		except:
			print('!!! UNABLE TO UPDATE SITE HOSTS, IPWHOIS NOT INSTALLED !!!')
		
		page_ips_w_no_owner = self.sql_driver.get_page_ips_w_no_owner()
		total_to_update = len(page_ips_w_no_owner)

		progress = 0
		for ip, in page_ips_w_no_owner:
			progress += 1
			print('\t\t %s of %s done' % (progress,total_to_update))

			try:
				obj = IPWhois(ip)
				result = obj.lookup_whois()
				owner = result['nets'][0]['description']
			except:
				print('fail on %s' % ip)
				pass

			# fall back
			if owner == None:
				owner = result['asn_description']

			if owner:
				# combine amazon
				# if 'Amazon' in owner:
				# 	owner = 'amazon'
				# fix strings
				owner = owner.replace('.','')
				owner = owner.replace('"','')
				owner = owner.replace("'","")
				owner = owner.replace('\n', ' ')
				owner = owner.replace('\r', ' ')
				owner = owner.replace(' ','_')
				owner = owner.replace(',','_')
				owner = owner.lower()
				self.sql_driver.update_ip_owner(ip,owner)

	# update_site_hosts

	def get_site_host_network(self):
		"""
		Return all records where we known the owner of the ip_addr
			corresponding to a given page's fqdn.
		"""
		records = []
		for site_domain,host_name in self.sql_driver.get_site_hosts():
			records.append({
				'site_domain'	: site_domain,
				'host_name'		: host_name
			})

		return records
	#get_site_hosts

	##############
	# POLICYXRAY #
	##############

	def get_policy_count(self,policy_type=None):
		"""
		For a given type of policy tells us how many we have, if
			policy_type is None we get total count.
		"""
		return self.sql_driver.get_total_policy_count(policy_type)
	# get_policy_count

	def get_average_policy_word_count(self, policy_type=None):
		"""
		Returns average policy word count, filtered by policy_type.
		"""
		return self.sql_driver.get_average_policy_word_count(policy_type=policy_type)
	# get_average_policy_word_count

	def update_readability_scores(self):
		"""
		This function performs two English-language readability tests: Flesch-Kinkaid
			grade-level and Flesch Reading Ease for any policies we haven't already 
			done.  The python textstat module handle the actual calculations.

		Note these scores are meaningless for non-English language policies.
		"""

		# non-standard lib which must be installed
		from textstat.textstat import textstat

		for policy_id, text in self.sql_driver.get_id_and_policy_text(readability_null = True):
			fre_score = textstat.flesch_reading_ease(text)
			fk_score = textstat.flesch_kincaid_grade(text)
			self.sql_driver.update_readability_scores(policy_id, fre_score, fk_score)
	# update_readability_scores

	def get_readability_scores(self, policy_type=None):
		"""
		Returns average policy word count, filtered by policy_type.
		"""
		ave_fre = self.sql_driver.get_ave_fre(policy_type=policy_type)
		ave_fkg = self.sql_driver.get_ave_fkg(policy_type=policy_type)
		return({
			'ave_fre': ave_fre,
			'ave_fkg': ave_fkg
		})
	# get_readability_scores

	def update_crawl_disclosure(self):
		"""
		REDOING THIS FOR CRAWLS
		"""
		# set up dictionaries so we can pull in the policy_id and policy_text for each page
		crawl_id_to_policy_id_text = {}
		for crawl_id, policy_id, policy_text in self.sql_driver.get_crawl_id_policy_id_policy_text():
			crawl_id_to_policy_id_text[crawl_id] = (policy_id, policy_text)

		# pull in all sets of page_id/request_owner_id we haven't analyzed yet
		for crawl_id, domain_owner_id in self.sql_driver.get_all_crawl_id_3p_request_owner_ids():
			# only process in cases we have an associated policy
			if crawl_id in crawl_id_to_policy_id_text:
				policy_id   = crawl_id_to_policy_id_text[crawl_id][0]
				policy_text = crawl_id_to_policy_id_text[crawl_id][1]
				# default values
				disclosed = False
				disclosed_owner_id = None
				# each owner may have several parent owners and aliases, we check for all of these in the policy
				for this_owner_id, this_owner_name in self.utilities.get_domain_owner_lineage_strings(domain_owner_id,get_aliases=True):
					if this_owner_name in policy_text:
						disclosed = True
						disclosed_owner_id = this_owner_id

				# done for this record, update disclosure table
				self.sql_driver.update_crawl_3p_domain_disclosure(crawl_id, domain_owner_id)
		return
	# update_crawl_disclosure

	def update_request_disclosure(self):
		"""
		For any page where we have a policy we extract all third-party request domains
			where we have determined the owner.  Next, we check if the name of the owner,
			any of it's parent companies, is in a given policy.  Note we also check based
			on "aliases" which are spelling variations on a given owner name (eg 'doubleclick'
			and 'double click').  Once we've done the checks we update the policy_request_disclosure
			table.
		"""

		# set up dictionaries so we can pull in the policy_id and policy_text for each page
		page_id_to_policy_id_text = {}
		for page_id, policy_id, policy_text in self.sql_driver.get_page_id_policy_id_policy_text():
			page_id_to_policy_id_text[page_id] = (policy_id, policy_text)

		# pull in all sets of page_id/request_owner_id we haven't analyzed yet
		for page_id, request_owner_id in self.sql_driver.get_all_page_id_3p_request_owner_ids(not_in_disclosure_table=True):
			# only process in cases we have an associated policy
			if page_id in page_id_to_policy_id_text:
				policy_id   = page_id_to_policy_id_text[page_id][0]
				policy_text = page_id_to_policy_id_text[page_id][1]
				# default values
				disclosed = False
				disclosed_owner_id = None
				# each owner may have several parent owners and aliases, we check for all of these in the policy
				for this_owner_id, this_owner_name in self.utilities.get_domain_owner_lineage_strings(request_owner_id,get_aliases=True):
					if this_owner_name in policy_text:
						disclosed = True
						disclosed_owner_id = this_owner_id

				# done for this record, update disclosure table
				self.sql_driver.update_request_disclosure(
						page_id, policy_id,
						request_owner_id, disclosed, 
						disclosed_owner_id
				)
		return
	# update_request_disclosure

	def get_percent_crawl_3p_domains_disclosed(self, policy_type=None):
		"""
		Determine the global percentage of 3p requests which are disclosed
			in policies.
		"""
		total_identified = self.sql_driver.get_total_crawl_3p_count()
		total_disclosed  = self.sql_driver.get_total_crawl_3p_disclosure_count()
		if total_identified == 0:
			return 0
		else:
			return(100*(total_disclosed/total_identified))
	# get_percent_3p_requests_disclosed

	def get_percent_3p_requests_disclosed(self, policy_type=None):
		"""
		Determine the global percentage of 3p requests which are disclosed
			in privacy policies.

		NOTE A PAGE CAN HAVE SEVERAL POLICIES WITH DISCLOSURE OCCURING IN SOME 
		BUT NOT ALL, WE SHOULD ACCOUNT FOR THIS!
		"""
		total_identified = self.sql_driver.get_total_request_disclosure_count(policy_type=policy_type)
		total_disclosed  = self.sql_driver.get_total_request_disclosure_count(policy_type=policy_type,disclosed=True)
		if total_identified == 0:
			return 0
		else:
			return(100*(total_disclosed/total_identified))
	# get_percent_3p_requests_disclosed

	def get_disclosure_by_request_owner(self):
		"""
		For each domain owner we query the policy_disclosure_table to find
			out if it or its subsidiaries have been disclosed.  This gives a very
			granular view on disclosure on a per-service basis in some cases.

		Note that this is distinct on the page id to avoid over-counting for
			subsidiaries.
		
		Returns a dict which is keyed to the owner name.
		"""
		results = {}
		for owner_id in self.domain_owners:
			child_owner_ids = self.utilities.get_domain_owner_child_ids(owner_id)
			if len(child_owner_ids) > 0:
				total 				= self.sql_driver.get_domain_owner_disclosure_count(owner_id, child_owner_ids=child_owner_ids)
				total_disclosed 	= self.sql_driver.get_domain_owner_disclosure_count(owner_id, child_owner_ids=child_owner_ids, disclosed=True)
			else:
				total 				= self.sql_driver.get_domain_owner_disclosure_count(owner_id)
				total_disclosed 	= self.sql_driver.get_domain_owner_disclosure_count(owner_id, disclosed=True)
			
			if total != 0:
				results[self.domain_owners[owner_id]['owner_name']] = (total,total_disclosed,(total_disclosed/total)*100)	

		# return the dict which can be processed to a csv in the calling class
		return results
	# get_disclosure_by_request_owner

	def get_terms_percentage(self,substrings,policy_type=None,policy_type_count=None):
		total_count = self.sql_driver.get_total_policy_count(policy_type=None)
		if policy_type:
			matches_count = self.sql_driver.get_policy_substrings_count(substrings,policy_type=policy_type)
		else:
			matches_count = self.sql_driver.get_policy_substrings_count(substrings)
		
		return (matches_count/policy_type_count)*100
	# get_terms_percentage

	def stream_rate(self):
		wait_time = 10
		elapsed = 0
		query = 'SELECT COUNT(*) FROM task_queue'
		old_count = sql_driver.fetch_query(query)[0][0]
		all_rates = []
		while True:
			time.sleep(wait_time)
			elapsed += wait_time
			new_count = sql_driver.fetch_query(query)[0][0]
			all_rates.append((old_count-new_count)*60)
			old_count = new_count
			json_data = json.dumps({
				'time': elapsed/60,
				'rate': statistics.mean(all_rates)
				# 'rate': new_count
			})
			yield f"data:{json_data}\n\n"
	# stream_rate

# Analyzer
