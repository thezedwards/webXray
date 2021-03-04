# standard python libs
import os
import re
import json

# custom webxray classes
from webxray.ParseURL import ParseURL

class SingleScan:
	"""
	Loads and analyzes a single page, print outputs to cli
	Very simple and does not require a db being configured
	"""

	def __init__(self):
		self.url_parser		= ParseURL()
		self.domain_owners 	= {}
		self.id_to_owner	= {}
		self.id_to_parent	= {}

		# set up the domain ownership dictionary
		for item in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/domain_owners/domain_owners.json', 'r', encoding='utf-8')):
			if item['id'] == '-': continue

			self.id_to_owner[item['id']] 	= item['name']
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

	def execute(self, url, config):
		"""
		Main function, loads page and analyzes results.
		"""

		print('\t~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
		print('\tSingle Site Test On: %s' % url)
		print('\t - Browser type is %s' % config['client_browser_type'])
		print('\t - Browser max wait time is %s seconds' % config['client_max_wait'])

		# make sure it is an http(s) address
		# if not re.match('^https?://', url): 
		# 	print('\tNot a valid url, aborting')
		# 	return None

		# import and set up specified browser driver
		if config['client_browser_type'] == 'chrome':
			from webxray.ChromeDriver	import ChromeDriver
			browser_driver 	= ChromeDriver(config)
		# elif config['client_browser_type'] == 'basic':
		# 	from webxray.BasicDriver	import BasicDriver
		# 	browser_driver = BasicDriver(config)
		else:
			print('INVALID BROWSER TYPE FOR %s, QUITTING!' % config['client_browser_type'])
			exit()

		# attempt to get the page
		browser_output = browser_driver.get_scan(url)

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
		print('\t %s' % url)
		print('\n\t------------------{ Final URL }------------------')
		print('\t %s' % browser_output['final_url'])
		print('\n\t------------------{ Title }------------------')
		print('\t %s' % browser_output['title'])
		print('\n\t------------------{ Description }------------------')
		print('\t %s' % browser_output['meta_desc'])
		print('\n\t------------------{ Domain }------------------')
		print('\t %s' % origin_domain)
		print('\n\t------------------{ Seconds to Complete Download }------------------')
		print('\t%s' % (browser_output['load_time']))
		print('\n\t------------------{ Cookies }------------------')
		# put relevant fields from cookies into list we can sort
		cookie_list = []
		for cookie in browser_output['cookies']:
			cookie_list.append(cookie['domain']+' -> '+cookie['name']+' -> '+cookie['value'])

		cookie_list.sort()
		for count,cookie in enumerate(cookie_list):
			print(f'\t[{count}] {cookie}')
			
		print('\n\t------------------{ Local Storage }------------------')
		for item in browser_output['dom_storage']:
			print('\t%s (is local: %s): %s' % (item['security_origin'],item['is_local_storage'],item['key']))

		print('\n\t------------------{ Domains Requested }------------------')
		request_domains = set()

		for request in browser_output['requests']:
			# if the request starts with 'data'/etc we can't parse tld anyway, so skip
			if re.match('^(data|about|chrome).+', request['url']):
				continue

			# parse domain from the security_origin
			domain_info = self.url_parser.get_parsed_domain_info(request['url'])
			if domain_info['success'] == False:
				print('\tUnable to parse domain info for %s with error %s' % (request['url'], domain_info['result']))
				continue

			# if origin_domain != domain_info['result']['domain']:
			request_domains.add(domain_info['result']['domain'])
		
		count = 0
		for domain in sorted(request_domains):
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
