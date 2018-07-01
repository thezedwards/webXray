/*
*	originally based on netlog.js example from phantomjs docs
*
*	one major modification is that when a page has a chain of redirects phantomjs doesn't
*	follow all of them to completion so we wait for a varible period of time to
*	allow redirects to complete
*/

//enable, then clear cookies
phantom.cookiesEnabled = true;
phantom.clearCookies()

// set up global vars
var page = require('webpage').create(),
    system = require('system'),
    address,
    requested_urls = {},
    received_urls = {},
    requested_bytes = [],
    final_url;

// try to load the page
if (system.args.length === 1) {
    console.log('Usage: wbxr_logger.js <URL>');
    phantom.exit(1);
} else {
	start_load = Date.now();
	last_load = start_load

	wait_time = system.args[1];
    address = system.args[2];

	var final_url = address;

	// randomize user agent to assist in compatibility checks, etc
	// pulled the top 32 from here: https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
	// updated on 20171227
	
	ua_strings = [
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5',
		'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36 OPR/49.0.2725.47',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
		'Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
		'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
		'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:52.0) Gecko/20100101 Firefox/52.0',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36 OPR/49.0.2725.64',
		'Mozilla/5.0 (Windows NT 6.1; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/62.0.3202.94 Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:56.0) Gecko/20100101 Firefox/56.0',
		'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0;  Trident/5.0)',
		'Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/63.0.3239.84 Chrome/63.0.3239.84 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0;  Trident/5.0)',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (iPad; CPU OS 11_1_2 like Mac OS X) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0 Mobile/15B202 Safari/604.1',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:57.0) Gecko/20100101 Firefox/57.0',
		'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/603.2.4 (KHTML, like Gecko) Version/10.1.1 Safari/603.2.4',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Safari/604.1.38',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:58.0) Gecko/20100101 Firefox/58.0',
		'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.9 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko'
	]

	page.settings.userAgent = ua_strings[Math.floor(Math.random()*ua_strings.length)];

    // suppress errors from output
	page.onError = function (msg, trace) {}

	// keep track of what url we are on so we can find redirects later
	page.onUrlChanged = function(targetUrl) {
	  final_url = targetUrl;
	};

	// get all requests made
    page.onResourceRequested = function (request) {
		requested_urls[request.id] = request;
    };

    page.onResourceReceived = function (received) {
		// as the program executes, each request is given an id, and as the element
		// is received a series of messages are triggered, be we only care about
		// the last one with status 'end' as that gives us the time it completed
    	if(received.stage == 'end'){
			received_urls[received.id] = received;
		}
		
		// getting size per https://github.com/ariya/phantomjs/issues/10156#issuecomment-205769368
		if(received.stage == 'start'){
			if(received.bodySize != undefined){
				requested_bytes[received.id] = received.bodySize;
			} else {
				requested_bytes[received.id] = 0;
			}
		} else {
			if(received.bodySize != undefined){
				requested_bytes[received.id] += received.bodySize;
			}
		}
    };

	// python does a regex match on string 'FAIL' so this is non-arbitrary
	// and removing it will screw things up
    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('FAIL to load the address '+address);

            // if there is no phantom.exit() the program will never return!
            phantom.exit();
        }
    });
}

// this timeout waits for specified number of seconds, when done evaluates page 
//	data and prints JSON to console

setTimeout(function() {
	// we will return both the raw request and recieve logs, but it
	// is easier to figure out how long the requests took in milisecs up here
	// and return a nice 'processed_requests' which also includes element size in bytes
	
	processed_requests = {}

	for (id in requested_urls){
		data = {}
	
		// request info should always work
		data['method'] = requested_urls[id]['method'];
		data['request_headers'] = requested_urls[id]['headers'];
		data['user_agent'] = page.settings.userAgent;
		data['start_time_offset'] = requested_urls[id]['time'] - start_load;

		// default referer to null, then try to pull out the referer from the request headers if present
		data['referer'] = null;
		for (i =0; i< requested_urls[id]['headers'].length; i++){
			if(requested_urls[id]['headers'][i]['name'].match(/referer/i)){
				data['referer'] = requested_urls[id]['headers'][i]['value'];
			}
		}
		
		// receive info will fail if we don't receive, so start with defaults
		data['received'] = false;
		data['load_time'] = null;
		data['status'] = '';
		data['status_text'] = '';
		data['content_type'] = '';
		data['body_size'] = null;
		data['response_headers'] = '';

		// try/catch to fail gracefully on non-received requests
		try{
			data['load_time'] = received_urls[id]['time'] - requested_urls[id]['time'];

			// if the request came back, we advance the last_load time
			if(received_urls[id]['time'] > last_load){last_load = received_urls[id]['time'];}

			data['status'] = received_urls[id]['status'];
			data['status_text'] = received_urls[id]['statusText'];
			data['content_type'] = received_urls[id]['contentType'];
			data['received'] = true;
			data['body_size'] = requested_bytes[id];
			data['response_headers'] = received_urls[id]['headers'];
		} catch(err) {}

		// pack it up!
		processed_requests[requested_urls[id]['url']] = data;	
	}

	// total load time is the last time we got anything and the time we started
	load_time = last_load - start_load;

	// get the page description, retreat to null
	meta_desc = page.evaluate(function() {
		var metas = document.getElementsByTagName('meta'), i, meta_desc = '';
		for (i = 0; i < metas.length; i++) {
			if(metas[i].name.match(/description/i)){
				meta_desc = metas[i].content;
			}
		}
		return meta_desc;
	});
	
	if(!meta_desc){
		meta_desc = null;
	}
	
	// phantomjs will use 'evaluate' to run js on the page, but it can
	// have conflicts with active scripts already on the page, so we copy
	// the source to a new object and operate on that, seems to work

	var safe_html = document.createElement('safe_html');
	safe_html.innerHTML = page.content;

	// return all the links for later processing
	all_links = []
	links = safe_html.getElementsByTagName('a');
	for (var i = 0; i < links.length; i++) {
		all_links.push([links[i].text, links[i].getAttribute('href')]);
	}

	// get title, retreat to null
	title = page.title;
	if(!title){
		title = null;
	}

	// get the language of the page
	lang = document.getElementsByTagName('html')[0].getAttribute('lang');
	if (!lang){
		lang = null
	}

	// build the JSON format python will expect
	return_dict = {
		final_url: final_url,
		title: title,
		load_time: load_time,
		meta_desc: meta_desc,
		lang: lang,
		processed_requests: processed_requests,
		cookies: phantom.cookies,
		all_links: all_links,
		// return source w/out line breaks
		source: page.content.replace(/[\t\n\r]/g, "")
	};

	// prints JSON to CLI, python reads this and processes
	console.log(JSON.stringify(return_dict, undefined, 4));
		
	// if there is no phantom.exit() the program will never return!
	phantom.exit();
	
}, wait_time*1000); // wait_time is passed in seconds, multiply to get milisecond value
