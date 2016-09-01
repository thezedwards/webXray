#	this class extracts the sub domain, full domain, and tld from a uri string
#	for.example.com gets parsed to "for.example.com", "example.com", and "com"
#
#	the mozilla public suffix list is used for identifying ccTLDs, this list is incomplete
#		however, so I have patched it with additional ccTLD info, look into the dir
#		/resources/pubsuffix to find relevant files

import os
import re
import socket
from urllib.parse import urlsplit

class ParseURI:
	def __init__(self):
		# load up the tld list now as only hit it once this way
		self.pubsuffix_list = self.get_pubsuffix_list()
	# end __init__

	def get_pubsuffix_list(self):
		# builds a shared list of tuples based on the pubsuffix list; tuples allow for
		# quick comparisons of smaller strings

		# get the file from the local dir
		pubsuffix_raw_list = open(os.path.join(os.path.dirname(__file__), './resources/pubsuffix/wbxrPubSuffixList.txt'), 'r')
		pubsuffix_list = []

		for line in pubsuffix_raw_list:
				# the last part of the list is random stuff we don't care about, so stop reading
				if re.match("^// ===BEGIN PRIVATE DOMAINS===", line):break
				# skip lines that are comments or blank, add others to list
				# also remove leading ., !, and * as it screws up regex later
				if not re.match("^//.+$|^$", line):
					pubsuffix_string = re.sub('^[\!\*]\.?', '', line.strip())
					
					# to maintain consistency with phantomjs we need to convert to idna/ascii/utf-8
					pubsuffix_string = pubsuffix_string.encode('idna').decode('utf-8')

					# we convert to a tuple so we can do fast comparisons
					pubsuffix_list.append(tuple(pubsuffix_string.split('.')))
		return pubsuffix_list
	# get_pubsuffix_list

	def get_domain_pubsuffix_tld(self,uri):
		# first make sure it is actually an https? request we can parse
		if not (re.match('^https?://.+', uri)):
			return('Exception: Unable to parse: '+uri, 'Exception: Unable to parse: '+uri, 'Exception: Unable to parse: '+uri)

		try:
			# try to pull out the domain with some regex, handles cases where the port
			#	is included (eg 'example.com:1234'), drop leading/trailing '.', etc.
			domain = re.search('^(\.+)?(.+?)(:.+)?(\.+)?$', urlsplit(uri)[1]).group(2)

			# to maintain consistency with phantomjs we need to convert to idna/ascii/utf-8
			domain = domain.encode('idna').decode('utf-8')
		except:
			return('Exception: Unable to parse: '+uri, 'Exception: Unable to parse: '+uri, 'Exception: Unable to parse: '+uri)
		
		# if the domain works as an ip_adr we return that
		try:
			ip = socket.inet_aton(domain)
			return(domain,None,None)
		except socket.error:
			pass

		# convert what we have to a tuple and match against our list
		domain_tuple = tuple(domain.split('.'))
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
				return ('.'.join(domain), '.'.join(pubsuffix), tld)

		# if we get to this point nothing else has worked
		return('Exception: Unable to parse: '+uri, 'Exception: Unable to parse: '+uri, 'Exception: Unable to parse: '+uri)
	# get_domain_pubsuffix_tld
#end ParseURI