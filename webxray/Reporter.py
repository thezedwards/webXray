# standard python libraries
import os
import re
import csv
import json
import operator
import statistics
import collections
from operator import itemgetter

# custom libraries
from webxray.Analyzer  import Analyzer
from webxray.Utilities import Utilities

class Reporter:
	"""
	Manages the production of a number of CSV reports.
	"""

	def __init__(self, db_name, db_engine, num_tlds, num_results, tracker_threshold = None, flush_domain_owners = True, start_date = False, end_date = False):
		"""
		This performs a few start-up tasks:
			- sets up some useful global variables
			- makes sure we have a directory to store the reports
			- flushes the existing domain_owner mappings (this can be disabled)
			- if we want to do per-tld reports, figures out the most common
			- if we want to filter against a given tracker threshold, sets it 
				up here (see documentation below for tracker threshold)
		"""

		# set various global vars
		self.db_name 			= db_name
		self.num_tlds 			= num_tlds
		self.num_results 		= num_results
		self.tracker_threshold	= tracker_threshold

		# pass utilities the database info
		self.utilities 			= Utilities(db_name, db_engine)

		# set up the analyzer we will be using throughout
		self.analyzer			= Analyzer(db_name, db_engine)
		
		# number of decimal places to round to in reports
		self.num_decimals		= 2

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

		print('\t=============================')
		print('\t Checking Output Directories ')
		print('\t=============================')				
		
		# creates a new directory if it doesn't exist already
		self.report_path = self.utilities.setup_report_dir(self.db_name)

		# this is used in various places to get owner information
		self.domain_owners = self.utilities.get_domain_owner_dict()

		# if we want to get sub-reports for the most frequent tlds we find
		#	them here
		if self.num_tlds:
			print('\t=====================')
			print('\t Getting top %s tlds' % self.num_tlds)
			print('\t=====================')
			print('\t\tProcessing...', end='', flush=True)
			self.top_tlds = self.analyzer.get_top_tlds(self.num_tlds)
			print('done!')
			print('\t\tThe top tlds are:')
			for tld in self.top_tlds:
				if tld: print('\t\t |- %s' % tld)
		else:
			self.top_tlds = [None]
	# __init__

	#####################
	# REPORT GENERATORS #
	#####################

	def generate_db_summary_report(self,print_to_cli=True):
		"""
		outputs and stores report of basic data about how many records in db, etc.
		"""
		print('\t================')
		print('\t General Summary')
		print('\t================')
		
		# get the relevant db summary data
		db_summary = self.analyzer.get_db_summary()

		# print to cli
		if print_to_cli:
			print("\t\tTotal Crawls:\t\t\t%s" 					% db_summary['total_crawls_ok'])
			print("\t\tTotal Pages:\t\t\t%s" 					% db_summary['total_pages_ok'])
			print("\t\tTotal Tasks Fail:\t\t%s" 				% db_summary['total_tasks_fail'])
			print("\t\tTotal Tasks Attempted:\t\t%s" 			% db_summary['total_tasks_attempted'])
			print("\t\t%% Pages OK:\t\t\t%.2f%%" 				% db_summary['percent_tasks_ok'])
			print("\t\tTotal Errors:\t\t\t%s" 					% db_summary['total_errors'])
			print("\t\tTotal Cookies:\t\t\t%s" 					% db_summary['total_cookies'])
			print("\t\tTotal 3P Cookies:\t\t%s" 				% db_summary['total_3p_cookies'])
			print("\t\tTotal Dom Storage:\t\t%s" 				% db_summary['total_dom_storage'])
			print("\t\tTotal Websockets:\t\t%s" 				% db_summary['total_websockets'])
			print("\t\tTotal Websocket Events:\t\t%s" 			% db_summary['total_websocket_events'])
			print("\t\tTotal Requests:\t\t\t%s" 				% db_summary['total_requests'])
			print("\t\tTotal Responses:\t\t%s" 					% db_summary['total_responses'])
			print('\t\t%% Requests Received:\t\t%.2f%%' 		% db_summary['percent_requests_received'])
			print("\t\t3P Requests:\t\t\t%s" 					% db_summary['total_3p_requests'])
			print("\t\t3P Responses:\t\t\t%s" 					% db_summary['total_3p_responses'])
			print('\t\t%% 3P Requests Received:\t\t%.2f%%' 		% db_summary['percent_3p_requests_received'])
			print('\t\t'+'-'*40)

		# write results to csv
		csv_rows = []
		csv_rows.append(('total_crawls_ok',						db_summary['total_crawls_ok']))
		csv_rows.append(('total_pages_ok',						db_summary['total_pages_ok']))
		csv_rows.append(('total_tasks_fail', 					db_summary['total_tasks_fail']))
		csv_rows.append(('total_tasks_attempted', 				db_summary['total_tasks_attempted']))
		csv_rows.append(('percent_pages_ok', 					db_summary['percent_tasks_ok']))
		csv_rows.append(('total_errors', 						db_summary['total_errors']))
		csv_rows.append(('total_cookies', 						db_summary['total_cookies']))
		csv_rows.append(('total_3p_cookies', 					db_summary['total_3p_cookies']))
		csv_rows.append(('total_dom_storage', 					db_summary['total_dom_storage']))
		csv_rows.append(('total_websockets', 					db_summary['total_websockets']))
		csv_rows.append(('total_websocket_events', 				db_summary['total_websocket_events']))
		csv_rows.append(('total_requests', 						db_summary['total_requests']))
		csv_rows.append(('total_responses', 					db_summary['total_responses']))
		csv_rows.append(('percent_requests_received',		 	db_summary['percent_requests_received']))
		csv_rows.append(('total_3p_requests', 					db_summary['total_3p_requests']))
		csv_rows.append(('total_3p_responses', 					db_summary['total_3p_responses']))
		csv_rows.append(('percent_3p_requests_received', 		db_summary['percent_3p_requests_received']))

		self.utilities.write_csv(self.report_path,'db_summary.csv', csv_rows)
	# generate_db_summary_report

	def generate_stats_report(self):
		"""
		High level stats
		"""
		print('\t=============================')
		print('\t Processing High-Level Stats ')
		print('\t=============================')

		for tld_filter in self.top_tlds:
			csv_rows = []
	
			if tld_filter:
				stats = self.analyzer.get_high_level_stats(tld_filter)
			else:
				stats = self.analyzer.get_high_level_stats()

			if self.tracker_threshold:
				filter_depth = self.tracker_threshold
			else:
				filter_depth = 'no_filter_used'

			csv_rows.append(('n_pages', 					stats['total_pages']))
			csv_rows.append(('n_crawls', 					stats['total_crawls']))
			csv_rows.append(('%_pages_ssl', 				stats['percent_pages_ssl']))
			csv_rows.append(('n_requests_received', 		stats['total_requests_received']))
			csv_rows.append(('%_requests_received_ssl', 	stats['percent_requests_ssl']))
			csv_rows.append(('n_1p_requests_received', 		stats['total_requests_received_1p']))
			csv_rows.append(('%_1p_requests_received_ssl', 	stats['percent_1p_requests_ssl']))
			csv_rows.append(('n_3p_requests_received', 		stats['total_requests_received_3p']))
			csv_rows.append(('%_3p_requests_received_ssl', 	stats['percent_3p_requests_ssl']))
			csv_rows.append(('average_page_load_time', 		stats['average_page_load_time']))
			csv_rows.append(('%_w/3p_request',				stats['percent_w_3p_request']))
			csv_rows.append(('%_w/3p_cookie',				stats['percent_w_3p_cookie']))
			csv_rows.append(('%_w/3p_script',				stats['percent_w_3p_script']))
			csv_rows.append(('mean_3p_domains',				stats['3p_domains_mean']))
			csv_rows.append(('median_3p_domains',			stats['3p_domains_median']))
			csv_rows.append(('mode_3p_domains',				stats['3p_domains_mode']))
			csv_rows.append(('mean_3p_cookies',				stats['3p_cookies_mean']))
			csv_rows.append(('median_3p_cookies',			stats['3p_cookies_median']))
			csv_rows.append(('mode_3p_cookies',				stats['3p_cookies_mode']))

			if tld_filter:
				self.utilities.write_csv(self.report_path,tld_filter+'-stats.csv',csv_rows)
			else:
				self.utilities.write_csv(self.report_path,'stats.csv',csv_rows)
	# generate_stats_report

	def generate_aggregated_tracking_attribution_report(self):
		"""
		generates ranked list of which entities collect data 
			from the greatest number of crawls ('aggregated_tracking_attribution.csv')

		- entities which have subsidiaries are ranked according 
			to the crawls their subsidiaries get data from as well
		- however, parent entities only get one hit on 
			a crawl which has multiple subsidiaries present
		- for example, if a crawl has 'google analytics' and 'doubleclick' 
			that is only one hit for 'google'
		"""
		print('\t======================================')
		print('\t Processing Aggregated Tracking Report ')
		print('\t======================================')

		for tld_filter in self.top_tlds:
			csv_rows = []

			# write out data to csv
			for item in self.analyzer.get_aggregated_tracking_attribution(tld_filter):
				csv_rows.append((
					item['percent_crawls'],
					item['owner_name'],
					item['owner_country'],
					self.utilities.get_domain_owner_lineage_combined_string(item['owner_id'])
					)
				)
			
			# we want to first sort by owner name and then by percentage
			#	 to account for cases where two owners have the same percentage value
			csv_rows.sort(key=lambda x: x[1].lower())
			csv_rows.sort(key=lambda x: x[0],reverse=True)

			# insert header row after sort
			csv_rows.insert(0, ('percentage_crawls_tracked','owner','owner_country','owner_lineage'))

			# write out csv with tld prefix if applicable
			if tld_filter:
				self.utilities.write_csv(self.report_path,tld_filter+'-aggregated_tracking_attribution.csv',csv_rows)
			else:
				self.utilities.write_csv(self.report_path,'aggregated_tracking_attribution.csv',csv_rows)
	# generate_aggregated_tracking_attribution_report

	def generate_aggregated_3p_ssl_use_report(self):
		"""
		this report tells us the percentage of requests made to a given
			third-party are encrypted
		"""

		print('\t=========================================')
		print('\t Processing Aggregated 3P SSL Use Report ')
		print('\t=========================================')

		for tld_filter in self.top_tlds:
			csv_rows = []
			for item in self.analyzer.get_aggregated_3p_ssl_use(tld_filter):
				csv_rows.append((
					item['ssl_use'],
					item['owner_name'],
					item['owner_country'],
					self.utilities.get_domain_owner_lineage_combined_string(item['owner_id'])
				))

			# we want to first sort by owner name and then by percentage
			#	 to account for cases where two owners have the same percentage value
			csv_rows.sort(key=lambda x: x[1].lower())
			csv_rows.sort(key=lambda x: x[0],reverse=True)

			# insert header row after sort
			csv_rows.insert(0, ('percent_requests_encrypted','owner','owner_country','owner_lineage'))

			# write out csv with tld prefix if applicable
			if tld_filter:
				self.utilities.write_csv(self.report_path,tld_filter+'-3p_ssl_use.csv',csv_rows)
			else:
				self.utilities.write_csv(self.report_path,'3p_ssl_use.csv',csv_rows)
	# generate_aggregated_3p_ssl_use_report

	def generate_3p_domain_report(self):
		"""
		This report tells us the most commonly occuring third-party domains.
		"""
		print('\t==============================')
		print('\t Processing 3P Domains Report ')
		print('\t==============================')

		for tld_filter in self.top_tlds:
			csv_rows = []
			csv_rows.append(('percent_total','domain','owner','owner_country', 'owner_lineage'))

			# get_3p_domain_percentages returns a list, we slice it to get only desired num_results
			for item in self.analyzer.get_3p_domain_percentages(tld_filter)[:self.num_results]:
				
				# figure out the lineage string if we know who owns the domain
				if item['owner_id'] != None:
					lineage_string = self.utilities.get_domain_owner_lineage_combined_string(item['owner_id'])
				else:
					lineage_string = None

				csv_rows.append((
					item['percent_crawls'],
					item['domain'],
					item['owner_name'],
					item['owner_country'],
					lineage_string
				))

			if tld_filter:
				self.utilities.write_csv(self.report_path,tld_filter+'-3p_domains.csv',csv_rows)
			else:
				self.utilities.write_csv(self.report_path,'3p_domains.csv',csv_rows)
	# generate_3p_domain_report

	def generate_3p_request_report(self,request_type=None):
		"""
		this queries the db to get all requests, domains, or domain owners
		next they are counted to find the most common
		and formatted to csv rows and returned
		"""
		if request_type == 'script':
			print('\t=============================')
			print('\t Processing 3P Script Report ')
			print('\t=============================')
		else:
			print('\t==============================')
			print('\t Processing 3P Request Report ')
			print('\t==============================')
		
		for tld_filter in self.top_tlds:
			csv_rows = []
			csv_rows.append(('percent_total','request','type','domain','owner','owner_country','owner_lineage'))

			# get_3p_domain_percentages returns a list, we slice it to get only desired num_results
			for item in self.analyzer.get_3p_request_percentages(tld_filter,request_type)[:self.num_results]:
				
				# figure out the lineage string if we know who owns the domain
				if item['request_owner_id'] != None:
					lineage_string = self.utilities.get_domain_owner_lineage_combined_string(item['request_owner_id'])
				else:
					lineage_string = None

				csv_rows.append((
					item['percent_crawls'],
					item['request_url'],
					item['request_type'],
					item['request_domain'],
					item['request_owner_name'],
					item['request_owner_country'],
					lineage_string
				))

			if tld_filter:
				if request_type:
					self.utilities.write_csv(self.report_path,tld_filter+'-3p_'+request_type+'.csv',csv_rows)
				else:
					self.utilities.write_csv(self.report_path,tld_filter+'-3p_request.csv',csv_rows)
			else:
				if request_type:
					self.utilities.write_csv(self.report_path,'3p_'+request_type+'.csv',csv_rows)
				else:
					self.utilities.write_csv(self.report_path,'3p_request.csv',csv_rows)
	# generate_3p_request_report

	def generate_data_transfer_report(self):
		"""
		These reports tell us how much data was transferred across several dimensions
		"""
		
		print('\t==================================')
		print('\t Processing Data Transfer Reports ')
		print('\t==================================')
	

		for tld_filter in self.top_tlds:
			# set up filter and file names
			if tld_filter:
				summary_file_name 		= tld_filter+'-data_xfer_summary.csv'
				domain_file_name		= tld_filter+'-data_xfer_by_domain.csv'
				aggregated_file_name	= tld_filter+'-data_xfer_aggregated.csv'
			else:
				summary_file_name 		= 'data_xfer_summary.csv'
				domain_file_name		= 'data_xfer_by_domain.csv'
				aggregated_file_name	= 'data_xfer_aggregated.csv'

			# get the data from db, tuple of (response_domain, size, is_3p (boolean), domain_owner_id)
			response_sizes = self.sql_driver.get_response_sizes()

			# initialize vars
			first_party_data = 0
			third_party_data = 0
			total_data 		 = 0
			
			# need Counter object, allows sorting later
			domain_data	= collections.Counter()
			owner_data 	= collections.Counter()
			
			# process each row
			for item in response_sizes:

				response_domain	= item[0]
				response_size 	= item[1]
				response_is_3p 	= item[2]
				domain_owner_id = item[3]

				# this is the measure of all data downloaded
				total_data += response_size

				# measures for third and first party data
				if response_is_3p:
					third_party_data += response_size
				else:
					first_party_data += response_size

				# data by domain, increment if already in there, otherwise new entry
				if response_domain in domain_data:
					domain_data[response_domain] += response_size
				else:
					domain_data[response_domain] = response_size

				# only if we know the owner, increment
				if domain_owner_id:
					for lineage_id in self.utilities.get_domain_owner_lineage_ids(domain_owner_id):
						if lineage_id in owner_data:
							owner_data[lineage_id] += response_size
						else:
							owner_data[lineage_id] = response_size

			# avoid divide-by-zero
			if total_data == 0:
				print('\t\tTotal data is zero, no report')
				return

			# output data to csv
			summary_data_csv = []
			summary_data_csv.append(('party','percent_total','data_transfered_bytes'))
			summary_data_csv.append(('all','100',total_data))
			summary_data_csv.append((
				'First', 
				round((first_party_data/total_data)*100, self.num_decimals),
				first_party_data))
			summary_data_csv.append((
				'Third', 
				round((third_party_data/total_data)*100, self.num_decimals),
				third_party_data))

			self.utilities.write_csv(self.report_path,summary_file_name, summary_data_csv)
			
			# sort and output ranked data
			domain_data = domain_data.most_common()
			domain_data.sort()
			domain_data.sort(reverse=True, key=lambda item:item[1])

			# for csv data
			domain_data_csv = []
			domain_data_csv.append(('percent_total','domain','data_transfered_bytes'))

			# if num_results is None we get everything, otherwise stops at limit
			for item in domain_data[:self.num_results]:
				domain_data_csv.append((
					round((item[1]/total_data)*100,self.num_decimals),
					item[0],
					item[1]))
			self.utilities.write_csv(self.report_path,domain_file_name, domain_data_csv)

			owner_data 	= self.utilities.get_most_common_sorted(owner_data)
			owner_data_csv = []
			owner_data_csv.append(('percent_total','owner','owner_country','owner_lineage','data_transfered_bytes'))
			# get results for all known owners
			for item in owner_data:
				owner_data_csv.append((
					round((item[1]/total_data)*100,self.num_decimals),
					self.domain_owners[item[0]]['owner_name'],
					self.domain_owners[item[0]]['country'],
					self.utilities.get_domain_owner_lineage_combined_string(item[0]),
					item[1]
				))
			self.utilities.write_csv(self.report_path,aggregated_file_name, owner_data_csv)
	# generate_data_transfer_report

	def generate_use_report(self):
		"""
		This function handles the process of generating a csv report which details
			what percentage of pages use third-party content for specific uses,
			the number of requests made for a given type of use on a per-page basis,
			and the percentage of such requests which correspond to a third-party
			cookie.
		"""

		print('\t==========================')
		print('\t Processing 3P Use Report ')
		print('\t==========================')


		for tld_filter in self.top_tlds:
			use_data 						= self.analyzer.get_3p_use_data(tld_filter)
			all_uses						= use_data['all_uses']
			percentage_by_use 				= use_data['percentage_by_use']
			average_use_occurance_per_page 	= use_data['average_use_occurance_per_crawl']
			percentage_use_w_cookie 		= use_data['percentage_use_w_cookie']
			percentage_use_ssl				= use_data['percentage_use_ssl']

			csv_rows = []
			csv_rows.append(('use_category','percent_crawls_w_use','ave_occurances_per_page','percentage_of_use_w_cookie', 'percentage_of_use_ssl'))
			for use in sorted(all_uses):
				if percentage_by_use[use] != None:
					csv_rows.append((
						use,
						percentage_by_use[use],
						average_use_occurance_per_page[use],
						percentage_use_w_cookie[use],
						percentage_use_ssl[use]
					))
				else:
					csv_rows.append((use,None,None,None,None))

			# write out csv with tld prefix if applicable
			if tld_filter:
				self.utilities.write_csv(self.report_path,tld_filter+'-3p_uses.csv',csv_rows)
			else:
				self.utilities.write_csv(self.report_path,'3p_uses.csv',csv_rows)
	# generate_use_report

	def generate_per_page_network_report(self):
		"""
		this report generates data necessary for graph/network analysis by
			outputting a list of page domains and the requests/owners they connect to
			on a per-page basis
		"""

		print('\t====================================')
		print('\t Processing Per-Page Network Report ')
		print('\t====================================')
		
		# put output here
		csv_rows = []
		
		# header row for csv		
		csv_rows.append(('page_start_url','page_final_url','page_accessed','3p_request_domain','3p_domain_owner','3p_domain_owner_country'))

		# process all records
		for item in self.analyzer.get_page_to_3p_network():
			csv_rows.append((
				item['page_start_url'],
				item['page_final_url'],
				item['page_accessed'],
				item['request_domain'],
				item['request_owner_name'],
				item['request_owner_country']
			))

		self.utilities.write_csv(self.report_path,'per_page_network_report.csv', csv_rows)
	# generate_per_page_network_report

	def generate_per_site_network_report(self):
		"""
		this report generates data necessary for graph/network analysis by
			outputting a list of page domains and the requests/owners they connect to
			aggregated on a per-site basis (eg combining all pages)
		"""

		print('\t================================')
		print('\t Processing Site Network Report ')
		print('\t================================')

		# put output here
		csv_rows = []
		
		# header row for csv		
		csv_rows.append(('page_domain','3p_request_domain','3p_domain_owner','3p_domain_owner_country'))
		
		for item in self.analyzer.get_site_to_3p_network():
			csv_rows.append((
				item['page_domain'],
				item['request_domain'],
				item['request_owner_name'],
				item['request_owner_country']
			))

		self.utilities.write_csv(self.report_path,'per_site_network_report.csv', csv_rows)
	# generate_per_site_network_report

	def generate_all_pages_request_dump(self):
		"""
		Full dump of all requests loaded by all pages across all load times.
			Default is 3p only, can be overridden.
		"""

		print('\t===================================')
		print('\t Processing All Pages request Dump ')
		print('\t===================================')
		
		# put output here
		csv_rows = []
		
		# header row for csv		
		csv_rows.append((
			'accessed',
			'start_url',
			'final_url',
			'request_url',
			'request_domain',
			'domain_owner'
		))

		# process all records
		for item in self.analyzer.get_all_pages_requests():
			csv_rows.append((
				item['accessed'],
				item['start_url'],
				item['final_url'],
				item['request_url'],
				item['request_domain'],
				item['request_domain_owner']
			))

		self.utilities.write_csv(self.report_path,'all_pages_request_dump.csv', csv_rows)
	# generate_all_pages_request_dump

	def generate_all_pages_cookie_dump(self):
		"""
		Full dump of all cookies loaded by all pages across all load times.
			Default is 1p and 3p, can be overridden to 3p only.
		"""

		print('\t==================================')
		print('\t Processing All Pages Cookie Dump ')
		print('\t==================================')
		
		# put output here
		csv_rows = []
		
		# header row for csv		
		csv_rows.append((
			'accessed',
			'start_url',
			'final_url',
			'cookie_domain',
			'cookie_owner',
			'cookie_name',
			'cookie_value'
		))

		# process all records
		for item in self.analyzer.get_all_pages_cookies():
			csv_rows.append((
				item['accessed'],
				item['start_url'],
				item['final_url'],
				item['cookie_domain'],
				item['cookie_owner'],
				item['cookie_name'],
				item['cookie_value']
			))

		self.utilities.write_csv(self.report_path,'all_pages_cookie_dump.csv', csv_rows)
	# generate_all_pages_request_dump

	def generate_site_host_report(self):
		"""
		First, we update the domain table with the owners
			of the various ip addresses which gives us
			a mapping of pages to hosts.

		Second, we generate a network report for
			site domains to hosts.

		"""
		print('\t=====================')
		print('\t Updating Site Hosts ')
		print('\t=====================')

		self.analyzer.update_site_hosts()

		print('\t==============================')
		print('\t Generating Site Host Network ')
		print('\t==============================')

		site_host_data = self.analyzer.get_site_host_network()

		if len(site_host_data) == 0:
			print('\t\tNo site host data, skipping report.')
			return

		# put output here
		csv_rows = []
		
		# header row for csv		
		csv_rows.append((
			'page_domain',
			'host_name'
		))

		for item in site_host_data:
			csv_rows.append((
				item['site_domain'],
				item['host_name']
			))

		self.utilities.write_csv(self.report_path,'site_hosts-network.csv', csv_rows)

		print('\t============================================')
		print('\t Generating Aggregate Host Ownership Report ')
		print('\t============================================')

		owner_occurances = []
		for owner, in self.sql_driver.get_ip_owners():
			owner_occurances.append(owner)

		csv_rows = [('owner','percent_sites_w_owner')]
		for item in self.utilities.get_most_common_sorted(owner_occurances):
			csv_rows.append((item[0],100*(item[1]/len(owner_occurances))))

		self.utilities.write_csv(self.report_path,'site_hosts-aggregated.csv', csv_rows)
	# generate_site_host_report

	##############
	# POLICYXRAY #
	##############

	def initialize_policy_reports(self):
		"""
		Run various pre-production steps.
		"""

		print('\t====================================')
		print('\t Updating 3p Domain Disclosure Data ')
		print('\t====================================')

		#self.analyzer.update_request_disclosure()
		self.analyzer.update_crawl_disclosure()

		print('\t\t...done!')


		print('\t======================================')
		print('\t Getting Policy Types List and Counts ')
		print('\t======================================')

		# pre-populate with 'None' which gives all policies
		self.policy_types = [
			{
			'type'	: None,
			'count'	: self.analyzer.get_policy_count()
			}
		]

		for policy_type, in self.sql_driver.get_available_policy_types():
			self.policy_types.append({
				'type': policy_type,
				'count': self.analyzer.get_policy_count(policy_type=policy_type)
			})

		print('\t\t...done!')
	# initialize_policy_reports

	def generate_policy_summary_report(self):
		"""
		Conducts prelminary analysis steps, determines what types of 
			policies we have, and then initiates the pertinent reports.
		"""
		print('\t==================================')
		print('\t Generating Policy Summary Report ')
		print('\t==================================')

		# header row
		csv_rows = [('Type','N','Word Count','FK Grade','FRE', '% 3P Disclosed')]

		# get results for each policy_type
		for policy_type in self.policy_types:
			# makes reports clearer than 'None'
			if policy_type['type'] == None: 
				this_policy_type = 'all'
			else:
				this_policy_type = policy_type['type']

			print('\t\tProcessing %s...' % this_policy_type, end='', flush=True)

			# fetch results
			readability_scores	= self.analyzer.get_readability_scores(policy_type=policy_type['type'])
			
			csv_rows.append((
				this_policy_type,
				policy_type['count'],
				self.analyzer.get_average_policy_word_count(policy_type=policy_type['type']),
				readability_scores['ave_fkg'],
				readability_scores['ave_fre'],
				self.analyzer.get_percent_crawl_3p_domains_disclosed(policy_type=policy_type['type'])
			))
			print('done!')

		self.utilities.write_csv(self.report_path,'policy-summary.csv', csv_rows)
	# generate_policy_summary_report

	def generate_policy_owner_disclosure_reports(self):
		"""
		Determines what types of policies we have, and then
			initiates the pertinent reports.
		"""

		print('\t======================================')
		print('\t Generating Company Disclosure Report ')
		print('\t======================================')

		# header row
		csv_rows = [('Type','N','%% 3P Disclosed')]

		print('\t\tProcessing ...', end='', flush=True)

		company_results = self.analyzer.get_disclosure_by_request_owner()
		csv_rows = [('Domain Owner','Total Occurances','Total Disclosures','Percent Disclosed')]
		for item in company_results:
			csv_rows.append((item,company_results[item][0],company_results[item][1],round(company_results[item][2],2)))
	
		print('done!')
		self.utilities.write_csv(self.report_path,'policy-owner_disclosure.csv',csv_rows)
	# generate_policy_owner_disclosure_reports

	def generate_policy_gdpr_report(self):
		"""
		Determine percentage of all policy types
			that contain gdpr article 9 terms.
		"""

		print('\t==============================')
		print('\t Generating GDPR Term Report ')
		print('\t==============================')

		term_list = [
			'racial or ethnic origin', 'political opinions', 
			'religious or philosophical beliefs', 'trade union membership', 
			'genetic data', 'biometric data', 
			'data concerning health', 'sex life', 
			'sexual orientation'
		]

		self.generate_terms_report('policy-gdpr_terms.csv',term_list)
	# generate_policy_gdpr_report

	def generate_policy_pacification_report(self):
		"""
		Determine percentage of all policy types
			that contain pacification terms.
		"""

		print('\t=====================================')
		print('\t Generating Pacification Term Report ')
		print('\t=====================================')

		term_list = ['we value', 'we respect', 'important to us', 'help you', 'we care', 'committed to protecting', 'cares about', 'transparency']

		self.generate_terms_report('policy-pacification_terms.csv',term_list)
	# generate_policy_pacification_report

	def generate_policy_pii_report(self):
		"""
		Determine percentage of all policy types
			that contain pacification terms.
		"""

		print('\t============================')
		print('\t Generating PII Term Report ')
		print('\t============================')

		term_list = ['ip address','internet protocol address', 'browser type', 'operating system']

		self.generate_terms_report('policy-pii_terms.csv',term_list)
	# generate_policy_pacification_report

	def generate_terms_report(self,report_name,term_list):
		"""
		Generic function to generate reports on how
			often terms appear in policies.
		"""

		# set up header row
		csv_rows = []
		header_row = ('Type','any term')
		for term in term_list:
			header_row = header_row + (term,)

		csv_rows.append(header_row)

		# get results for each policy_type
		for policy_type in self.policy_types:
			# makes reports clearer than 'None'
			if policy_type['type'] == None: 
				this_policy_type = 'all'
			else:
				this_policy_type = policy_type['type']

			print('\t\tProcessing %s...' % this_policy_type, end='', flush=True)

			this_csv_row = (this_policy_type,)
			this_csv_row = this_csv_row + (self.analyzer.get_terms_percentage(term_list,policy_type=policy_type['type'],policy_type_count=policy_type['count']),)
			for term in term_list:
				this_csv_row = this_csv_row + (self.analyzer.get_terms_percentage([term],policy_type=policy_type['type'],policy_type_count=policy_type['count']),)
			csv_rows.append(this_csv_row)
			print('done!')

		self.utilities.write_csv(self.report_path,report_name,csv_rows)
	# generate_policy_gdpr_report

# Reporter
