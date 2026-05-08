import http.server
import socketserver
import os

PORT = int(os.environ.get('PORT', 8004))

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Item Enrichment</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background-color: #f0f2f5; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            height: 100vh; 
            margin: 0; 
        }
        h1 { 
            font-size: 3.5rem; 
            color: #2c3e50; 
            margin-bottom: 50px; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .button-container { 
            display: flex; 
            gap: 40px; 
        }
        .btn { 
            padding: 20px 40px; 
            font-size: 1.5rem; 
            font-weight: bold;
            color: white; 
            background-color: #3498db; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            text-decoration: none; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
            transition: all 0.3s ease; 
        }
        .btn:hover { 
            background-color: #2980b9; 
            transform: translateY(-5px); 
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        }
        .btn-secondary { 
            background-color: #2ecc71; 
        }
        .btn-secondary:hover { 
            background-color: #27ae60; 
        }
        .top-right-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            font-size: 1rem;
            background-color: #95a5a6;
        }
        .top-right-btn:hover {
            background-color: #7f8c8d;
        }
    </style>
</head>
<body>
    <h1>Item Enrichment</h1>
    <div class="button-container">
        <a href="http://localhost:8002" target="_blank" class="btn">Item Master</a>
        <a href="http://localhost:8003" target="_blank" class="btn btn-secondary">Invoice Creation</a>
    </div>
    <a href="http://localhost:8000" target="_blank" class="btn top-right-btn">API Details</a>
</body>
</html>"""

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    is_on_cloud = os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud"
    if not is_on_cloud:
        current_port = PORT
        while True:
            try:
                with ReusableTCPServer(("", current_port), MyHandler) as httpd:
                    print(f"Serving Home Page at port {current_port}")
                    print(f"Open your browser to http://localhost:{current_port}")
                    httpd.serve_forever()
            except OSError as e:
                if e.errno == 48 or (os.name == 'nt' and e.errno == 10048):
                    print(f"Port {current_port} is already in use. Trying port {current_port + 1}...")
                    current_port += 1
                else:
                    raise
    else:
        print("Cloud deployment detected.")
