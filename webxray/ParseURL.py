# standard python libs
import os
import re
import json
import socket
from urllib.parse import urlsplit

class ParseURL:
	"""
		Given a url string, this class will return the ip address, fully-qualified domain name,
			domain, public suffix, and top-level domain as a tuple.
		Example: "http://sub.domain.example.ac.uk/"
			ip:				xxx.xxx.xxx.xxx
			fqdn:			sub.domain.example.ac.uk
			domain:			example.ac.uk
			public suffix:	ac.uk
			tld:			uk

		Note: the mozilla public suffix list is used for identifying pub suffixes, see https://publicsuffix.org

	"""

	def __init__(self):
		# load up the tld list now as only hit it once this way
		self.pubsuffix_list = self.get_pubsuffix_list()

		# get domain owner data
		self.domain_owners = {}
		domain_owner_data = json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/domain_owners/domain_owners.json', 'r', encoding='utf-8'))
		for item in domain_owner_data:
			# skipping for now, but perhaps find a way to enter this in db?
			if 'revision_date' in item: continue
			for domain in item['domains']:
				self.domain_owners[domain] = item['id']
	# end __init__

	def get_pubsuffix_list(self):
		"""
			this builds a shared list of tuples based on the pubsuffix list; tuples allow for
			quick comparisons of smaller strings
		"""

		# path is relative from root webxray directory
		pubsuffix_raw_list = open(os.path.dirname(os.path.abspath(__file__))+'/resources/pubsuffix/public_suffix_list.dat', mode='r', encoding='utf8')
		pubsuffix_list = []

		for line in pubsuffix_raw_list:
				# the last part of the list is random stuff we don't care about, so stop reading
				if re.match("^// ===BEGIN PRIVATE DOMAINS===", line):break

				# skip lines that are comments or blank, add others to list
				if not re.match("^//.+$|^$", line):
					# remove leading ., !, and * as it screws up regex later
					pubsuffix_string = re.sub('^[\!\*]\.?', '', line.strip())
					
					# convert to idna/ascii/utf-8 for enhanced compatability
					pubsuffix_string = pubsuffix_string.encode('idna').decode('utf-8')

					# convert to a tuple so we can do faster comparisons
					pubsuffix_list.append(tuple(pubsuffix_string.split('.')))
		
		# add the pubsuffix for tor addresses
		pubsuffix_list.append(('onion',))

		# done
		return pubsuffix_list
	# get_pubsuffix_list

	def get_parsed_domain_info(self,url,get_ip_adrr=False):
		"""
			Given a url string, this class will return the ip address, fully-qualified domain name,
				domain, public suffix, and top-level domain as a tuple.
		"""
		
		# first make sure it is actually an https? or wss? request we can parse
		if not (re.match('^(https?|wss?)://.+', url)):
			return({
				'success': False,
				'result': 'Does not appear to be an http or wss address'
			})

		try:
			# try to pull out the fully-qualified domain name (fqdn) from the netloc 
			#	with some regex, handles cases where the port is included (eg 'example.com:1234')
			#	drops leading/trailing '.', etc.
			fqdn = re.search('^(\.+)?(.+?)(:.+)?(\.+)?$', urlsplit(url).netloc).group(2)

			# convert to idna/ascii/utf-8 for enhanced compatability
			fqdn = fqdn.encode('idna').decode('utf-8')
		except:
			return({
				'success': False,
				'result': 'Could not extract fqdn'
			})

		if get_ip_adrr:
			# to see if the fqdn is simply an ip_addr try to load it as such
			# return the IP for all fields even though not strictly 
			# accurate as to field values
			try:
				ip_addr = socket.inet_aton(fqdn)
				return({
					'success': True,
					'result': {
						'ip_addr'			: fqdn,
						'fqdn'				: fqdn,
						'domain'			: fqdn,
						'pubsuffix'			: None,
						'tld'				: None,
						'domain_owner_id'	: None
					}
				})
			except socket.error:
				pass

			# if the fqdn is not an ip_addr we use socket to get the ip_addr
			# this will fail if the host doesn't respond to ping
			# which often happens with cookie domains
			try:
				ip_addr = socket.gethostbyname(fqdn)
			except:
				ip_addr = None
		else:
			ip_addr = None

		# convert what we have to a tuple and match against our list
		domain_tuple = tuple(fqdn.split('.'))
		num_tokens = len(domain_tuple)
		slice_point = 0

		# we keep dropping off the left-most token until we find a match
		# this way we match on "ac.uk" *before* "uk"
		while slice_point < num_tokens-1:
			slice_point += 1
			pubsuffix = domain_tuple[slice_point:]
			if pubsuffix in self.pubsuffix_list:
				# we found the pubsuffix, 1 back is the domain
				domain = domain_tuple[slice_point-1:]
				
				# tld is always the final token
				tld = domain_tuple[num_tokens-1]

				# glue back together domain/pubsuffix
				domain = '.'.join(domain)
				pubsuffix = '.'.join(pubsuffix)

				# found match, see if we have an owner for domain
				if domain in self.domain_owners:
					domain_owner_id = self.domain_owners[domain]
				else:
					domain_owner_id = None

				# return as strings joined on '.'
				return({
					'success': True,
					'result': {
						'ip_addr'			: ip_addr,
						'fqdn'				: fqdn,
						'domain'			: domain,
						'pubsuffix'			: pubsuffix,
						'tld'				: tld,
						'domain_owner_id'	: domain_owner_id
					}
				})

		# if we get to this point nothing else has worked
		return ({
			'success': False,
			'result': 'Unknown error'
		})
	# get_parsed_domain_info

	def get_ip_fqdn_domain_pubsuffix_tld(self,url,get_ip_adrr=True):
		"""
			Given a url string, this class will return the ip address, fully-qualified domain name,
				domain, public suffix, and top-level domain as a tuple.
		"""

		# first make sure it is actually an https? or wss? request we can parse
		if not (re.match('^(https?|wss?)://.+', url)):
			return None

		try:
			# try to pull out the fully-qualified domain name (fqdn) from the netloc 
			#	with some regex, handles cases where the port is included (eg 'example.com:1234')
			#	drops leading/trailing '.', etc.
			fqdn = re.search('^(\.+)?(.+?)(:.+)?(\.+)?$', urlsplit(url).netloc).group(2)

			# convert to idna/ascii/utf-8 for enhanced compatability
			fqdn = fqdn.encode('idna').decode('utf-8')
		except:
			return None

		if get_ip_adrr:
			# to see if the fqdn is simply an ip_addr try to load it as such
			# return the IP for all fields even though not strictly 
			# accurate as to field values
			try:
				ip_addr = socket.inet_aton(fqdn)
				return(fqdn, fqdn, fqdn, None, None)
			except socket.error:
				pass

			# if the fqdn is not an ip_addr we use socket to get the ip_addr
			# this will fail if the host doesn't respond to ping
			# which often happens with cookie domains
			try:
				ip_addr = socket.gethostbyname(fqdn)
			except:
				ip_addr = None
		else:
			ip_addr = None

		# convert what we have to a tuple and match against our list
		domain_tuple = tuple(fqdn.split('.'))
		num_tokens = len(domain_tuple)
		slice_point = 0

		# we keep dropping off the left-most token until we find a match
		# this way we match on "ac.uk" *before* "uk"
		while slice_point < num_tokens-1:
			slice_point += 1
			pubsuffix = domain_tuple[slice_point:]
			if pubsuffix in self.pubsuffix_list:
				# we found the pubsuffix, 1 back is the domain
				domain = domain_tuple[slice_point-1:]
				# tld is always the final token
				tld = domain_tuple[num_tokens-1]
				# found match, return as single strings joined on '.'
				return (ip_addr, fqdn, '.'.join(domain), '.'.join(pubsuffix), tld)

		# if we get to this point nothing else has worked
		return None
	# get_domain_pubsuffix_tld
#end ParseURL
