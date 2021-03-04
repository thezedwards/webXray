# run with:
#	gunicorn3 --workers=32 -k gevent -t 240 start_server:app --daemon
from flask import Flask, Response, request
from webxray.Server import Server

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def flask_handler():
	wbxr_server = Server()
	response = wbxr_server.process_request(request)
	return Response(response), 200

if __name__ == "__main__":
	app.run(debug=True)
