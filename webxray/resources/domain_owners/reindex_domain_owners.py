import json

def list_to_json_string(list):
	json_string = ''
	if len(list) > 0:
		for item in sorted(list):
			json_string += '\n\t\t\t\t"'+item+'",'
		return json_string[:-1]
	else:
		return json_string
# list_to_json_string

def url_list_to_json_string(list):
	json_string = ''
	if len(list) > 0:
		for lang,url in sorted(list):
			json_string += '\n\t\t\t\t["%s","%s"],' % (lang,url)
		return json_string[:-1]
	else:
		return json_string
# url_list_to_json_string

def null_json_string(string):
	if string:
		return '"%s"' % string
	else:
		return 'null'
# null_json_string

if __name__ == '__main__':
	infile	= open('domain_owners.json', 'r')
	data 	= json.load(infile)
	infile.close()
	
	# alpha sort list on id string
	data_sorted = sorted(data, key=lambda data:data['id'])

	# stuff everything into one giant string
	out_string = '['

	# make sure the revision date is first
	for item in data_sorted:
		out_string += ("""\n\t{
			"id"							: "%s",
			"parent_id"						: %s,
			"name"							: %s,
			"aliases"						: [%s
			],
			"homepage_url"					: %s,
			"homepage_meta_desc"			: %s,
			"site_privacy_policy_urls"		: [%s
			],
			"service_privacy_policy_urls"	: [%s
			],
			"gdpr_statement_urls"			: [%s
			],
			"terms_of_use_urls"				: [%s
			],
			"cookie_policy_urls"			: [%s
			],
			"adchoices_urls"				: [%s
			],
			"ccpa_urls"						: [%s
			],
			"health_segment_urls"			: [%s
			],
			"opt_out_urls"					: [%s
			],
			"platforms"						: [%s
			],
			"uses"							: [%s
			],
			"notes"							: %s,
			"country"						: %s,
			"crunchbase_id"					: %s,
			"trade_groups"					: [%s
			],
			"domains"						: [%s
			]
	},""" % (
				item['id'],
				null_json_string(item['parent_id']),
				null_json_string(item['name']),
				list_to_json_string(item['aliases']),
				null_json_string(item['homepage_url']),
				null_json_string(item['homepage_meta_desc']),
				url_list_to_json_string(item['site_privacy_policy_urls']),
				url_list_to_json_string(item['service_privacy_policy_urls']),
				url_list_to_json_string(item['gdpr_statement_urls']),
				url_list_to_json_string(item['terms_of_use_urls']),
				url_list_to_json_string(item['cookie_policy_urls']),
				url_list_to_json_string(item['adchoices_urls']),
				url_list_to_json_string(item['ccpa_urls']),
				url_list_to_json_string(item['health_segment_urls']),
				url_list_to_json_string(item['opt_out_urls']),
				list_to_json_string(item['platforms']),
				list_to_json_string(item['uses']),
				null_json_string(item['notes']), 
				null_json_string(item['country']),
				null_json_string(item['crunchbase_id']),
				list_to_json_string(item['trade_groups']),
				list_to_json_string(item['domains'])
		))
	# end loop

	# all done.
	out_string = out_string[:-1]+'\n]'
	outfile	= open('domain_owners.json', 'w')
	outfile.write(out_string)
	outfile.close()
# end main
