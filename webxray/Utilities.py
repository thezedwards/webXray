import os
import re
import csv
import json
from urllib.parse import urlparse

class Utilities:
	def __init__(self):
		return None
	# __init__

	def write_csv(self, report_path, file_name, csv_rows):
		"""
		basic utility function to write list of csv rows to a file
		"""
		full_file_path = report_path+'/'+file_name
		with open(full_file_path, 'w', newline='', encoding='utf-8') as csvfile:
			csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			for row in csv_rows:
				csv_writer.writerow(row)
		print('\t\tOutput written to %s' % full_file_path)
	# write_csv

	def get_absolute_url_from_page_link(self,page_url,link_url):
		"""
		Given a page_url and a link_url from that page we determine
			the absolute url of the link from the page_url.
		"""

		# ex nihilo nihil fit
		if link_url == None: return None
		if len(link_url) == 0: return None

		# we use the info from the original url for converting 
		#	relative links to absolute
		parsed_page_url = urlparse(page_url)

		# this is an absolute url already, nothing further to do to
		if re.match('^https?://', link_url):
			return(link_url)
		# link with no scheme, paste it in
		elif re.match('^//', link_url):
			return(parsed_page_url.scheme+':'+link_url)
		# relative link, fix it up
		else:
			if link_url[0] != '/':
				return(parsed_page_url.scheme + '://' + parsed_page_url.netloc + '/' + link_url)
			else:
				return(parsed_page_url.scheme + '://' + parsed_page_url.netloc + link_url)

		# this only happens if something breaks
		return None
	# get_absolute_url_from_link

	def get_privacy_policy_term_list(self):
		"""
		Returns a list of all strings we know to correspond to
			privacy policy links which are retrieved from
			our json database.
		"""
		privacy_policy_term_list = []
		for lang_term_set in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/policyxray/policy_terms.json', 'r', encoding='utf-8')):
			for term in lang_term_set['policy_terms']:
				privacy_policy_term_list.append(term)
		return privacy_policy_term_list
	# get_privacy_policy_term_list

	def get_lang_to_privacy_policy_term_dict(self):
		"""
		Returns a dict of privacy policy terms keyed by language code.
		"""
		lang_to_terms = {}
		for lang_term_set in json.load(open(os.path.dirname(os.path.abspath(__file__))+'/resources/policyxray/policy_terms.json', 'r', encoding='utf-8')):
			lang_to_terms[lang_term_set['lang']] = lang_term_set['policy_terms']
		return lang_to_terms
	# get_lang_to_priv_term_dict

# Utilities	
