# standard python packages
import os
import hashlib
import sqlite3
import datetime

class SQLiteDriver:
	"""
	this class handles all of the database work, no sql is to be found 
		elsewhere in the code base aside from other db drivers
	"""

	def __init__(self, db_name = '', db_prefix = 'wbxr_'):
		"""
		set the root path for the db directory since sqlite dbs are not contained in a server
		if db_name is specified, set up global connection
		"""
		self.db_root_path = os.path.dirname(os.path.abspath(__file__))+'/resources/db/sqlite/'

		# the db_prefix can be overridden if you like
		self.db_prefix = db_prefix
		
		if db_name != '':
			self.db_name = self.db_prefix+db_name+'.db'
			self.db_conn = sqlite3.connect(self.db_root_path+self.db_name,detect_types=sqlite3.PARSE_DECLTYPES)
			self.db = self.db_conn.cursor()
	# __init__

	#-----------------#
	# GENERAL PURPOSE #
	#-----------------#

	def md5_text(self,text):
		"""
		this class is unique to the sqlite driver as md5 is not built in
		"""
		try:
			return hashlib.md5(text.encode('utf-8')).hexdigest()
		except:
			return None
	# md5_text

	def db_switch(self, db_name):
		"""
		connect to a new db, in sqlite this requires loading the db from disk
		"""

		# close existing connection
		self.close()

		# open the new connection
		self.db_name = self.db_prefix+db_name
		self.db_conn = sqlite3.connect(self.db_root_path+self.db_name+'.db',detect_types=sqlite3.PARSE_DECLTYPES)
		self.db = self.db_conn.cursor()
		return True
	# db_switch

	def fetch_query(self, query):
		"""
		allows executing raw queries, very unsafe and should be disabled in public-facing systems
		"""
		self.db.execute(query)
		return self.db.fetchall()
	# fetch_query

	def commit_query(self, query):
		"""
		allows executing raw queries, very unsafe and should be disabled in public-facing systems
		"""
		self.db.execute(query)
		self.db_conn.commit()
		return True
	# commit_query

	def check_db_exist(self, db_name):
		"""
		before creating a new db make sure it doesn't already exist, uses specified prefix
		"""
		dbs = os.listdir(self.db_root_path)
		if self.db_prefix+db_name+'.db' in dbs:
			return True
		else:
			return False
	# check_db_exist

	def build_filtered_query(self,query,filters):
		"""
		takes a base query + filters and returns
		a query with appropraite 'where'/'and' placements
		only needed in cases where query conditionals get particularly ugly
		"""
		if filters:
			for index,filter in enumerate(filters):
				if index == 0:
					query += ' WHERE '+filter
				else:
					query += ' AND '+filter
		return query
	# build_filtered_query

	def get_wbxr_dbs_list(self):
		"""
		return database names with the class-specified prefix, stripped of prefix, default is 'wbxr_'
		"""
		wbxr_dbs = []
		for item in os.listdir(self.db_root_path):
			if item[0:len(self.db_prefix)] == self.db_prefix:
				wbxr_dbs.append(item[len(self.db_prefix):-3])
		return wbxr_dbs
	# get_wbxr_dbs_list

	def close(self):
		"""
		very important, frees up connections to db
		"""

		# it is possible a database is not open, in which case we silently fail
		try:
			self.db.close()
			self.db_conn.close()
		except:
			pass
	# close

	#-------------#
	# DB Creation #
	#-------------#

	def create_wbxr_db(self, db_name):
		"""
		create empty db using the sql init file in /webxray/resources/db/sqlite
		and update the current db
		"""

		# update global db_name
		self.db_name = self.db_prefix+db_name

		# make sure we don't overwrite existing db
		if os.path.isfile(self.db_root_path+self.db_name+'.db'):
			print('****************************************************************************')
			print('ERROR: Database exists, SQLite will overwrite existing databases, aborting! ')
			print('****************************************************************************')
			exit()
		else:
			# create new db here, if it does not exist yet it gets created on the connect
			self.db_conn = sqlite3.connect(self.db_root_path+self.db_name+'.db',detect_types=sqlite3.PARSE_DECLTYPES)
			self.db = self.db_conn.cursor()

			# initialize webxray formatted database
			db_init_file = open(self.db_root_path+'sqlite_db_init.schema', 'r')
			for query in db_init_file:
				# skip lines that are comments
				if "-" in query[0]: continue
				# lose whitespace
				query = query.strip()
				# push to db
				self.db.execute(query)
				self.db_conn.commit()
	# create_wbxr_db

	#-----------------------#
	# INGESTION AND STORING #
	#-----------------------#	

	def get_page_last_accessed_by_browser_type(self,url,browser_type=None):
		"""
		see when the page was last accessed, if the page is not in the db yet, this will return none
		additionaly you can specifify which browser to check for
		if no browser is specified just return the last time it was accessed
		"""
		if browser_type == None:
			self.db.execute('SELECT accessed,browser_type FROM page WHERE start_url_md5 = ? ORDER BY accessed DESC LIMIT 1', (self.md5_text(url),))
		else:
			self.db.execute('SELECT accessed,browser_type FROM page WHERE start_url_md5 = ? AND browser_type = ? ORDER BY accessed DESC LIMIT 1', (self.md5_text(url),browser_type))

		try:
			return (datetime.datetime.strptime(self.db.fetchone()[0], "%Y-%m-%d %H:%M:%S.%f"), self.db.fetchone()[1])
		except:
			return None
	# get_page_last_accessed_by_browser_type


	def page_exists(self, url):
		"""
		checks if page exists at all, regardless of number of occurances
		"""
		self.db.execute("SELECT COUNT(*) FROM page WHERE start_url_md5 = ?", (self.md5_text(url),))
		if self.db.fetchone()[0]:
			return True
		else:
			return False
	# page_exists

	def add_domain(self, ip_addr, fqdn, domain, pubsuffix, tld):
		"""
		add a new domain record to db, ignores duplicates
		returns id of newly added domain
		"""
		self.db.execute("""
			INSERT OR IGNORE INTO domain (
				ip_addr, 
				fqdn_md5, fqdn,
				domain_md5, domain, 
				pubsuffix_md5, pubsuffix, 
				tld_md5, tld)
			VALUES (
				?,
				?,?,
				?,?,
				?,?,
				?,?)""", 
			(
				ip_addr, 
				self.md5_text(fqdn), fqdn,
				self.md5_text(domain), domain, 
				self.md5_text(pubsuffix), pubsuffix, 
				self.md5_text(tld), tld
			)
		)
		self.db_conn.commit()
		self.db.execute("SELECT id FROM domain WHERE fqdn_md5 = ?", (self.md5_text(fqdn),))
		return self.db.fetchone()[0]
	# add_domain

	def add_page(self,
		browser_type, browser_version, browser_wait,
		title, meta_desc, 
		start_url, final_url,
		priv_policy_url,
		priv_policy_url_text,
		is_ssl, source, 
		load_time, domain_id):
		"""
		page is unique on 'accessed' and 'start_url_md5', in the unlikely event of a collision this will fail
		ungracefully, which is desired as the bug would be major

		returns id of newly added page

		note that sqlite does not have an automatic timestamp so we have to create a datetime object
		"""

		accessed = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

		self.db.execute("""INSERT INTO page (
				title, meta_desc, 
				browser_type, browser_version, browser_wait,
				start_url_md5, start_url,
				final_url_md5, final_url,
				priv_policy_url_md5, priv_policy_url, 
				priv_policy_url_text,
				is_ssl, source, 
				load_time, domain_id,
				accessed
	 	) VALUES (
		 		?,?,
		 		?,?,?,
		 		?,?,
		 		?,?,
		 		?,?,
		 		?,
		 		?,?,
		 		?,?,
		 		?
		)""", 
		(		title, meta_desc, 
				browser_type, browser_version, browser_wait,
				self.md5_text(start_url), start_url, 
				self.md5_text(final_url), final_url,
				self.md5_text(priv_policy_url), priv_policy_url,
				priv_policy_url_text,
				is_ssl, source, 
				load_time, domain_id,
				accessed)
		)
		self.db_conn.commit()
		
		# return id of record with this start_url and accessed time
		self.db.execute("SELECT id FROM page WHERE start_url_md5 = ? AND accessed = ?", (self.md5_text(start_url),accessed))

		return self.db.fetchone()[0]
	# add_page

	def add_element(self, 
		page_id,
		full_url, element_url,
		is_3p, is_ssl,
		received,
		referer, page_domain_in_referer,
		start_time_offset, load_time, 
		status, status_text, 
		content_type, body_size, 
		request_headers, response_headers, 
		file_md5, extension,
		type, args, 
		domain_id):
		"""
		stores an element, should fail ungracefully if the page_id or domain_id does not exist

		returns nothing
		"""
		self.db.execute("""INSERT OR IGNORE INTO element (
				page_id,
				full_url_md5, full_url,
				element_url_md5, element_url,
				is_3p, is_ssl,
				received, 
				referer, page_domain_in_referer, 
				start_time_offset, load_time, 
				status, status_text, 
				content_type, body_size, 
				request_headers, response_headers, 
				file_md5, extension,
				type, args, 
				domain_id) 
		VALUES (
				?,
				?, ?,
				?, ?,
				?, ?,
				?,
				?, ?,
				?, ?,
				?, ?,
				?, ?,
				?, ?,
				?, ?,
				?, ?, 
				?)""", 
		(		page_id,
				self.md5_text(full_url), full_url,
				self.md5_text(element_url), element_url,
				is_3p, is_ssl,
				received, 
				referer, page_domain_in_referer, 
				start_time_offset, load_time, 
				status, status_text, 
				content_type, body_size, 
				request_headers, response_headers, 
				file_md5, extension,
				type, args, 
				domain_id)
		)
		self.db_conn.commit()
	# add_element

	def add_cookie(self, 
		page_id,
		name, secure, path, 
		domain, httponly, 
		expiry, value, is_3p, 
		domain_id):
		"""
		stores a cookie, should fail ungracefully if the page_id or domain_id does not exist

		returns nothing
		"""
		self.db.execute("""
			INSERT INTO cookie (
				page_id,
				name, secure, path, 
				domain, httponly, 
				expiry, value, is_3p, 
				domain_id)
			VALUES (?,?,?,?,?,?,?,?,?,?)""",
			(	page_id,
				name, secure, path, 
				domain, httponly, 
				expiry, value, is_3p, 
				domain_id
			)
		)
		self.db_conn.commit()
	# add_cookie

	def log_error(self, url, msg):
		"""
		general purpose error logging, unique on url/msg
		"""
		self.db.execute("INSERT OR IGNORE INTO error (url, msg, timestamp) VALUES (?,?,?)", (url, msg,datetime.datetime.now()))
		self.db_conn.commit()
	# log_error

	#------------------------#
	# ANALYSIS AND REPORTING #
	#------------------------#	

	# the first step for analysis is to assign owners to domains so we can track
	# corporate ownership structures; the next few functions update the database to do this after
	# the collection has been done
	
	def reset_domain_owners(self):
		"""
		when the domain ownership is updated it is neccessary to flush existing mappings
		first reset all the domain owner records then clear the domain_owner db
		"""
		self.db.execute('UPDATE domain SET domain_owner_id=NULL;')
		self.db.execute('DELETE FROM domain_owner WHERE id != 1;')
		return True
	# reset_domain_owners

	def add_domain_owner(self, 
			id, parent_id, 
			name, aliases, 
			homepage_url, privacy_policy_url,
			notes, country):
		"""
		create entries for the domain owners we are analyzing
		"""
		self.db.execute("""
			INSERT OR IGNORE INTO domain_owner (
				id, parent_id, 
				name, aliases, 
				homepage_url, privacy_policy_url,
				notes, country
			) VALUES (?,?,?,?,?,?,?,?)""", 
			(id, parent_id, name, aliases, homepage_url, privacy_policy_url, notes, country)
		)
		self.db_conn.commit()
	# add_domain_owner

	def update_domain_owner(self, id, domain):
		"""
		link the domains to the owners
		"""
		self.db.execute('UPDATE OR IGNORE domain SET domain_owner_id = ? WHERE domain_md5 = ?', (id, self.md5_text(domain)))
		self.db_conn.commit()
		return True
	# update_domain_owner

	def get_all_domain_owner_data(self):
		"""
		returns everything from the domain_owner table
		which is relatively small and can be a global 
		var elsewhere

		in cases where the user does not wish the update the domain owners
		with a fresh copy of the domain_owners.json file this will
		provide the same mappings as were used originally and is important
		for historical reporting
		"""
		self.db.execute("""
			SELECT 
				id, parent_id, name,
				aliases, homepage_url, privacy_policy_url,
				notes, country
			FROM
				domain_owner
			""")
		return self.db.fetchall()
	# get_all_domain_owner_data

	def get_all_tlds(self, type='tld'):
		"""
		get all tlds from page domains, type can be 'tld' or 'pubsuffix', will crash on invalid type
		"""
		if type == 'tld':
			query = 'SELECT domain.tld from page LEFT JOIN domain ON page.domain_id = domain.id'
		elif type == 'pubsuffix':
			query = 'SELECT domain.pubsuffix from page LEFT JOIN domain ON page.domain_id = domain.id'
		
		self.db.execute(query)
		return self.db.fetchall()
	# get_all_tlds

	def get_pages_ok_count(self, is_ssl = False):
		"""
		simple way to query number of pages in db, can filter on ssl
		"""
		if is_ssl is True:
			self.db.execute('SELECT COUNT(*) FROM page WHERE is_ssl = 1')
		else:
			self.db.execute('SELECT COUNT(*) FROM page')
		return self.db.fetchone()[0]
	# get_pages_ok_count

	def get_pages_load_times(self):
		"""
		returns a list of all the load times of each page, data is miliseconds in integer form
		"""
		load_times = []
		self.db.execute('SELECT load_time FROM page')
		for item in self.db.fetchall():
			load_times.append(item[0])
		return load_times
	# get_pages_load_times

	def get_pages_noload_count(self):
		"""
		to get all pages that haven't loaded we first pull the errors, then check
			if they exist in the main page table; in the event we have tried one or more
			attempts there may both be an error message from a first attempt, but on
			an additional attempt, the page is loaded - this function makes sure we only
			count pages that didn't subsequently get loaded

		NOTE: for time-series collections this overall behavior may be undesirable
		"""
		noload_count = 0
		self.db.execute('SELECT DISTINCT url FROM error WHERE msg = "Unable to load page"')
		for item in self.db.fetchall():
			if not self.page_exists(item[0]):
				noload_count += 1
		return noload_count
	# get_pages_noload_count

	def get_total_errors_count(self):
		"""
		simple way to see how many errors encounted, can be anything logged
		"""
		self.db.execute('SELECT COUNT(*) FROM error')
		return self.db.fetchone()[0]
	# get_total_errors_count

	def get_total_cookie_count(self, is_3p = False):
		"""
		total cookies in the db, can be filtered on 3p only
		"""
		if is_3p:
			self.db.execute('SELECT COUNT(*) FROM cookie WHERE is_3p = 1')
		else:
			self.db.execute('SELECT COUNT(*) FROM cookie')
		return self.db.fetchone()[0]
	# get_total_cookie_count

	def get_total_request_count(self, received = False, party = None, is_ssl = None):
		"""
		count of total requests in db, can be filtered by party (first or third)
		as well as if the element was successfully received after the request was made
		
		by default returns all
		"""

		# base query
		query = 'SELECT COUNT(*) FROM element'

		# add filters
		filters = []

		if received:
			filters.append('received = 1')

		if party == 'third':
			filters.append('is_3p = 1')
		if party == 'first':
			filters.append('is_3p = 0')

		if is_ssl:
			filters.append('is_ssl = 1')

		# execute and return
		self.db.execute(self.build_filtered_query(query,filters))
		return self.db.fetchone()[0]
	# get_total_request_count

	def get_element_sizes(self, tld_filter = None):
		"""
		return tuple of (element_domain, size, is_3p (boolean), domain_owner_id)

		can filter on page tld
		"""
		if tld_filter:
			self.db.execute("""
				SELECT element_domain.domain,element.body_size,element.is_3p,element_domain.domain_owner_id
				FROM element 
				JOIN domain element_domain ON element_domain.id = element.domain_id
				JOIN page on element.page_id = page.id
				JOIN domain page_domain ON page_domain.id = page.domain_id
				WHERE element.body_size IS NOT NULL
				AND page_domain.tld = '%s'
			""" % tld_filter)			
		else:
			self.db.execute("""
				SELECT element_domain.domain,element.body_size,element.is_3p,element_domain.domain_owner_id
				FROM element 
				JOIN domain element_domain on element_domain.id = element.domain_id
				WHERE element.body_size IS NOT NULL
			""")
		
		return self.db.fetchall()
	# get_element_sizes

	def get_complex_page_count(self, tld_filter = None, type = None, tracker_domains = None):
		"""
		given various types of analyses we may want to count how many pages meet
			certain criteria, this function handles creating complex sql queries
		
		note that in order to avoid counting the same item more than
			once for a given page we need to use a distinct query against page_id 
		
		while it is better to have logic in elsewhere, some logic has to be here
			as building the queries this way is specific to different sql flavors
		
		FOR EXPERTS:
		by defining 'tracker_domains' to be those domains which link X number of 
			sites, we can change our reports to be bounded by those domains. note the 
			list of domains comes from 'get_tracker_domains' in Analyzer.py
		"""

		# holder for filters
		filters = []

		# set up base query, build filter list
		if type == 'elements' or type =='javascript':
			query = '''SELECT COUNT(DISTINCT page_id) FROM element
				JOIN page ON page.id = element.page_id
				JOIN domain page_domain ON page_domain.id = page.domain_id
				JOIN domain element_domain ON element_domain.id = element.domain_id'''
			filters.append('element.is_3p = 1')
		elif type == 'cookies':
			query = '''SELECT COUNT(DISTINCT cookie.page_id) FROM cookie
				JOIN page ON page.id = cookie.page_id
				JOIN domain page_domain ON page_domain.id = page.domain_id
				JOIN domain cookie_domain ON cookie_domain.id = cookie.domain_id'''
			filters.append('cookie.is_3p = 1')
		else:
			query = '''
				SELECT COUNT(*) FROM page 
				JOIN domain page_domain ON page_domain.id = page.domain_id
			'''

		# addtional filtering
		if type == 'javascript': filters.append("element.type = 'javascript'")
		if tld_filter: filters.append("page_domain.tld = '%s'" % tld_filter)

		# special tracker filtering
		if tracker_domains:
			# if we set a very high threshold it is possible we have no tracking domains
			#	in this case our count will be zero, so we do that and return
			if len(tracker_domains) == 0:
				return 0
			# otherwise we build the query with a super long conditional as 
			#	we have tracker domains
			tracker_filter = '('
			for tracker_domain_name in tracker_domains:
				if type == 'cookies':
					tracker_filter += "cookie_domain.domain = '%s' OR " % tracker_domain_name
				else:
					tracker_filter += "element_domain.domain = '%s' OR " % tracker_domain_name
			tracker_filter = tracker_filter[:-3]
			tracker_filter += ')'
			filters.append(tracker_filter)

		self.db.execute(self.build_filtered_query(query,filters))
		return self.db.fetchone()[0]
	# get_complex_page_count

	def get_page_ids(self, tld_filter=None):
		"""
		basic utility function, allows to filter on page tld
		"""
		if tld_filter:
			self.db.execute('SELECT page.id FROM page JOIN domain ON page.domain_id = domain.id WHERE domain.tld = ?', (tld_filter,))
		else:
			self.db.execute('SELECT page.id FROM page')
		return self.db.fetchall()
	# get_page_ids
	
	def get_all_page_id_3p_domain_owner_ids(self,tld_filter=None):
		"""
		return mapping of all page to third-party element owner ids
		ignores domains where owners are not known
		"""
		if tld_filter:
			self.db.execute("""
				SELECT DISTINCT page.id, element_domain.domain_owner_id from page
				JOIN element ON element.page_id = page.id
				JOIN domain element_domain ON element.domain_id = element_domain.id
				JOIN domain page_domain ON page.domain_id = page_domain.id
				WHERE element.is_3p = 1
				AND element_domain.domain_owner_id IS NOT NULL
				AND page_domain.tld = ?
			""", (tld_filter,))
		else:
			self.db.execute("""
				SELECT DISTINCT page.id, element_domain.domain_owner_id from page
				JOIN element ON element.page_id = page.id
				JOIN domain element_domain ON element.domain_id = element_domain.id
				WHERE element.is_3p = 1
				AND element_domain.domain_owner_id IS NOT NULL
			""")

		return self.db.fetchall()
	# get_page_3p_domain_ids

	def get_all_pages_3p_domains_and_owners(self):
		"""
		get a full report for each page of distinct domains requested along with owner id
		owner id can then be used to find parent owners/etc
		also includes pages where domain owner is not known
		"""
		self.db.execute("""
			SELECT DISTINCT page.start_url,page.final_url,element_domain.fqdn,element_domain.domain_owner_id from page
			JOIN element ON element.page_id = page.id
			JOIN domain element_domain ON element.domain_id = element_domain.id
			WHERE element.is_3p = 1
			ORDER BY page.final_url, element_domain.domain_owner_id
		""")
		return self.db.fetchall()
	# get_all_pages_3p_domains_and_owners

	def get_3p_domain_owners(self, tld_filter = None):
		"""
		get all occurances of element domains and their owners for domain report

		note that in order to avoid counting the same item more than
			once for a given page we need to use a distinct query against page_id 
			this field is subsequently ignored by the calling function
		"""
		query = """
			SELECT DISTINCT page.id, element_domain.domain, element_domain.domain_owner_id FROM page 
			LEFT JOIN element ON element.page_id = page.id
			LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
			LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
			WHERE element.is_3p = 1
		"""

		if tld_filter:
			self.db.execute(query + ' AND page_domain.tld = ?', (tld_filter,))
		else:
			self.db.execute(query)
		return self.db.fetchall()
	# get_3p_domain_owners

	def get_3p_elements(self, tld_filter = None, element_type = None):
		"""
		find the most frequently occuring 3p elements
		according to different criteria
		"""

		base_query = """	
				SELECT DISTINCT 
					page.id, element.element_url, element.extension, 
					element.type, element_domain.domain, domain_owner.id
				FROM page 
				LEFT JOIN element ON element.page_id = page.id
				LEFT JOIN domain page_domain ON page.domain_id = page_domain.id
				LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
				LEFT JOIN domain_owner on domain_owner.id = element_domain.domain_owner_id
				WHERE element.is_3p = 1
		"""

		if tld_filter and element_type:
			self.db.execute(base_query + ' AND page_domain.tld = ? AND element.type = ?', (tld_filter, element_type))
		elif tld_filter:
			self.db.execute(base_query + ' AND page_domain.tld = ?', (tld_filter,))
		elif element_type:
			self.db.execute(base_query + ' AND element.type = ?', (element_type,))
		else:
			self.db.execute(base_query)
		return self.db.fetchall()
	# get_3p_elements

	def get_page_domain_element_domain_pairs(self):
		"""
		returns all of the unique pairings between the domain of a page and that
			of an element
		"""
		query = """
				SELECT DISTINCT page_domain.domain, element_domain.domain 
				FROM page
				LEFT JOIN element ON element.page_id = page.id
				LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
				LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
		"""	
		self.db.execute(query)
		return self.db.fetchall()
	# get_page_domain_element_domain_pairs

	def get_page_id_page_domain_element_domain(self, tld_filter):
		"""
		return data needed for determing average number of 3p per page, etc.

		pages with no elements return a single record with (page.final_url, 'None')
			this is necessary to see which pages have no trackers and why we do not
			use a tracker filter here
		"""
		
		query = '''
			SELECT DISTINCT page.id, page_domain.domain, element_domain.domain
			FROM page
			JOIN domain page_domain ON page_domain.id = page.domain_id
			JOIN element ON element.page_id = page.id
			JOIN domain element_domain ON element_domain.id = element.domain_id
			WHERE element.is_3p = 1
		'''

		if tld_filter: 
			query += " AND page_domain.tld = '"+tld_filter+"'"
	
		self.db.execute(query)
		return self.db.fetchall()
	# end get_page_element_domain_pairs

	def get_page_id_3p_cookie_id_3p_cookie_domain(self, tld_filter):
		"""
		returns all of the page id and third-party cookie id
		"""
		query = '''
			SELECT DISTINCT page.id, cookie.id, cookie_domain.domain
			FROM page
			JOIN domain page_domain ON page_domain.id = page.domain_id
			JOIN cookie on cookie.page_id = page.id
			JOIN domain cookie_domain ON cookie_domain.id = cookie.domain_id
			WHERE cookie.is_3p = 1
		'''

		if tld_filter: 
			query += " AND page_domain.tld = '"+tld_filter+"'"
	
		self.db.execute(query)
		return self.db.fetchall()
	# get_page_id_3p_cookie_id_3p_cookie_domain

	def get_3p_network_ties(self, domain_owner_is_known = False):
		"""
		returns all of the unique pairings between the domain of a page and that
			of an element
		
		paramater domain_owner_is_known is to only return those elements where we have
			identified the owner
		"""
		query = """
				SELECT DISTINCT page_domain.domain, element_domain.domain, element_domain.domain_owner_id
				FROM page
				LEFT JOIN element ON element.page_id = page.id
				JOIN domain page_domain ON page.domain_id = page_domain.id
				JOIN domain element_domain ON element_domain.id = element.domain_id
				WHERE element.is_3p = 1
		"""
		
		# to limit analysis to domains who we know the owner add following to above query
		if domain_owner_is_known: query += " AND element_domain.domain_owner_id IS NOT NULL "
		
		query += " ORDER BY page_domain.domain, element_domain.domain "
		
		self.db.execute(query)
		return self.db.fetchall()
	# get_3p_network_ties

	def get_3p_element_domain_owner_id_ssl_use(self):
		"""
		for each received third-party request returns
			the domain owner id and true/false value for ssl
		"""
		self.db.execute('''
			SELECT 
				domain_owner.id,
				element.is_ssl
			FROM 
				element 
			JOIN 
				domain on element.domain_id = domain.id 
			JOIN 
				domain_owner on domain.domain_owner_id = domain_owner.id
			WHERE
				element.is_3p = 1
			AND
				element.received = 1
		''')

		return self.db.fetchall()
	# get_3p_element_domain_owner_id_ssl_use
# SQLiteDriver
