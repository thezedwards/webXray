# standard python libraries
import os
import re
import csv
import json
import operator
import statistics
import collections
from datetime import datetime
from operator import itemgetter

class Analyzer:
	"""
	webXray stores data in a relational db, but that isn't human-readable
	so what this class does is analyze the data and exports it to csv files that can be
	opened in other programs (e.g. excel, r, gephi)

	Most of the reports may also be run on the top tlds (off by default), so you will be able to
	see if there are variations between tlds ('org' and 'com' usually differ quite a bit)

	See the readme for details on all of the available reports.
	"""

	def __init__(self, db_engine, db_name, num_tlds, num_results, flush_owner_db = True):
		"""
		This performs a few start-up tasks:
			- sets up some useful global variables
			- makes sure we have a directory to store the reports
			- flushes the existing domain_owner mappings (this can be disabled)
			- if we want to do per-tld reports, figures out the most common
		"""

		# set various global vars
		self.db_engine			= db_engine
		self.db_name 			= db_name
		self.num_tlds 			= num_tlds
		self.top_tlds 			= []
		self.num_results 		= num_results
		self.start_time			= datetime.now()
		
		# number of decimal places to round to in reports
		self.num_decimals		= 2

		# set up global db connection
		if self.db_engine == 'sqlite':
			from webxray.SQLiteDriver import SQLiteDriver
			self.sql_driver = SQLiteDriver(self.db_name)
		else:
			print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
			exit()
		
		# this is reused often, do it once to save time
		self.get_pages_ok_count		= self.sql_driver.get_pages_ok_count()

		print('\t=============================')
		print('\t Checking Output Directories ')
		print('\t=============================')				
		
		self.setup_report_dir()

		print('\t============================')
		print('\t Patching Domain Owner Data ')
		print('\t============================')

		if flush_owner_db:
			# update the domains to their owners in the db, can be overridden
			#	by changing flush_owner_db to false
			self.patch_domain_owners()
		else:
			print('\t\t\tSkipping')

		# this is used in various places to get owner information
		self.domain_owners = self.get_domain_owner_dict()

		# if we want to get sub-reports for the most frequent tlds we find
		#	them here
		if self.num_tlds:
			print('\t=====================')
			print('\t Getting top %s tlds' % self.num_tlds)
			print('\t=====================')
			print('\t\tProcessing...', end='', flush=True)
			self.top_tlds = self.get_top_tlds(self.num_tlds)
			print('done!')
			print('\t\tThe top tlds are:')
			for (tld, pages) in self.top_tlds:
				if tld: print('\t\t |- %s (%s)' % (tld,pages))
		else:
			# othewise we push in a single empty entry
			self.top_tlds.append((None,self.get_pages_ok_count))
	# __init__

	#################
	#	UTILITIES	#
	#################

	def setup_report_dir(self):
		"""
		create directory for where the reports go if it does not exist
		"""
		if os.path.exists('./reports') == False:
			print('\t\tMaking global reports directory at ./reports.')
			os.makedirs('./reports')
		
		# set global report_path
		self.report_path = './reports/'+self.db_name
	
		# set up subdir for this analysis
		if os.path.exists(self.report_path) == False:
			print('\t\tMaking subdirectory for reports at %s' % self.report_path)
			os.makedirs(self.report_path)

		print('\t\tStoring output in %s' % self.report_path)
	# setup_report_dir

	def write_csv(self, file_name, csv_rows):
		"""
		basic utility function to write list of csv rows to a file
		"""
		full_file_path = self.report_path+'/'+file_name
		with open(full_file_path, 'w', newline='', encoding='utf-8') as csvfile:
			csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			for row in csv_rows:
				csv_writer.writerow(row)
		print('\t\tOutput written to %s' % full_file_path)
	# write_csv

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

	def print_runtime(self):
		"""
		just for CLI info
		"""
		print('~='*40)
		print('Finished!')
		print('Time to process: %s' % str(datetime.now()-self.start_time))
		print('-'*80)
	# print_runtime

	def patch_domain_owners(self):
		"""
		in order to analyze what entities receive user data, we need to update
		  the database with domain ownership records we have stored previously
		"""

		# we first clear out what is the db in case the new data has changed, 
		# 	on big dbs takes a while
		print('\t\tFlushing extant domain owner data...', end='', flush=True)
		self.sql_driver.reset_domain_owners()
		print('done!')

		# next we pull the owner/domain pairings from the json file in 
		# 	the resources dir and add to the db
		print('\t\tPatching with new domain owner data...', end='', flush=True)
		domain_owner_data = json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/domain_owners/domain_owners.json', 'r', encoding='utf-8'))
		for item in domain_owner_data:
			aliases = ''
			for alias in item['aliases']:
				aliases += '<<' + alias + '>>'
			self.sql_driver.add_domain_owner(
				item['id'], 
				item['parent_id'],
				item['owner_name'], 
				aliases,
				item['homepage_url'],
				item['notes'], 
				item['country']
			)
			for domain in item['domains']:
				self.sql_driver.update_domain_owner(item['id'], domain)
		print('done!')
	# patch_domain_owners

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
		domain_owners = {}
		domain_owner_raw_data = self.sql_driver.get_all_domain_owner_data()
		if domain_owner_raw_data:
			for item in domain_owner_raw_data:
				# aliases are stored in the db as a string that needs to be turned into a list
				aliases = []
				for alias in re.split('<<(.+?)>>',item[3]):
					if alias != '': aliases.append(alias)
				# add everything to the dict
				domain_owners[item[0]] = {
					'parent_id' :			item[1],
					'owner_name' :			item[2],
					'aliases' :				aliases,
					'homepage_url' :		item[4],
					'notes' :				item[5],
					'country' :				item[6],
				}
		return domain_owners
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
		return lineage_string[:-2]
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

	def get_top_tlds(self, limit):
		"""
		finds the most common tlds from all the pages
		type is default to tld, but pubsuffix also works

		returns list of tlds
		"""

		tlds = []

		for row in self.sql_driver.get_all_tlds():
			tlds.append(row[0])

		top_tlds = collections.Counter(tlds).most_common()
	
		# cut the list to the limit
		top_tlds = top_tlds[0:limit]

		# push in entry for all tlds
		top_tlds.insert(0, (None,self.get_pages_ok_count))
		
		return top_tlds
	# get_top_tlds

	#####################
	# 	REPORT HELPERS	#
	#####################

	def get_3p_domain_stats(self, num_pages, tld_filter = None):
		"""
		determines basic stats for the number of 3p domains contacted per-page
		
		note this is distinct domain+pubsuffix, not fqdns (e.g. 'sub.example.com' 
			and sub2.example.com' only count as 'example.com')
		"""

		# each page id corresponds to a list of domains belonging to page elements
		page_id_to_domains_dict = {}

		# run query to get all page id, page domain, and element domain entries
		# there is no third-party filter so each page will have at least one entry for first-party domain
		for row in self.sql_driver.get_page_id_3p_element_domain_pairs(tld_filter):
			page_id 		= row[0]
			element_domain 	= row[1]

			# if the page id is not yet seen enter the current element as a fresh list
			#	otherwise, we add to the existing list
			if page_id not in page_id_to_domains_dict:
				page_id_to_domains_dict[page_id] = [element_domain]
			else:
				page_id_to_domains_dict[page_id] = page_id_to_domains_dict[page_id] + [element_domain]

		# now we determine the number of domains each page is connected to by looking at len of list of 3p domains
		per_page_3p_element_counts = []
		for page_id in page_id_to_domains_dict:
			per_page_3p_element_counts.append(len(page_id_to_domains_dict[page_id]))

		# pages that have no 3p elements are not yet in our counts
		# 	so for all uncounted pages we add in zeros
		uncounted_pages = num_pages - len(per_page_3p_element_counts)
		while uncounted_pages > 0:
			uncounted_pages -= 1
			per_page_3p_element_counts.append(0)

		# mean and median should always be ok
		mean 	= statistics.mean(per_page_3p_element_counts)
		median 	= statistics.median(per_page_3p_element_counts)

		# but mode can throw an error, so catch here
		try:
			mode = statistics.mode(per_page_3p_element_counts)
		except:
			mode = None

		return(mean, median, mode)
	# get_3p_domain_stats

	def get_3p_cookie_stats(self, num_pages, tld_filter = None):
		"""
		determines basic stats for the number of 3p cookies contacted per-page
			note that a single 3p many set more than one cookie
		"""

		# each page id corresponds to a list of cookie ids
		page_id_to_cookie_id_dict = {}

		# run query to get all page id, 3p cookie id, 3p cookie domain entries
		for row in self.sql_driver.get_page_id_3p_cookie_id_3p_cookie_domain(tld_filter):
			page_id 		= row[0]
			cookie_id		= row[1]
			cookie_domain 	= row[2]

			# if the page id is not yet seen enter the current cookie id as a fresh list
			#	otherwise, we add to the existing list
			if page_id not in page_id_to_cookie_id_dict:
				page_id_to_cookie_id_dict[page_id] = [cookie_id]
			else:
				page_id_to_cookie_id_dict[page_id] = page_id_to_cookie_id_dict[page_id] + [cookie_id]

		# determine the number of 3p cookies each page has by looking at len of list of cookie ids
		per_page_3p_cookie_counts = []
		for page_id in page_id_to_cookie_id_dict:
			per_page_3p_cookie_counts.append(len(page_id_to_cookie_id_dict[page_id]))

		# pages that have no 3p cookies are not yet in our counts
		# so for all uncounted pages we add in zeros
		uncounted_pages = num_pages - len(per_page_3p_cookie_counts)
		while uncounted_pages > 0:
			uncounted_pages -= 1
			per_page_3p_cookie_counts.append(0)

		# mean and median should always be ok
		mean 	= statistics.mean(per_page_3p_cookie_counts)
		median 	= statistics.median(per_page_3p_cookie_counts)

		# but mode can throw an error, so catch here
		try:
			mode = statistics.mode(per_page_3p_cookie_counts)
		except:
			mode = None

		return(mean, median, mode)
	# get_3p_cookie_stats

	#####################
	# REPORT GENERATORS #
	#####################

	def generate_db_summary_report(self):
		"""
		outputs and stores report of basic data about how many records in db, etc.
		"""
		print('\t================')
		print('\t General Summary')
		print('\t================')
		
		csv_rows = []

		total_pages_ok = self.sql_driver.get_pages_ok_count()

		print("\t\tTotal Pages OK:\t\t\t%s" % total_pages_ok)
	
		csv_rows.append(('Total Pages OK',total_pages_ok))
	
		total_pages_noload = self.sql_driver.get_pages_noload_count()
		total_pages_attempted = total_pages_ok + total_pages_noload
	
		print("\t\tTotal Pages FAIL:\t\t%s" % total_pages_noload)
		csv_rows.append(('Total Pages FAIL', total_pages_noload))
	
		print("\t\tTotal Pages Attempted:\t\t%s" % total_pages_attempted)
		csv_rows.append(('Total Pages Attempted',total_pages_attempted))
	
		percent_pages_OK = (total_pages_ok/total_pages_attempted)*100
		print("\t\t%% Pages OK:\t\t\t%.2f%%" % round(percent_pages_OK,self.num_decimals))
		csv_rows.append(('% Pages OK', round(percent_pages_OK,self.num_decimals)))

		print('\t\t---')
	
		total_errors = self.sql_driver.get_total_errors_count()
		print("\t\tTotal Errors:\t\t\t%s" % total_errors)
		csv_rows.append(('Total Errors', total_errors))
	
		print('\t\t---')
	
		total_3p_cookies = self.sql_driver.get_total_cookie_count(is_3p = True)
		print("\t\tTotal 3P Cookies:\t\t%s" % total_3p_cookies)
		csv_rows.append(('Total Cookies', total_3p_cookies))

		print('\t\t---')
	
		# see if we have both 1p/3p requests, if so show stats for all
		total_1p_elements = self.sql_driver.get_total_request_count(party='first')
		if total_1p_elements > 0:
			total_elements = self.sql_driver.get_total_request_count()
			print("\t\tTotal Elements Requested:\t%s" % total_elements)
			csv_rows.append(('Total Elements Requested', total_elements))

			total_elements_received = self.sql_driver.get_total_request_count(received = True)
			print("\t\tTotal Elements Received:\t%s" % total_elements_received)
			csv_rows.append(('Total Elements Received', total_elements_received))

			percent_element_received = (total_elements_received/total_elements)*100
			print('\t\tTotal %% Elements Received:\t%.2f%%' % percent_element_received)
			csv_rows.append(('Total % Elements Received', round(percent_element_received,self.num_decimals)))
		
			print('\t\t---')

		# only 3p request/receive info - we always do this
		total_3p_elements = self.sql_driver.get_total_request_count(party='third')
		print("\t\t3P Elements Requested:\t\t%s" % total_3p_elements)
		csv_rows.append(('3P Elements Requested', total_3p_elements))

		# avoid divide-by-zero if no 3p elements
		if total_3p_elements > 0:
			total_3p_elements_received = self.sql_driver.get_total_request_count(received = True, party='third')
			print("\t\t3P Elements Received:\t\t%s" % total_3p_elements_received)
			csv_rows.append(('3P Elements Received', total_3p_elements_received))

			percent_3p_element_received = (total_3p_elements_received/total_3p_elements)*100
			print('\t\t3P %% Elements Received:\t\t%.2f%%' % percent_3p_element_received)
			csv_rows.append(('3P % Elements Received', round(percent_3p_element_received,self.num_decimals)))

		print('\t\t'+'-'*40)
		self.write_csv('db_summary.csv', csv_rows)
	# generate_db_summary_report

	def generate_stats_report(self):
		"""
		High level stats
		"""
		print('\t=============================')
		print('\t Processing High-Level Stats ')
		print('\t=============================')

		for tld in self.top_tlds:
			csv_rows = []
	
			if tld[0]:
				tld_filter = tld[0]
				file_name = tld[0]+'-stats.csv'
			else:
				tld_filter = None
				file_name = 'stats.csv'

			# page info
			total_pages 			= self.sql_driver.get_complex_page_count(tld_filter)
			total_pages_percent 	= (total_pages/self.get_pages_ok_count)*100
			total_pages_elements 	= self.sql_driver.get_complex_page_count(tld_filter, 'elements')
			percent_with_elements 	= (total_pages_elements/total_pages)*100
			total_pages_cookies 	= self.sql_driver.get_complex_page_count(tld_filter, 'cookies')
			percent_with_cookies 	= (total_pages_cookies/total_pages)*100
			total_pages_js 			= self.sql_driver.get_complex_page_count(tld_filter, 'javascript')
			percent_with_js 		= (total_pages_js/total_pages)*100
			total_pages_ssl 		= self.sql_driver.get_pages_ok_count(is_ssl = True)
			percent_pages_ssl		= (total_pages_ssl/total_pages)*100

			# elements info
			total_elements_received 		= self.sql_driver.get_total_request_count(received = True)
			total_elements_received_ssl		= self.sql_driver.get_total_request_count(received = True, is_ssl = True)

			total_elements_received_1p 		= self.sql_driver.get_total_request_count(received = True, party='first')
			total_elements_received_1p_ssl	= self.sql_driver.get_total_request_count(received = True, party='first', is_ssl = True)

			total_elements_received_3p 		= self.sql_driver.get_total_request_count(received = True, party='third')
			total_elements_received_3p_ssl	= self.sql_driver.get_total_request_count(received = True, party='third', is_ssl = True)

			all_load_times = self.sql_driver.get_pages_load_times()
			all_load_times_sum = 0
			for load_time in all_load_times:
				all_load_times_sum += load_time

			average_page_load_time =  all_load_times_sum/len(all_load_times)

			domain_stats	= self.get_3p_domain_stats(total_pages, tld_filter)
			domain_mean 	= domain_stats[0]
			domain_median	= domain_stats[1]
			domain_mode		= domain_stats[2]

			cookie_stats 	= self.get_3p_cookie_stats(total_pages, tld_filter)
			cookie_mean 	= cookie_stats[0]
			cookie_median	= cookie_stats[1]
			cookie_mode		= cookie_stats[2]

			csv_rows.append(('N Pages Loaded', total_pages))
			csv_rows.append(('% of all Pages',total_pages_percent))
			csv_rows.append(('% Pages SSL', round(percent_pages_ssl, self.num_decimals)))

			csv_rows.append(('N Elements Received', total_elements_received))
			csv_rows.append(('% Elements Received SSL', round((total_elements_received_ssl/total_elements_received)*100,self.num_decimals)))
			csv_rows.append(('N 1P Elements Received', total_elements_received_1p))
			csv_rows.append(('% 1P Elements Received SSL', round((total_elements_received_1p_ssl/total_elements_received_1p)*100,self.num_decimals)))
			csv_rows.append(('N 3P Elements Received', total_elements_received_3p))
			csv_rows.append(('% 3P Elements Received SSL', round((total_elements_received_3p_ssl/total_elements_received_3p)*100,self.num_decimals)))

			csv_rows.append(('Average Page Load Time (ms)', round(average_page_load_time,self.num_decimals)))

			csv_rows.append(('% w/3p Element',round(percent_with_elements,self.num_decimals)))
			csv_rows.append(('% w/3p Cookie',round(percent_with_cookies,self.num_decimals)))
			csv_rows.append(('% w/3p Javascript',round(percent_with_js,self.num_decimals)))

			csv_rows.append(('Mean 3p Domains',round(domain_mean,self.num_decimals)))
			csv_rows.append(('Median 3p Domains',domain_median))
			csv_rows.append(('Mode 3p Domains',domain_mode))

			csv_rows.append(('Mean 3p Cookies',round(cookie_mean,self.num_decimals)))
			csv_rows.append(('Median 3p Cookies',cookie_median))
			csv_rows.append(('Mode 3p Cookies',cookie_mode))

			self.write_csv(file_name,csv_rows)
	# generate_stats_report

	def generate_aggregated_tracking_attribution_report(self):
		"""
		generates ranked list of which entities collect data 
			from the greatest number of pages ('data_flow_ownership.csv')

		- entities which have subsidiaries are ranked according 
			to the pages their subsidiaries get data from as well
		- however, parent entities only get one hit on 
			a page which has multiple subsidiaries present
		- for example, if a page has 'google analytics' and 'doubleclick' 
			that is only one hit for 'google'

		also able to filter by tld
		"""
		print('\t======================================')
		print('\t Processing Aggregated Tracking Report ')
		print('\t======================================')

		for tld in self.top_tlds:
			csv_rows = []
			csv_rows.append(('Percentage Pages Tracked','Owner','Owner Country','Owner Lineage'))

			# will need this value to determine percentages later on
			total_pages = self.sql_driver.get_complex_page_count(tld_filter=tld[0])

			# list will have entry for each hit on a given entity
			all_owner_occurances = []

			# each page id is a key which corresponds to a list of 
			#	ids for entities which own the 3p element domains
			page_to_element_owners = {}

			# this query may produce a large volume of results!
			results = self.sql_driver.get_all_page_id_3p_domain_owner_ids(tld_filter=tld[0])

			# for each result we either create a new list, or extend the existing one
			#	with the ids of the owners of the 3p elements
			for item in results:
				page_id = item[0]
				element_owner_id = item[1]

				if page_id not in page_to_element_owners:
					page_to_element_owners[page_id] = [element_owner_id]
				else:
					page_to_element_owners[page_id] = page_to_element_owners[page_id] + [element_owner_id]

			# now that we have ids for each page, we can look up the lineage
			#	to create the aggregate measure of how often entities appear
			for item in page_to_element_owners:

				# this is a set so items which appear more than once only get counted once
				# reset this for each page
				page_domain_owners = set()

				# we are operating on a list of ids which correspond to the owners of domains which get the data
				for page_3p_owner_id in page_to_element_owners[item]:
					# for each domain owner we also count all of its parents by getting the lineage
					for lineage_id in self.get_domain_owner_lineage_ids(page_3p_owner_id):
						page_domain_owners.add((lineage_id, self.domain_owners[lineage_id]['owner_name']))

				# we have finished processing for this page so we add the owner ids to the full list
				for owner_id in page_domain_owners:
					all_owner_occurances.append(owner_id)

			# write out data to csv
			for item in self.get_most_common_sorted(all_owner_occurances):
				# we want to specify the parent name for each item, or if there is no parent, identify as such
				parent_id = self.domain_owners[item[0][0]]['parent_id']
				if parent_id:
					parent_name = self.domain_owners[parent_id]['owner_name']
				else:
					parent_name = ''
				csv_rows.append((
					round((item[1]/total_pages)*100,2),
					item[0][1],
					self.domain_owners[item[0][0]]['country'],
					self.get_domain_owner_lineage_combined_string(item[0][0])
					)
				)
			
			# set file name prefix when doing tld-bounded report
			if tld[0]:
				file_name = tld[0]+'-aggregated_tracking_attribution.csv'
			else:
				file_name = 'aggregated_tracking_attribution.csv'

			# done!
			self.write_csv(file_name,csv_rows)
	# generate_aggregated_tracking_attribution_report

	def generate_aggregated_3p_ssl_use_report(self):
		"""
		this report tells us the percentage of requests made to a given
			third-party are encrypted
		"""

		print('\t=========================================')
		print('\t Processing Aggregated 3P SSL Use Report ')
		print('\t=========================================')

		csv_rows = []

		domain_owners_ssl_use_dict = {}

		for item in self.sql_driver.get_3p_element_domain_owner_id_ssl_use():
			child_domain_owner_id = item[0]
			is_ssl = item[1]

			for domain_owner_id in self.get_domain_owner_lineage_ids(child_domain_owner_id):
				if domain_owner_id not in domain_owners_ssl_use_dict:
					domain_owners_ssl_use_dict[domain_owner_id] = [is_ssl]
				else:
					domain_owners_ssl_use_dict[domain_owner_id] = domain_owners_ssl_use_dict[domain_owner_id] + [is_ssl]

		for domain_owner_id in domain_owners_ssl_use_dict:
			csv_rows.append((
				round(100*(sum(domain_owners_ssl_use_dict[domain_owner_id])/len(domain_owners_ssl_use_dict[domain_owner_id])),self.num_decimals),
				self.domain_owners[domain_owner_id]['owner_name'], 
				self.domain_owners[domain_owner_id]['country'],
				self.get_domain_owner_lineage_combined_string(domain_owner_id)
			))

		# sort results by owner, note is upper then lower case
		#	would cause code bloat to do otherwise, but worth considering
		csv_rows.sort(key=itemgetter(1))

		# now sort by percentage of encrypted requests descending
		csv_rows.sort(key=itemgetter(0),reverse=True)

		# insert header row after sort
		csv_rows[0] = ('Percent Requests Encrypted','Owner','Owner Country','Owner Lineage')

		# done!
		self.write_csv('3p_ssl_use.csv',csv_rows)
	# generate_aggregated_3p_ssl_use_report

	def generate_per_page_data_flow_report(self):
		"""
		generates a csv which has information on data flows for each page

		note this file may be very large and is disabled by default
		"""
		print('\t======================================')
		print('\t Processing Per-Page Data Flow Report ')
		print('\t======================================')
		
		file_name = 'per_page_data_flow.csv'
		csv_rows = []
		csv_rows.append(('Final URL','3P Domain','Owner','Owner Country','Owner Lineage'))

		for item in self.sql_driver.get_all_pages_3p_domains_and_owners():
			# this condition has to specify != None, b/c otherwise it will skip values of 0
			if item[3] != None:
				csv_rows.append((
					item[1],
					item[2],
					self.domain_owners[item[3]]['owner_name'],
					self.domain_owners[item[3]]['country'],
					self.get_domain_owner_lineage_combined_string(item[3])
				))
			else:
				csv_rows.append((item[1],item[2],'Unknown','',''))
		self.write_csv(file_name,csv_rows)
	# generate_per_page_data_flow_report

	def generate_3p_domain_report(self):
		"""
		this queries the db to get all elements, domains, and domain owners
		next they are counted to find the most common
		and formatted to csv rows and returned
		"""
		print('\t==============================')
		print('\t Processing 3P Domains Report ')
		print('\t==============================')

		for tld in self.top_tlds:
			csv_rows = []
			csv_rows.append(('Percent Total','Domain','Owner','Owner Country', 'Owner Lineage'))

			if tld[0]:
				tld_filter = tld[0]
				file_name = tld[0]+'-3p_domains.csv'
			else:
				tld_filter = None
				file_name = '3p_domains.csv'

			total_pages = tld[1]

			all_3p_domains = []
			for item in self.sql_driver.get_3p_domain_owners(tld_filter):
				all_3p_domains.append((item[1],item[2]))

			# if num_results is None we get everything, otherwise stops at limit
			for item in self.get_most_common_sorted(all_3p_domains)[:self.num_results]:
				# this condition has to specify != None, b/c otherwise it will skip values of 0
				if item[0][1] != None:
					owner_name = self.domain_owners[item[0][1]]['owner_name']
					owner_country = self.domain_owners[item[0][1]]['country']
					owner_lineage = self.get_domain_owner_lineage_combined_string(item[0][1])
				else:
					owner_name = 'Unknown'
					owner_country = ''
					owner_lineage = ''

				csv_rows.append((
					round((item[1]/total_pages)*100,self.num_decimals),
					item[0][0],
					owner_name,
					owner_country,
					owner_lineage
				))
			self.write_csv(file_name,csv_rows)
	# generate_3p_domain_report

	def generate_3p_element_report(self,element_type=None):
		"""
		this queries the db to get all elements, domains, or domain owners
		next they are counted to find the most common
		and formatted to csv rows and returned
		"""
		if element_type == 'javascript':
			print('\t=================================')
			print('\t Processing 3P Javascript Report ')
			print('\t=================================')
		elif element_type == 'image':
			print('\t=============================')
			print('\t Processing 3P Images Report ')
			print('\t=============================')
		else:
			print('\t==============================')
			print('\t Processing 3P Element Report ')
			print('\t==============================')
		
		for tld in self.top_tlds:
			total_pages = tld[1]

			csv_rows = []
			csv_rows.append(('Percent Total','Element','Extension','Type','Domain','Owner','Owner Country','Owner Lineage'))

			if tld[0]:
				tld_filter = tld[0]
				if element_type:
					file_name = tld[0]+'-3p_'+element_type+'.csv'
				else:
					file_name = tld[0]+'-3p_element.csv'
			else:
				tld_filter = None
				if element_type:
					file_name = '3p_'+element_type+'.csv'
				else:
					file_name = '3p_element.csv'

			all_3p_elements = []
			for item in self.sql_driver.get_3p_elements(tld_filter, element_type):
				# we need to drop off the first element returned here
				# perhaps tho it should happen insql?

				all_3p_elements.append((item[1],item[2],item[3],item[4],item[5]))

			# if num_results is None we get everything, otherwise stops at limit
			for item in self.get_most_common_sorted(all_3p_elements)[:self.num_results]:
				# this condition has to specify != None, b/c otherwise it will skip values of 0
				if item[0][4] != None:
					owner_name = self.domain_owners[item[0][4]]['owner_name']
					owner_country = self.domain_owners[item[0][4]]['country']
					owner_lineage = self.get_domain_owner_lineage_combined_string(item[0][4])
				else:
					owner_name = 'Unknown'
					owner_country = ''
					owner_lineage = ''

				csv_rows.append((
					round((item[1]/total_pages)*100,self.num_decimals),
					item[0][0],
					item[0][1],
					item[0][2],
					item[0][3],
					owner_name,
					owner_country,
					owner_lineage
				))
			self.write_csv(file_name,csv_rows)
	# generate_3p_element_report

	def generate_data_transfer_report(self):
		"""
		these reports tell us how much data was transferred across several dimensions
		"""
		
		print('\t==================================')
		print('\t Processing Data Transfer Reports ')
		print('\t==================================')
	

		for tld in self.top_tlds:
			# set up filter and file names
			if tld[0]:
				tld_filter = tld[0]
				summary_file_name 		= tld[0]+'-data_xfer_summary.csv'
				domain_file_name		= tld[0]+'-data_xfer_by_domain.csv'
				aggregated_file_name	= tld[0]+'-data_xfer_aggregated.csv'
			else:
				tld_filter = None
				summary_file_name 		= 'data_xfer_summary.csv'
				domain_file_name		= 'data_xfer_by_domain.csv'
				aggregated_file_name	= 'data_xfer_aggregated.csv'

			# get the data from db, tuple of (element_domain, size, is_3p (boolean), domain_owner_id)
			element_sizes = self.sql_driver.get_element_sizes(tld_filter=tld_filter)

			# initialize vars
			first_party_data = 0
			third_party_data = 0
			total_data 		 = 0
			
			# need Counter object, allows sorting later
			domain_data	= collections.Counter()
			owner_data 	= collections.Counter()
			
			# process each row
			for item in element_sizes:

				element_domain	= item[0]
				element_size 	= item[1]
				element_is_3p 	= item[2]
				domain_owner_id = item[3]

				# this is the measure of all data downloaded
				total_data += element_size

				# measures for third and first party data
				if element_is_3p:
					third_party_data += element_size
				else:
					first_party_data += element_size

				# data by domain, increment if already in there, otherwise new entry
				if element_domain in domain_data:
					domain_data[element_domain] += element_size
				else:
					domain_data[element_domain] = element_size

				# only if we know the owner, increment
				if domain_owner_id:
					for lineage_id in self.get_domain_owner_lineage_ids(domain_owner_id):
						if lineage_id in owner_data:
							owner_data[lineage_id] += element_size
						else:
							owner_data[lineage_id] = element_size

			# output data to csv
			summary_data_csv = []
			summary_data_csv.append(('Party','Percent Total','Data Transfered (bytes)'))
			summary_data_csv.append(('All','100',total_data))
			summary_data_csv.append((
				'First', 
				round((first_party_data/total_data)*100, self.num_decimals),
				first_party_data))
			summary_data_csv.append((
				'Third', 
				round((third_party_data/total_data)*100, self.num_decimals),
				third_party_data))

			self.write_csv(summary_file_name, summary_data_csv)
			
			# sort and output ranked data
			domain_data = domain_data.most_common()
			domain_data.sort()
			domain_data.sort(reverse=True, key=lambda item:item[1])

			# for csv data
			domain_data_csv = []
			domain_data_csv.append(('Percent Total','Domain','Data Transfered (bytes)'))

			# if num_results is None we get everything, otherwise stops at limit
			for item in domain_data[:self.num_results]:
				domain_data_csv.append((
					round((item[1]/total_data)*100,self.num_decimals),
					item[0],
					item[1]))
			self.write_csv(domain_file_name, domain_data_csv)

			owner_data 	= self.get_most_common_sorted(owner_data)
			owner_data_csv = []
			owner_data_csv.append(('Percent Total','Owner','Owner Country','Owner Lineage','Data Transfered (bytes)'))
			# get results for all known owners
			for item in owner_data:
				owner_data_csv.append((
					round((item[1]/total_data)*100,self.num_decimals),
					self.domain_owners[item[0]]['owner_name'],
					self.domain_owners[item[0]]['country'],
					self.get_domain_owner_lineage_combined_string(item[0]),
					item[1]
				))
			self.write_csv(aggregated_file_name, owner_data_csv)
	# generate_data_transfer_report

	def generate_network_report(self):
		"""
		this report generates data necessary for graph/network analysis by
			outputting a list of page domains and the elements/owners they connect to
		"""

		print('\t=========================')
		print('\t Processing Network Ties ')
		print('\t=========================')

		# put output here
		csv_rows = []
		
		# header row for csv		
		csv_rows.append(('Page Domain','3P Element Domain','3P Domain Owner','3P Domain Owner Country'))
		
		# sql_driver.get_network_ties returns a set of tuples in the format
		#	(page domain, element domain, element domain owner id)
		#	we just go through this data to produce the report
		
		for item in self.sql_driver.get_3p_network_ties():
			# if a page has no elements, edge[1] will be 'None' so we skip it
			#	an alternate approach would be to include as orphan nodes
			if item[1]:
				# this condition has to specify != None, b/c otherwise it will skip values of 0
				if item[2] != None:
					csv_rows.append((item[0],item[1],self.domain_owners[item[2]]['owner_name'],self.domain_owners[item[2]]['country']))
				else:
					csv_rows.append((item[0],item[1],'Unknown',''))
		self.write_csv('network.csv', csv_rows)
	# generate_network_report
# Analyzer
