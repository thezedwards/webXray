# standard python libs
import os
import re
import json

# custom webxray classes
from webxray.ParseURL import ParseURL

# browsers
from webxray.PhantomDriver	import PhantomDriver
from webxray.ChromeDriver	import ChromeDriver

class SingleScan:
	"""
	Loads and analyzes a single page, print outputs to cli
	Very simple and does not require a db being configured
	"""

	def __init__(self, browser_type):
		self.url_parser		= ParseURL()
		self.browser_type 	= browser_type
		self.domain_owners 	= {}
		self.id_to_owner	= {}
		self.id_to_parent	= {}

		# set up the domain ownership dictionary
		for item in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/domain_owners/domain_owners.json', 'r', encoding='utf-8')):
			self.id_to_owner[item['id']] 	= item['owner_name']
			self.id_to_parent[item['id']] 	= item['parent_id']
			for domain in item['domains']:
				self.domain_owners[domain] = item['id']
	# end init

	def get_lineage(self, id):
		"""
		Find the upward chain of ownership for a given domain.
		"""
		if self.id_to_parent[id] == None:
			return [id]
		else:
			return [id] + self.get_lineage(self.id_to_parent[id])
	# end get_lineage

	def execute(self, url, browser_wait):
		"""
		Main function, loads page and analyzes results.
		"""

		print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
		print('Single Site Test On: %s' % url)
		print('\tBrowser type is %s' % self.browser_type)
		print('\tBrowser wait time is %s seconds' % browser_wait)

		# make sure it is an http(s) address
		if not re.match('^https?://', url): 
			print('\tNot a valid url, aborting')
			return None

		# import and set up specified browser driver
		if self.browser_type == 'phantomjs':
			browser_driver 	= PhantomDriver()
		elif self.browser_type == 'chrome':
			browser_driver 	= ChromeDriver()
			chrome_ua = browser_driver.get_ua_for_headless()
			browser_driver 	= ChromeDriver(ua=chrome_ua)

		# attempt to get the page
		browser_output = browser_driver.get_webxray_scan_data(url, browser_wait)

		# if there was a problem we print the error
		if browser_output['success'] == False:
			print('\t\t%-50s Browser Error: %s' % (url[:50], browser_output['result']))
			return
		else:
			browser_output = browser_output['result']

		# get the ip, fqdn, domain, pubsuffix, and tld from the URL
		# we need the domain to figure out if cookies/elements are third-party
		origin_ip_fqdn_domain_pubsuffix_tld	= self.url_parser.get_ip_fqdn_domain_pubsuffix_tld(url)

		# if we can't get page domain info we bail out
		if origin_ip_fqdn_domain_pubsuffix_tld is None:
			print('could not parse origin domain')
			return None

		origin_ip 			= origin_ip_fqdn_domain_pubsuffix_tld[0]
		origin_fqdn 		= origin_ip_fqdn_domain_pubsuffix_tld[1]
		origin_domain 		= origin_ip_fqdn_domain_pubsuffix_tld[2]
		origin_pubsuffix 	= origin_ip_fqdn_domain_pubsuffix_tld[3]
		origin_tld 			= origin_ip_fqdn_domain_pubsuffix_tld[4]

		print('\n\t------------------{ URL }------------------')
		print('\t'+url)
		print('\n\t------------------{ Final URL }------------------')
		print('\t'+browser_output['final_url'])
		print('\n\t------------------{ Domain }------------------')
		print('\t'+origin_domain)
		print('\n\t------------------{ Seconds to Complete Download }------------------')
		print('\t%s' % (browser_output['load_time']/1000))
		print('\n\t------------------{ 3rd Party Cookies }------------------')
		cookie_list = []
		for cookie in browser_output['cookies']:
			# get domain, pubsuffix, and tld from cookie
			# we have to append http b/c the parser will fail, this is a lame hack, should fix
			cookie_ip_fqdn_domain_pubsuffix_tld	= self.url_parser.get_ip_fqdn_domain_pubsuffix_tld('http://'+cookie['domain'])

			# something went wrong, but we continue to go process the elements
			if cookie_ip_fqdn_domain_pubsuffix_tld is None:
				print('could not parse cookie')
				continue

			# otherwise, everything went fine
			cookie_ip 			= cookie_ip_fqdn_domain_pubsuffix_tld[0]
			cookie_fqdn 		= cookie_ip_fqdn_domain_pubsuffix_tld[1]
			cookie_domain 		= cookie_ip_fqdn_domain_pubsuffix_tld[2]
			cookie_pubsuffix 	= cookie_ip_fqdn_domain_pubsuffix_tld[3]
			cookie_tld 			= cookie_ip_fqdn_domain_pubsuffix_tld[4]

			# print external cookies
			if origin_domain not in cookie_domain:
				cookie_list.append(re.sub('^\.', '', cookie['domain'])+' -> '+cookie['name'])

		cookie_list.sort()
		count = 0
		for cookie in cookie_list:
			count += 1
			print('\t%s) %s' % (count,cookie))

		print('\n\t------------------{ 3p Domains Requested }------------------')
		element_domains = []

		for request in browser_output['processed_requests']:
			# if the request starts with 'data'/etc we can't parse tld anyway, so skip
			if re.match('^(data|about|chrome).+', request):
				continue

			element_ip_fqdn_domain_pubsuffix_tld	= self.url_parser.get_ip_fqdn_domain_pubsuffix_tld(request)

			# problem with this request, bail on it and do the next
			if element_ip_fqdn_domain_pubsuffix_tld is None:
				continue

			element_ip 			= element_ip_fqdn_domain_pubsuffix_tld[0]
			element_fqdn 		= element_ip_fqdn_domain_pubsuffix_tld[1]
			element_domain 		= element_ip_fqdn_domain_pubsuffix_tld[2]
			element_pubsuffix 	= element_ip_fqdn_domain_pubsuffix_tld[3]
			element_tld 		= element_ip_fqdn_domain_pubsuffix_tld[4]
				
			if origin_domain not in element_domain:
				if element_domain not in element_domains:
					element_domains.append(element_domain)
		
		element_domains.sort()

		count = 0
		for domain in element_domains:
			count += 1
			if domain in self.domain_owners:
				lineage = ''
				for item in self.get_lineage(self.domain_owners[domain]):
					lineage += self.id_to_owner[item]+' > '
				print('\t%s) %s [%s]' % (count, domain, lineage[:-3]))
			else:
				print('\t%s) %s [Unknown Owner]' % (count, domain))
	# end execute
# end SingleScan
