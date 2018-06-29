import json

if __name__ == '__main__':
	"""
	reindexes the domain_owners file
	"""
	infile	= open('domain_owners.json', 'r')
	data 	= json.load(infile)
	infile.close()
	outfile	= open('domain_owners.json', 'w')

	data_sorted = sorted(data, key=lambda data:data['owner_name'].lower())
	data_reindexed = []
	old_id_to_new_id = {}

	new_id = 0

	for item in data_sorted:
		old_id_to_new_id[item['id']] = new_id
		
		if item['parent_id']:
			old_parent_id = item['parent_id']
		else:
			old_parent_id = None

		data_reindexed.append({
			"id"					: new_id,
			"old_parent_id"			: old_parent_id,
			"owner_name"			: item['owner_name'],
			"aliases"				: item['aliases'],
			"homepage_url"			: item['homepage_url'],
			"privacy_policy_url"	: item['privacy_policy_url'],
			"notes"					: item['notes'],
			"country"				: item['country'],
			"uses"					: item['uses'],
			"platforms"				: item['platforms'],
			"domains"				: item['domains']
		})

		new_id +=1

	out_string = '['
	for item in data_reindexed:
		if item['old_parent_id'] != None:
			parent_id = old_id_to_new_id[item['old_parent_id']]
		else:
			parent_id = "null"

		if len(item['aliases']) != 0:
			aliases_string = ''
			for alias in sorted(item['aliases']):
				aliases_string += '"'+alias+'",'
			aliases_string = aliases_string[:-1]
		else:
			aliases_string = ''

		if len(item['platforms']) != 0:
			platforms_string = ''
			for platform in sorted(item['platforms']):
				platforms_string += '"'+platform+'",'
			platforms_string = platforms_string[:-1]
		else:
			platforms_string = ''

		if len(item['uses']) != 0:
			uses_string = ''
			for use in sorted(item['uses']):
				uses_string += '"'+use+'",'
			uses_string = uses_string[:-1]
		else:
			uses_string = ''

		if len(item['domains']) != 0:
			domains_string = ''
			for domain in sorted(item['domains']):
				domains_string += '\n\t\t\t"'+domain+'",'
			domains_string = domains_string[:-1]
		else:
			domains_string = ''

		if item['homepage_url'] is None:
			homepage_url = 'null'
		else:
			homepage_url = '"'+item['homepage_url']+'"'

		if item['privacy_policy_url'] is None:
			privacy_policy_url = 'null'
		else:
			privacy_policy_url = '"'+item['privacy_policy_url']+'"'

		if item['notes'] is None:
			notes = 'null'
		else:
			notes = '"'+item['notes']+'"'

		if item['country'] is None:
			country = 'null'
		else:
			country = '"'+item['country']+'"'

		out_string += ("""\n\t{
		"id"				 : %s,
		"parent_id"			 : %s,
		"owner_name"		 : "%s",
		"aliases"		 	 : [%s],
		"homepage_url"		 : %s,
		"privacy_policy_url" : %s,
		"notes"				 : %s,
		"country"			 : %s,
		"uses"				 : [%s],
		"platforms"			 : [%s],
		"domains"			 : [%s
		]
	},""" % (
			item['id'],
			parent_id,item['owner_name'],
			aliases_string,
			homepage_url,
			privacy_policy_url,
			notes,
			country,
			uses_string,
			platforms_string,
			domains_string
		))
	# end loop
	out_string = out_string[:-1]+'\n]'
	outfile.write(out_string)
	outfile.close()
# end main
