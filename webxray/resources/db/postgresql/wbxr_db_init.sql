-- this file is read line-by-line by python to init the database
-- for the sake of readability, db schemas are in laid out in comments
-- but for python sake they are read as very long single lines
----------------------------------
--- NEEDED FOR TRIGRAM INDEXES ---
----------------------------------
CREATE EXTENSION pg_trgm;
--------------
--- CONFIG ---
--------------
-- CREATE TABLE config(
-- 	client_browser_type TEXT,
-- 	client_prewait BIGINT,
-- 	client_no_event_wait BIGINT,
-- 	client_max_wait BIGINT,
-- 	client_get_bodies BOOLEAN,
-- 	client_get_bodies_b64 BOOLEAN,
-- 	client_get_screen_shot BOOLEAN,
-- 	client_get_text BOOLEAN,
-- 	client_crawl_depth BIGINT,
-- 	client_crawl_retries BIGINT,
-- 	client_page_load_strategy TEXT,
-- 	client_reject_redirects BOOLEAN,
-- 	client_min_internal_links BIGINT,
-- 	max_attempts BIGINT,
-- 	modified TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	store_1p BOOLEAN,
-- 	store_base64 BOOLEAN,
-- 	store_files BOOLEAN,
-- 	store_screen_shot BOOLEAN,
-- 	store_source BOOLEAN,
-- 	store_page_text BOOLEAN,
-- 	store_links BOOLEAN,
-- 	store_dom_storage BOOLEAN,
-- 	store_responses BOOLEAN,
-- 	store_request_xtra_headers BOOLEAN,
-- 	store_response_xtra_headers BOOLEAN,
-- 	store_requests BOOLEAN,
-- 	store_websockets BOOLEAN,
-- 	store_websocket_events BOOLEAN,
-- 	store_event_source_msgs BOOLEAN,
-- 	store_cookies BOOLEAN,
-- 	store_security_details BOOLEAN,
-- 	timeseries_enabled BOOLEAN,
-- 	timeseries_interval BIGINT
-- );
CREATE TABLE config(client_browser_type TEXT,client_prewait BIGINT,client_no_event_wait BIGINT,client_max_wait BIGINT,client_get_bodies BOOLEAN,client_get_bodies_b64 BOOLEAN,client_get_screen_shot BOOLEAN,client_get_text BOOLEAN,client_crawl_depth BIGINT,client_crawl_retries BIGINT,client_page_load_strategy TEXT,client_reject_redirects BOOLEAN,client_min_internal_links BIGINT,max_attempts BIGINT,modified TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,store_1p BOOLEAN,store_base64 BOOLEAN,store_files BOOLEAN,store_screen_shot BOOLEAN,store_source BOOLEAN,store_page_text BOOLEAN,store_links BOOLEAN,store_dom_storage BOOLEAN,store_responses BOOLEAN,store_request_xtra_headers BOOLEAN,store_response_xtra_headers BOOLEAN,store_requests BOOLEAN,store_websockets BOOLEAN,store_websocket_events BOOLEAN,store_event_source_msgs BOOLEAN,store_cookies BOOLEAN,store_security_details BOOLEAN,timeseries_enabled BOOLEAN,timeseries_interval BIGINT);
------------------
--- TASK_QUEUE ---
------------------
-- CREATE TABLE task_queue(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	target TEXT,
-- 	target_md5 TEXT,
-- 	task TEXT,
-- 	client_id TEXT,
-- 	attempts BIGINT DEFAULT 0,
-- 	locked BOOLEAN DEFAULT FALSE,
-- 	failed BOOLEAN DEFAULT FALSE,
-- 	added TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	modified TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	UNIQUE (target_md5, task)
-- );
CREATE TABLE task_queue(id BIGSERIAL PRIMARY KEY,target TEXT,target_md5 TEXT,task TEXT,client_id TEXT,attempts BIGINT DEFAULT 0,locked BOOLEAN DEFAULT FALSE,failed BOOLEAN DEFAULT FALSE,added TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,modified TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,UNIQUE (target_md5, task));
---------------------
--- DOMAIN OWNER  ---
---------------------
-- CREATE TABLE domain_owner(
-- 	id TEXT PRIMARY KEY UNIQUE,
-- 	parent_id TEXT,
-- 	name TEXT,
-- 	aliases TEXT,
-- 	homepage_url TEXT,
-- 	site_privacy_policy_urls TEXT,
-- 	service_privacy_policy_urls TEXT,
-- 	gdpr_statement_urls TEXT,
-- 	terms_of_use_urls TEXT,
-- 	platforms TEXT,
-- 	uses TEXT,
-- 	notes TEXT,
-- 	country TEXT
-- );
CREATE TABLE domain_owner(id TEXT PRIMARY KEY UNIQUE,parent_id TEXT,name TEXT,aliases TEXT,homepage_url TEXT,site_privacy_policy_urls TEXT,service_privacy_policy_urls TEXT,gdpr_statement_urls TEXT,terms_of_use_urls TEXT,platforms TEXT,uses TEXT,notes TEXT,country TEXT);
--------------
--- DOMAIN ---
--------------
-- CREATE TABLE domain(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	fqdn_md5 TEXT UNIQUE,
-- 	fqdn TEXT,
-- 	domain_md5 TEXT,
-- 	domain TEXT,
-- 	pubsuffix_md5 TEXT,
-- 	pubsuffix TEXT,
-- 	tld_md5 TEXT,
-- 	tld TEXT,
-- 	is_tracker_domain BOOLEAN DEFAULT FALSE,
-- 	domain_owner_id TEXT REFERENCES domain_owner(id)
-- );
CREATE TABLE domain(id BIGSERIAL PRIMARY KEY,fqdn_md5 TEXT UNIQUE,fqdn TEXT,domain_md5 TEXT,domain TEXT,pubsuffix_md5 TEXT,pubsuffix TEXT,tld_md5 TEXT,tld TEXT,is_tracker_domain BOOLEAN DEFAULT FALSE,domain_owner_id TEXT REFERENCES domain_owner(id));
-- CREATE INDEX index_domain_owner_id 		ON domain (domain_owner_id);
-- CREATE INDEX index_domain_fqdn_md5		ON domain (fqdn_md5);
-- CREATE INDEX index_domain_domain_md5	ON domain (domain_md5);
-- CREATE INDEX index_domain_domain 	ON domain USING GIN(domain gin_trgm_ops);
-- CREATE INDEX index_domain_fqdn 		ON domain USING GIN(domain gin_trgm_ops);
----------------------
--- DOMAIN_IP_ADDR ---
----------------------
-- CREATE TABLE domain_ip_addr(
-- 	ip_addr TEXT,
-- 	ip_owner TEXT,
-- 	domain_id BIGSERIAL,
-- 	UNIQUE (ip_addr, domain_id)
-- );
CREATE TABLE domain_ip_addr(ip_addr TEXT,ip_owner TEXT,domain_id BIGSERIAL,UNIQUE (ip_addr, domain_id));
-----------------
--- PAGE_TEXT ---
-----------------
-- CREATE TABLE page_text(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	readability_source_md5 TEXT,
-- 	text TEXT,
-- 	text_md5 TEXT NOT NULL,
-- 	tokens TSVECTOR,
-- 	word_count BIGINT,
-- 	UNIQUE (readability_source_md5, text_md5)
-- );
CREATE TABLE page_text(id BIGSERIAL PRIMARY KEY,readability_source_md5 TEXT,text TEXT,text_md5 TEXT NOT NULL,tokens TSVECTOR,word_count BIGINT,UNIQUE (readability_source_md5, text_md5));
-- CREATE INDEX index_page_text_readability_md5 	ON page_text (readability_source_md5);
-- CREATE INDEX index_page_text_text_md5 			ON page_text (text_md5);
CREATE INDEX index_page_text 					ON page_text USING GIN(text gin_trgm_ops);
------------
--- PAGE ---
------------
-- CREATE TABLE page(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	crawl_id TEXT,
-- 	crawl_timestamp TIMESTAMPTZ,
-- 	crawl_sequence BIGINT,
-- 	client_id TEXT,
-- 	client_timezone TEXT,
-- 	client_ip TEXT,
-- 	browser_type TEXT,
-- 	browser_version TEXT,
-- 	browser_prewait BIGINT,
-- 	browser_no_event_wait BIGINT,
-- 	browser_max_wait BIGINT,
-- 	page_load_strategy TEXT,
-- 	title TEXT,
-- 	meta_desc TEXT,
-- 	lang TEXT,
-- 	start_url_md5 TEXT,
-- 	start_url TEXT,
-- 	start_url_domain_id BIGINT REFERENCES domain(id),
-- 	final_url_md5 TEXT,
-- 	final_url TEXT,
-- 	final_url_domain_id BIGINT REFERENCES domain(id),
-- 	page_domain_redirect BOOLEAN,
-- 	is_ssl BOOLEAN,
-- 	link_count_internal BIGINT,
-- 	link_count_external BIGINT,
-- 	load_time NUMERIC,
-- 	page_text_id BIGINT,
-- 	page_source_md5 TEXT,
-- 	screen_shot_md5 TEXT,
-- 	accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	stored TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	UNIQUE (accessed, start_url_md5)
-- );
CREATE TABLE page(id BIGSERIAL PRIMARY KEY,crawl_id TEXT,crawl_timestamp TIMESTAMPTZ,crawl_sequence BIGINT,client_id TEXT,client_timezone TEXT,client_ip TEXT,browser_type TEXT,browser_version TEXT,browser_prewait BIGINT,browser_no_event_wait BIGINT,browser_max_wait BIGINT,page_load_strategy TEXT,title TEXT,meta_desc TEXT,lang TEXT,start_url_md5 TEXT,start_url TEXT,start_url_domain_id BIGINT REFERENCES domain(id),final_url_md5 TEXT,final_url TEXT,final_url_domain_id BIGINT REFERENCES domain(id),page_domain_redirect BOOLEAN,is_ssl BOOLEAN,link_count_internal BIGINT,link_count_external BIGINT,load_time NUMERIC,page_text_id BIGINT,page_source_md5 TEXT,screen_shot_md5 TEXT,accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,stored TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,UNIQUE (accessed, start_url_md5));
CREATE INDEX index_page_crawl_id 				ON page(crawl_id);
-- CREATE INDEX index_page_client_id 				ON page(client_id);
-- CREATE INDEX index_page_client_ip 				ON page(client_ip);
CREATE INDEX index_page_title 					ON page USING GIN(title gin_trgm_ops);
CREATE INDEX index_page_meta_desc 				ON page USING GIN(meta_desc gin_trgm_ops);
-- CREATE INDEX index_page_start_url_md5 			ON page(start_url_md5);
-- CREATE INDEX index_page_start_url_domain_id 	ON page(start_url_domain_id);
-- CREATE INDEX index_page_final_url_md5 			ON page(final_url_md5);
-- CREATE INDEX index_page_final_url_domain_id 	ON page(final_url_domain_id);
-- CREATE INDEX index_page_page_text_id 			ON page(page_text_id);
-- CREATE INDEX index_page_page_source_md5 		ON page(page_source_md5);
-- CREATE INDEX index_page_screen_shot_md5 		ON page(screen_shot_md5);
---------------
--- CLUSTER ---
---------------
-- CREATE TABLE cluster(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	type TEXT,
-- 	name TEXT,
-- 	data TEXT
-- );
CREATE TABLE cluster(id BIGSERIAL PRIMARY KEY,type TEXT,name TEXT,data TEXT);
--------------------------
--- PAGE_CLUSTER_JUNCTION ---
--------------------------
-- CREATE TABLE page_cluster_junction(
-- 	page_id BIGINT,
-- 	cluster_id BIGINT,
-- 	UNIQUE (page_id, link_id)
-- );
CREATE TABLE page_cluster_junction(page_id BIGINT,cluster_id BIGINT,UNIQUE (page_id, cluster_id));
CREATE INDEX index_page_cluster_page_id 	ON page_cluster_junction(page_id);
CREATE INDEX index_page_cluster_cluster_id 	ON page_cluster_junction(cluster_id);
------------------------
--- SECURITY_DETAILS ---
------------------------
-- CREATE TABLE security_details(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	lookup_md5 TEXT,
-- 	cert_transparency_compliance TEXT,
-- 	cipher TEXT,
-- 	issuer TEXT,
-- 	key_exchange TEXT,
-- 	protocol TEXT,
-- 	san_list TEXT,
-- 	signed_cert_timestamp_list TEXT,
-- 	subject_name TEXT,
-- 	valid_from BIGINT,
-- 	valid_to BIGINT,
-- 	UNIQUE(lookup_md5)
-- );
CREATE TABLE security_details(id BIGSERIAL PRIMARY KEY,lookup_md5 TEXT,cert_transparency_compliance TEXT,cipher TEXT,issuer TEXT,key_exchange TEXT,protocol TEXT,san_list TEXT,signed_cert_timestamp_list TEXT,subject_name TEXT,valid_from BIGINT,valid_to BIGINT,UNIQUE(lookup_md5));
-- CREATE INDEX index_security_details_lookup_md5 ON security_details(lookup_md5);
----------------
--- RESPONSE ---
----------------
-- CREATE TABLE response(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	domain_id BIGINT REFERENCES domain(id),
-- 	security_details_id BIGINT REFERENCES security_details(id),
-- 	base_url TEXT,
-- 	base_url_md5 TEXT,
-- 	extension TEXT,
-- 	internal_request_id TEXT,
-- 	connection_reused BOOLEAN,
-- 	cookies_sent TEXT,
-- 	cookies_set TEXT,
-- 	file_md5 TEXT,
-- 	final_data_length BIGINT,
-- 	from_disk_cache BOOLEAN,
-- 	from_prefetch_cache BOOLEAN,
-- 	from_service_worker BOOLEAN,
-- 	is_3p BOOLEAN,
-- 	is_ssl BOOLEAN,
-- 	is_data BOOLEAN,
-- 	mime_type TEXT,
-- 	page_domain_in_headers BOOLEAN,
-- 	protocol TEXT,
-- 	referer TEXT,
-- 	remote_ip_address TEXT,
-- 	remote_port TEXT,
-- 	request_headers TEXT,
-- 	response_headers TEXT,
-- 	security_state TEXT,
-- 	status TEXT,
-- 	status_text TEXT,
-- 	timestamp TIMESTAMPTZ,
-- 	timing TEXT,
-- 	type TEXT,
-- 	url TEXT
-- );
CREATE TABLE response(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,domain_id BIGINT REFERENCES domain(id),security_details_id BIGINT REFERENCES security_details(id),base_url TEXT,base_url_md5 TEXT,extension TEXT,internal_request_id TEXT,connection_reused BOOLEAN,cookies_sent TEXT,cookies_set TEXT,file_md5 TEXT,final_data_length BIGINT,from_disk_cache BOOLEAN,from_prefetch_cache BOOLEAN,from_service_worker BOOLEAN,is_3p BOOLEAN,is_ssl BOOLEAN,is_data BOOLEAN,mime_type TEXT,page_domain_in_headers BOOLEAN,protocol TEXT,referer TEXT,remote_ip_address TEXT,remote_port TEXT,request_headers TEXT,response_headers TEXT,security_state TEXT,status TEXT,status_text TEXT,timestamp TIMESTAMPTZ,timing TEXT,type TEXT,url TEXT);
CREATE INDEX index_response_page_id 			ON response(page_id);
CREATE INDEX index_response_domain_id 			ON response(domain_id);
-- CREATE INDEX index_response_security_details_id ON response(security_details_id);
-- CREATE INDEX index_response_base_url 			ON response USING GIN(base_url gin_trgm_ops);
CREATE INDEX index_response_internal_request_id ON response(internal_request_id);
CREATE INDEX index_response_file_md5 			ON response(file_md5);
-- CREATE INDEX index_response_remote_ip_address 	ON response(remote_ip_address);
-- CREATE INDEX index_response_status 				ON response(status);
-- CREATE INDEX index_response_type 				ON response(type);
-- CREATE INDEX index_response_url 				ON response USING GIN(url gin_trgm_ops);
------------------------------
--- RESPONSE_EXTRA_HEADERS ---
------------------------------
-- CREATE TABLE response_extra_headers(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	internal_request_id TEXT,
-- 	cookies_set TEXT,
-- 	headers TEXT,
-- 	blocked_cookies TEXT
-- );
CREATE TABLE response_extra_headers(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,internal_request_id TEXT,cookies_set TEXT,headers TEXT,blocked_cookies TEXT);
CREATE INDEX index_response_extra_headers_page_id 				ON response_extra_headers (page_id);
CREATE INDEX index_response_extra_headers_internal_request_id 	ON response_extra_headers (internal_request_id);
---------------
--- REQUEST ---
---------------
-- CREATE TABLE request(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	domain_id BIGINT REFERENCES domain(id),
-- 	base_url TEXT,
-- 	base_url_md5 TEXT,
-- 	internal_request_id TEXT,
-- 	document_url TEXT,
-- 	extension TEXT,
-- 	file_md5 TEXT,
-- 	full_url TEXT,
-- 	full_url_md5 TEXT,
-- 	has_user_gesture TEXT,
-- 	headers TEXT,
-- 	initial_priority TEXT,
-- 	initiator TEXT,
-- 	is_3p BOOLEAN,
-- 	is_data BOOLEAN,
-- 	is_link_preload BOOLEAN,
-- 	is_ssl BOOLEAN,
-- 	load_finished BOOLEAN,
-- 	loader_id TEXT,
-- 	method TEXT,
-- 	page_domain_in_headers BOOLEAN,
-- 	post_data TEXT,
-- 	get_data TEXT,
-- 	redirect_response_url TEXT,
-- 	referer TEXT,
-- 	referrer_policy TEXT,
-- 	response_received BOOLEAN,
-- 	timestamp TIMESTAMPTZ,
-- 	type TEXT
-- );
CREATE TABLE request(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,domain_id BIGINT REFERENCES domain(id),base_url TEXT,base_url_md5 TEXT,internal_request_id TEXT,document_url TEXT,extension TEXT,file_md5 TEXT,full_url TEXT,full_url_md5 TEXT,has_user_gesture TEXT,headers TEXT,initial_priority TEXT,initiator TEXT,is_3p BOOLEAN,is_data BOOLEAN,is_link_preload BOOLEAN,is_ssl BOOLEAN,load_finished BOOLEAN,loader_id TEXT,method TEXT,page_domain_in_headers BOOLEAN,post_data TEXT,get_data TEXT,redirect_response_url TEXT,referer TEXT,referrer_policy TEXT,response_received BOOLEAN,timestamp TIMESTAMPTZ,type TEXT);
CREATE INDEX index_request_page_id 	ON request (page_id);
CREATE INDEX index_request_internal_request_id ON request(internal_request_id);
-- CREATE INDEX index_request_base_url ON request USING GIN(base_url gin_trgm_ops);
-- CREATE INDEX index_request_file_md5 ON request (file_md5);
-- CREATE INDEX index_request_full_url ON request USING GIN(full_url gin_trgm_ops);
-----------------------------
--- REQUEST_EXTRA_HEADERS ---
-----------------------------
-- CREATE TABLE request_extra_headers(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	internal_request_id TEXT,
-- 	cookies_sent TEXT,
-- 	headers TEXT,
-- 	associated_cookies TEXT
-- );
CREATE TABLE request_extra_headers(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,internal_request_id TEXT,cookies_sent TEXT,headers TEXT,associated_cookies TEXT);
CREATE INDEX index_request_extra_headers_page_id 				ON request_extra_headers (page_id);
CREATE INDEX index_request_extra_headers_internal_request_id 	ON request_extra_headers (internal_request_id);
------------------
--- WEBSOCKETS ---
------------------
-- CREATE TABLE websocket(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	domain_id BIGINT REFERENCES domain(id),
-- 	initiator TEXT,
-- 	is_3p BOOLEAN,
-- 	url TEXT
-- );
CREATE TABLE websocket(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,domain_id BIGINT REFERENCES domain(id),initiator TEXT,is_3p BOOLEAN,url TEXT);
CREATE INDEX index_websocket_page_id 	ON websocket(page_id);
-- CREATE INDEX index_websocket_domain_id 	ON websocket(domain_id);
-- CREATE INDEX index_websocket_url 		ON websocket USING GIN(url gin_trgm_ops);
------------------------
--- WEBSOCKET EVENTS ---
------------------------
-- CREATE TABLE websocket_event(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	websocket_id BIGINT REFERENCES websocket(id),
-- 	timestamp TIMESTAMPTZ,
-- 	event_type TEXT,
-- 	payload TEXT
-- );
CREATE TABLE websocket_event(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,websocket_id BIGINT REFERENCES websocket(id),timestamp TIMESTAMPTZ,event_type TEXT,payload TEXT);
CREATE INDEX index_websocket_event_page_id 		ON websocket_event(page_id);
CREATE INDEX index_websocket_event_websocket_id ON websocket_event(websocket_id);
------------------------
--- EVENT_SOURCE_MSG ---
------------------------
-- CREATE TABLE event_source_msg(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	internal_request_id TEXT,
-- 	event_name TEXT,
-- 	event_id TEXT,
-- 	data TEXT,
-- 	timestamp TIMESTAMPTZ
-- );
CREATE TABLE event_source_msg(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,internal_request_id TEXT,event_name TEXT,event_id TEXT,data TEXT,timestamp TIMESTAMPTZ);
CREATE INDEX index_event_source_msg_page_id 				ON event_source_msg(page_id);
CREATE INDEX index_event_source_msg_internal_request_id 	ON event_source_msg(internal_request_id);
--------------
--- COOKIE ---
--------------
-- CREATE TABLE cookie(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	domain_id BIGINT REFERENCES domain(id),
-- 	domain TEXT,
-- 	expires_text TEXT,
-- 	expires_timestamp TIMESTAMPTZ,
-- 	http_only BOOLEAN,
-- 	is_3p BOOLEAN,
-- 	is_1p_3p BOOLEAN,
-- 	name TEXT,
-- 	path TEXT,
-- 	same_site TEXT,
-- 	secure BOOLEAN,
-- 	session BOOLEAN,
-- 	size BIGINT,
-- 	value TEXT,
-- 	is_set_by_response BOOLEAN
-- );
CREATE TABLE cookie(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,domain_id BIGINT REFERENCES domain(id),domain TEXT,expires_text TEXT,expires_timestamp TIMESTAMPTZ,http_only BOOLEAN,is_3p BOOLEAN,is_1p_3p BOOLEAN,name TEXT,path TEXT,same_site TEXT,secure BOOLEAN,session BOOLEAN,size BIGINT,value TEXT,is_set_by_response BOOLEAN);
CREATE INDEX index_cookie_page_id 	ON cookie(page_id);
CREATE INDEX index_cookie_domain_id ON cookie(domain_id);
-- CREATE INDEX index_cookie_name 		ON cookie USING GIN(name gin_trgm_ops);
-- CREATE INDEX index_cookie_value 	ON cookie USING GIN(value gin_trgm_ops);
-------------------
--- DOM_STORAGE ---
-------------------
-- CREATE TABLE dom_storage(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	domain_id BIGINT REFERENCES domain(id),
-- 	security_origin TEXT,
-- 	is_local_storage BOOLEAN,
-- 	key TEXT,
-- 	value TEXT,
-- 	is_3p BOOLEAN
-- );
CREATE TABLE dom_storage(id BIGSERIAL PRIMARY KEY,page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,domain_id BIGINT REFERENCES domain(id),security_origin TEXT,is_local_storage BOOLEAN,key TEXT,value TEXT,is_3p BOOLEAN);
CREATE INDEX index_dom_storage_page_id 			ON dom_storage(page_id);
CREATE INDEX index_dom_storage_domain_id 		ON dom_storage(domain_id);
-- CREATE INDEX index_dom_storage_security_origin 	ON dom_storage(security_origin);
-------------
--- ERROR ---
-------------
-- CREATE TABLE error(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	client_id TEXT NOT NULL,
-- 	target TEXT NOT NULL,
-- 	task TEXT NOT NULL,
-- 	msg TEXT NOT NULL,
-- 	timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- );
CREATE TABLE error(id BIGSERIAL PRIMARY KEY,client_id TEXT NOT NULL,target TEXT NOT NULL,task TEXT NOT NULL,msg TEXT NOT NULL,timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);
------------
--- LINK ---
------------
-- CREATE TABLE link(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	url TEXT,
-- 	url_md5 TEXT,
-- 	text TEXT,
-- 	text_md5 TEXT,
-- 	is_policy BOOLEAN,
-- 	is_internal BOOLEAN,
-- 	domain_id BIGINT REFERENCES domain(id),
-- 	UNIQUE (url_md5, text_md5)
-- );
CREATE TABLE link(id BIGSERIAL PRIMARY KEY,url TEXT,url_md5 TEXT,text TEXT,text_md5 TEXT,is_policy BOOLEAN,is_internal BOOLEAN,domain_id BIGINT REFERENCES domain(id),UNIQUE (url_md5, text_md5));
-- CREATE INDEX index_link_url_md5 	ON link(url_md5);
-- CREATE INDEX index_link_text_md5 	ON link(text_md5);
CREATE INDEX index_link_domain_id 	ON link(domain_id);
--------------------------
--- PAGE_LINK_JUNCTION ---
--------------------------
-- CREATE TABLE page_link_junction(
-- 	page_id BIGINT,
-- 	link_id BIGINT,
-- 	UNIQUE (page_id, link_id)
-- );
CREATE TABLE page_link_junction(page_id BIGINT,link_id BIGINT,UNIQUE (page_id, link_id));
CREATE INDEX index_page_link_junction_page_id ON page_link_junction(page_id);
CREATE INDEX index_page_link_junction_link_id ON page_link_junction(link_id);
--------------
--- POLICY ---
--------------
-- CREATE TABLE policy(
-- 	id BIGSERIAL PRIMARY KEY,
-- 	client_id TEXT,
-- 	client_timezone TEXT,
-- 	client_ip TEXT,
-- 	browser_type TEXT,
-- 	browser_version TEXT,
-- 	browser_prewait BIGINT,
-- 	start_url TEXT,
-- 	start_url_md5 TEXT,
-- 	final_url TEXT,
-- 	final_url_md5 TEXT,
-- 	title TEXT,
-- 	meta_desc TEXT,
-- 	lang TEXT,
-- 	fk_score NUMERIC,
-- 	fre_score NUMERIC,
-- 	type TEXT,
-- 	match_term TEXT,
-- 	match_text TEXT,
-- 	match_text_type TEXT,
-- 	confidence BIGINT DEFAULT 0,
-- 	page_text_id BIGINT,
-- 	page_source_md5 TEXT,
-- 	accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	added TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	UNIQUE (start_url_md5, page_text_id)
-- );
CREATE TABLE policy(id BIGSERIAL PRIMARY KEY,client_id TEXT,client_timezone TEXT,client_ip TEXT,browser_type TEXT,browser_version TEXT,browser_prewait BIGINT,start_url TEXT,start_url_md5 TEXT,final_url TEXT,final_url_md5 TEXT,title TEXT,meta_desc TEXT,lang TEXT,fk_score NUMERIC,fre_score NUMERIC,type TEXT,match_term TEXT,match_text TEXT,match_text_type TEXT,confidence BIGINT DEFAULT 0,page_text_id BIGINT,page_source_md5 TEXT,accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,added TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,UNIQUE (start_url_md5, page_text_id));
-- CREATE INDEX index_policy_start_url_md5 	ON policy(start_url_md5);
-- CREATE INDEX index_policy_final_url_md5 	ON policy(final_url_md5);
CREATE INDEX index_policy_title 			ON policy USING GIN(title gin_trgm_ops);
CREATE INDEX index_policy_meta_desc 		ON policy USING GIN(meta_desc gin_trgm_ops);
CREATE INDEX index_policy_page_text_id 		ON policy(page_text_id);
-- CREATE INDEX index_policy_page_source_md5 	ON policy(page_source_md5);
----------------------------
--- PAGE_POLICY_JUNCTION ---
----------------------------
-- CREATE TABLE page_policy_junction(
-- 	page_id BIGINT,
-- 	policy_id BIGINT,
-- 	accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	UNIQUE (page_id, policy_id, accessed)
-- );
CREATE TABLE page_policy_junction(page_id BIGINT,policy_id BIGINT,accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,UNIQUE (page_id, policy_id, accessed));
CREATE INDEX index_page_policy_junction_page_id 	ON page_policy_junction (page_id);
CREATE INDEX index_page_policy_junction_policy_id 	ON page_policy_junction (policy_id);
-----------------------------
--- CRAWL_POLICY_JUNCTION ---
-----------------------------
-- CREATE TABLE crawl_policy_junction(
-- 	crawl_id TEXT,
-- 	policy_id BIGINT,
-- 	accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
-- 	UNIQUE (crawl_id, policy_id, accessed)
-- );
CREATE TABLE crawl_policy_junction(crawl_id TEXT,policy_id BIGINT,accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,UNIQUE (crawl_id, policy_id, accessed));
CREATE INDEX index_crawl_policy_junction_crawl_id 	ON crawl_policy_junction (crawl_id);
CREATE INDEX index_crawl_policy_junction_policy_id 	ON crawl_policy_junction (policy_id);
---------------------------------
--- POLICY_REQUEST_DISCLOSURE ---
---------------------------------
-- CREATE TABLE policy_request_disclosure(
-- 	page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,
-- 	policy_id BIGINT REFERENCES policy(id),
-- 	request_owner_id TEXT REFERENCES domain_owner(id),
-- 	disclosed BOOLEAN,
-- 	disclosed_owner_id TEXT REFERENCES domain_owner(id),
-- 	UNIQUE (page_id, request_owner_id)
-- );
CREATE TABLE policy_request_disclosure(page_id BIGINT REFERENCES page(id) ON DELETE CASCADE,policy_id BIGINT REFERENCES policy(id),request_owner_id TEXT REFERENCES domain_owner(id),disclosed BOOLEAN,disclosed_owner_id TEXT REFERENCES domain_owner(id),UNIQUE (page_id, request_owner_id));
CREATE INDEX index_policy_request_disclosure_page_id 			ON policy_request_disclosure(page_id);
CREATE INDEX index_policy_request_disclosure_policy_id 			ON policy_request_disclosure(policy_id);
CREATE INDEX index_policy_request_disclosure_request_owner_id 	ON policy_request_disclosure(request_owner_id);
CREATE INDEX index_policy_request_disclosure_disclosed_owner_id ON policy_request_disclosure(disclosed_owner_id);
------------
--- FILE ---
------------
-- CREATE TABLE file(
-- 	md5 TEXT UNIQUE PRIMARY KEY,
-- 	body TEXT,
-- 	type TEXT,
-- 	is_base64 BOOLEAN,
-- 	accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- );
CREATE TABLE file(md5 TEXT UNIQUE PRIMARY KEY,body TEXT,type TEXT,is_base64 BOOLEAN,accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX index_file_md5 	ON file(md5);
-- CREATE INDEX index_type 		ON file(type);
------------------------------
--- CRAWL_ID_DOMAIN_LOOKUP ---
------------------------------
-- CREATE TABLE IF NOT EXISTS crawl_id_domain_lookup(
-- 	crawl_id TEXT,
-- 	domain TEXT,
-- 	domain_owner_id TEXT,
-- 	is_request BOOLEAN DEFAULT FALSE,
-- 	is_response BOOLEAN DEFAULT FALSE,
-- 	is_cookie BOOLEAN DEFAULT FALSE,
-- 	is_websocket BOOLEAN DEFAULT FALSE,
-- 	is_domstorage BOOLEAN DEFAULT FALSE,
-- 	is_disclosed BOOLEAN DEFAULT FALSE
-- );
CREATE TABLE IF NOT EXISTS crawl_id_domain_lookup(crawl_id TEXT,domain TEXT,domain_owner_id TEXT,is_request BOOLEAN DEFAULT FALSE,is_response BOOLEAN DEFAULT FALSE,is_cookie BOOLEAN DEFAULT FALSE,is_websocket BOOLEAN DEFAULT FALSE,is_domstorage BOOLEAN DEFAULT FALSE,is_disclosed BOOLEAN DEFAULT FALSE);
CREATE INDEX IF NOT EXISTS index_crawl_id_domain_lookup_crawl_id 		ON crawl_id_domain_lookup (crawl_id);
CREATE INDEX IF NOT EXISTS index_crawl_id_domain_lookup_domain 			ON crawl_id_domain_lookup (domain);
CREATE INDEX IF NOT EXISTS index_crawl_id_domain_lookup_domain_owner_id ON crawl_id_domain_lookup (domain_owner_id);
-----------------------------
--- PAGE_ID_DOMAIN_LOOKUP ---
-----------------------------
-- CREATE TABLE IF NOT EXISTS page_id_domain_lookup(
-- 	page_id BIGINT,
-- 	domain TEXT,
-- 	domain_owner_id TEXT,
-- 	is_request BOOLEAN DEFAULT FALSE,
-- 	is_response BOOLEAN DEFAULT FALSE,
-- 	is_cookie BOOLEAN DEFAULT FALSE,
-- 	is_websocket BOOLEAN DEFAULT FALSE,
-- 	is_domstorage BOOLEAN DEFAULT FALSE,
-- 	is_disclosed BOOLEAN DEFAULT FALSE
-- );
CREATE TABLE IF NOT EXISTS page_id_domain_lookup(page_id BIGINT,domain TEXT,domain_owner_id TEXT,is_request BOOLEAN DEFAULT FALSE,is_response BOOLEAN DEFAULT FALSE,is_cookie BOOLEAN DEFAULT FALSE,is_websocket BOOLEAN DEFAULT FALSE,is_domstorage BOOLEAN DEFAULT FALSE,is_disclosed BOOLEAN DEFAULT FALSE);
CREATE INDEX IF NOT EXISTS index_page_id_domain_lookup_page_id 			ON page_id_domain_lookup (page_id);
CREATE INDEX IF NOT EXISTS index_page_id_domain_lookup_domain 			ON page_id_domain_lookup (domain);
CREATE INDEX IF NOT EXISTS index_page_id_domain_lookup_domain_owner_id 	ON page_id_domain_lookup (domain_owner_id);