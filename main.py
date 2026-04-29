import http.server
import socketserver
import os
import requests
import json

PORT = 8000
WEB_DIR = 'webapp'
SECOND_API_URL = 'https://lens.indiamart.com/ajaxrequest/CombineSearchGateway'

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_POST(self):
        if self.path == '/proxy-api':
            self.proxy_request()
        else:
            super().do_POST()

    def do_GET(self):
        # Serve static files for GET requests
        super().do_GET()

    def proxy_request(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            # Forward the request to the actual API
            headers = {'Content-Type': 'application/json'}
            response = requests.post(SECOND_API_URL, data=post_data, headers=headers)
            
            # Send the API response back to the client
            self.send_response(response.status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.content)
        except requests.exceptions.RequestException as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_message = {"error": f"Proxy request failed: {str(e)}"}
            self.wfile.write(json.dumps(error_message).encode('utf-8'))

if __name__ == '__main__':
    # Ensure the webapp directory exists
    if not os.path.isdir(WEB_DIR):
        print(f"Error: The '{WEB_DIR}' directory was not found.")
        print("Please ensure 'index.html' and 'script.js' are inside a folder named 'webapp'.")
    else:
        with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
            print(f"Serving at port {PORT}")
            print(f"Proxying requests for {SECOND_API_URL} via /proxy-api")
            print(f"Open your browser to http://localhost:{PORT}")
            httpd.serve_forever()
