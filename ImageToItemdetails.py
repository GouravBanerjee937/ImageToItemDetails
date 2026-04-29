import http.server
import socketserver
import requests
import json
import csv
import os
import time

PORT = 8000
SECOND_API_URL = 'https://lens.indiamart.com/ajaxrequest/CombineSearchGateway'
CSV_FILE_PATH = 'api_logs.csv'

# Update existing CSV file to add File Name column and initial values
if os.path.exists(CSV_FILE_PATH):
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
    if reader and reader[0][0] != 'File Name':
        names = ["Water Bottle", "Tshirt", "Bicycle", "CocaCola", "Pen"]
        reader[0].insert(0, 'File Name')
        for i in range(1, len(reader)):
            name = names[i-1] if i-1 < len(names) else ""
            reader[i].insert(0, name)
        with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(reader)
else:
    # Initialize CSV file if it doesn't exist
    with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            'File Name',
            'First API Request (Payload)', 
            'First API Response', 
            'First API Time Taken (ms)', 
            'Second API Request', 
            'Second API Response', 
            'Second API Time Taken (ms)'
        ])

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Uploader</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
        /* Modal styles */
        .modal {
            display: none; 
            position: fixed; 
            z-index: 1; 
            left: 0;
            top: 0;
            width: 100%; 
            height: 100%; 
            overflow: auto; 
            background-color: rgba(0,0,0,0.4); 
        }
        .modal-content {
            background-color: #fefefe;
            margin: 5% auto; 
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
            border-radius: 5px;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover,
        .close:focus {
            color: black;
            text-decoration: none;
            cursor: pointer;
        }
        pre {
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
        /* Table styles */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            min-width: 600px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
            white-space: nowrap; /* Prevent wrapping in dynamic columns if possible */
        }
        th {
            background-color: #f2f2f2;
        }
        .table-container {
            overflow-x: auto;
            margin-bottom: 40px;
        }
    </style>
</head>
<body>
    <h1>Upload Image to API</h1>
    
    <div style="display: flex; align-items: flex-start; gap: 20px; margin-bottom: 20px;">
        <div>
            <input type="file" id="imageUpload" accept="image/*"><br><br>
            <button id="uploadButton">Upload Image</button>
            <button id="showJsonBtn" style="margin-left: 10px; display: none;">Show JSON Responses</button>
        </div>
        <img id="imagePreview" src="" alt="Image Preview" style="max-width: 300px; max-height: 300px; display: none; border: 1px solid #ccc; border-radius: 4px;">
    </div>

    <!-- Status message -->
    <div id="statusMessage" style="margin-bottom: 20px; font-weight: bold; color: blue;"></div>

    <!-- The Modal -->
    <div id="jsonModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>First API Response:</h2>
            <pre id="firstApiResponse"></pre>
            <h2>Extracted Image Path:</h2>
            <pre id="imagePath"></pre>
            <h2>Second API Request Payload:</h2>
            <pre id="secondApiRequestPayload"></pre>
            <h2>Final API Response:</h2>
            <pre id="apiResponse"></pre>
        </div>
    </div>

    <!-- Table to display extracted data -->
    <div id="resultsContainer" style="display: none;">
        <h2>Extracted Results</h2>
        <div class="table-container">
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th>File Name</th>
                        <th>Vlm Predicted Title</th>
                        <th>Subcat Name</th>
                        <th>Response Time</th>
                        <th>Mcat Name</th>
                        <th>Search Term</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Rows will be added here -->
                </tbody>
            </table>
        </div>

        <h2>Vendor Options</h2>
        <div class="table-container">
            <table id="vendorTable">
                <thead>
                    <tr id="vendorTableHeadRow">
                        <!-- Base headers will be injected here -->
                        <!-- Dynamic ISQ headers will be injected here -->
                    </tr>
                </thead>
                <tbody>
                    <!-- Rows will be added here -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Modal logic
        const modal = document.getElementById("jsonModal");
        const btn = document.getElementById("showJsonBtn");
        const span = document.getElementsByClassName("close")[0];

        btn.onclick = function() {
            modal.style.display = "block";
        }

        span.onclick = function() {
            modal.style.display = "none";
        }

        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }

        document.getElementById('imageUpload').addEventListener('change', (event) => {
            const file = event.target.files[0];
            const imagePreview = document.getElementById('imagePreview');
            
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                }
                reader.readAsDataURL(file);
            } else {
                imagePreview.src = '';
                imagePreview.style.display = 'none';
            }
        });

        document.getElementById('uploadButton').addEventListener('click', async () => {
            const imageUpload = document.getElementById('imageUpload');
            const firstApiResponseDisplay = document.getElementById('firstApiResponse');
            const imagePathDisplay = document.getElementById('imagePath');
            const secondApiRequestPayloadDisplay = document.getElementById('secondApiRequestPayload');
            const apiResponseDisplay = document.getElementById('apiResponse');
            const statusMessage = document.getElementById('statusMessage');
            const showJsonBtn = document.getElementById('showJsonBtn');
            const resultsContainer = document.getElementById('resultsContainer');
            const resultsTableBody = document.querySelector('#resultsTable tbody');
            const vendorTableHeadRow = document.getElementById('vendorTableHeadRow');
            const vendorTableBody = document.querySelector('#vendorTable tbody');

            // Clear previous content
            firstApiResponseDisplay.textContent = '';
            imagePathDisplay.textContent = '';
            secondApiRequestPayloadDisplay.textContent = '';
            apiResponseDisplay.textContent = '';
            statusMessage.textContent = '';
            showJsonBtn.style.display = 'none';
            vendorTableHeadRow.innerHTML = ''; // Clear headers
            vendorTableBody.innerHTML = ''; // Clear previous vendor data

            if (imageUpload.files.length === 0) {
                statusMessage.textContent = 'Please select an image first.';
                statusMessage.style.color = 'red';
                return;
            }

            const imageFile = imageUpload.files[0];
            const fileName = imageFile.name; // Extract the file name
            const formData = new FormData();
            formData.append('IMAGE', imageFile);
            formData.append('MODID', 'PHOTOSEARCH');
            formData.append('IMAGE_TYPE', 'ImgSearch');
            formData.append('USR_ID', '18882828');
            formData.append('UPLOADED_BY', '94011');

            statusMessage.textContent = 'Uploading image to first API...';
            statusMessage.style.color = 'blue';

            let firstApiRequestPayloadString = "MODID=PHOTOSEARCH, IMAGE_TYPE=ImgSearch, USR_ID=18882828, UPLOADED_BY=94011, IMAGE=[File]";
            let firstApiResponseData = {};
            let firstApiTimeTaken = 0;
            let secondApiRequestPayload = {};
            let secondApiResponseData = {};
            let secondApiTimeTaken = 0;

            try {
                // First API call
                const startTime1 = performance.now();
                const response1 = await fetch('https://uploading-external.imimg.com/uploadimage', {
                    method: 'POST',
                    body: formData
                });
                const endTime1 = performance.now();
                firstApiTimeTaken = (endTime1 - startTime1).toFixed(2);

                firstApiResponseData = await response1.json();
                
                // Display the full first API response in modal
                firstApiResponseDisplay.textContent = JSON.stringify(firstApiResponseData, null, 2);

                // Access the nested Image_Original_Path
                const imageOriginalPath = firstApiResponseData.Data?.AwsPath?.Image_Original_Path;

                if (imageOriginalPath) {
                    imagePathDisplay.textContent = imageOriginalPath;
                    statusMessage.textContent = 'Image uploaded. Now calling second API...';

                    // Second API call payload
                    secondApiRequestPayload = {
                        "Case": "normal",
                        "Image_url": imageOriginalPath,
                        "glid": "208238145",
                        "modid": "photo_search",
                        "ip": "103.226.203.223",
                        "usr_id": "208238145",
                        "add_input": {},
                        "urlmet": "prod",
                        "hybrid": "1",
                        "object_detection": "1"
                    };

                    // Display the second API request payload in modal
                    secondApiRequestPayloadDisplay.textContent = JSON.stringify(secondApiRequestPayload, null, 2);

                    // Send request to the Python proxy endpoint
                    const startTime2 = performance.now();
                    const response2 = await fetch('/proxy-api', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(secondApiRequestPayload) // Send only the actual payload to proxy
                    });
                    const endTime2 = performance.now();
                    secondApiTimeTaken = (endTime2 - startTime2).toFixed(2);

                    secondApiResponseData = await response2.json();
                    
                    // Display final response in modal
                    apiResponseDisplay.textContent = JSON.stringify(secondApiResponseData, null, 2);
                    
                    statusMessage.textContent = 'Process completed successfully!';
                    statusMessage.style.color = 'green';
                    showJsonBtn.style.display = 'inline-block'; // Show the button
                    resultsContainer.style.display = 'block';

                    // --- Extract and Populate Table ---
                    const dataObj = secondApiResponseData.data || {};
                    const analyzeImgObj = secondApiResponseData.analyze_img || {};

                    // Create a new row
                    const newRow = document.createElement('tr');

                    // Helper function to format arrays/objects
                    const formatData = (val) => {
                        if (val === undefined || val === null) return '';
                        if (typeof val === 'object') return JSON.stringify(val);
                        return val;
                    };

                    const colsData = [
                        fileName,
                        dataObj.vlm_predicted_title,
                        dataObj.subcat_name,
                        secondApiResponseData.response_time, // Or dataObj.response_time depending on exact structure
                        dataObj.mcat_name,
                        analyzeImgObj.search_term
                    ];

                    colsData.forEach(cellData => {
                        const td = document.createElement('td');
                        td.textContent = formatData(cellData);
                        newRow.appendChild(td);
                    });

                    resultsTableBody.appendChild(newRow);

                    // --- Extract and Populate Vendor Table ---
                    const vendorResults = dataObj.results || [];
                    
                    // 1. Determine maximum number of ISQ_RESPONSE objects across all vendors
                    let maxIsqCount = 0;
                    vendorResults.forEach(vendor => {
                        if (vendor.ISQ_RESPONSE && Array.isArray(vendor.ISQ_RESPONSE)) {
                            if (vendor.ISQ_RESPONSE.length > maxIsqCount) {
                                maxIsqCount = vendor.ISQ_RESPONSE.length;
                            }
                        }
                    });

                    // 2. Build Table Headers
                    const baseHeaders = [
                        'COMPANYNAME', // Brought to first
                        'CITY_NAME',
                        'STATE_NAME',
                        'CONTACT_NUMBER',
                        'GLCAT_CAT_NAME',
                        'GLCAT_MCAT_NAME',
                        'IMAGE_ORIGINAL',
                        'PC_ITEM_DISPLAY_NAME',
                        'PDP_URL',
                        'PRICE_SEO'
                    ];

                    baseHeaders.forEach(headerText => {
                        const th = document.createElement('th');
                        th.textContent = headerText;
                        vendorTableHeadRow.appendChild(th);
                    });

                    // Add dynamic headers for ISQ_RESPONSE
                    for (let i = 1; i <= maxIsqCount; i++) {
                        ['FK_IM_SPEC_MASTER_DESC', 'IM_SPEC_OPTIONS_DESC', 'SUPPLIER_RESPONSE_DETAIL'].forEach(colPrefix => {
                            const th = document.createElement('th');
                            th.textContent = `${colPrefix} ${i}`;
                            vendorTableHeadRow.appendChild(th);
                        });
                    }

                    // 3. Populate Rows
                    vendorResults.forEach(vendor => {
                        const vRow = document.createElement('tr');
                        
                        // Populate base columns
                        const vColsData = [
                            vendor.COMPANYNAME,
                            vendor.CITY_NAME,
                            vendor.STATE_NAME,
                            vendor.CONTACT_NUMBER,
                            vendor.GLCAT_CAT_NAME,
                            vendor.GLCAT_MCAT_NAME,
                            vendor.IMAGE_ORIGINAL,
                            vendor.PC_ITEM_DISPLAY_NAME,
                            vendor.PDP_URL,
                            vendor.PRICE_SEO
                        ];

                        vColsData.forEach(cellData => {
                            const td = document.createElement('td');
                            
                            // To make the original image and URL clickable/viewable
                            if (typeof cellData === 'string' && cellData.startsWith('http') && cellData.match(/\.(jpeg|jpg|gif|png|webp)$/i) != null) {
                                const img = document.createElement('img');
                                img.src = cellData;
                                img.style.maxWidth = '100px';
                                td.appendChild(img);
                            } else if (typeof cellData === 'string' && cellData.startsWith('http')) {
                                const a = document.createElement('a');
                                a.href = cellData;
                                a.target = '_blank';
                                a.textContent = 'Link';
                                td.appendChild(a);
                            } else {
                                td.textContent = formatData(cellData);
                            }
                            
                            vRow.appendChild(td);
                        });

                        // Populate ISQ_RESPONSE dynamic columns
                        const isqArray = vendor.ISQ_RESPONSE || [];
                        for (let i = 0; i < maxIsqCount; i++) {
                            const isqObj = isqArray[i] || {};
                            
                            // Create cells for the 3 specific keys
                            const keys = ['FK_IM_SPEC_MASTER_DESC', 'IM_SPEC_OPTIONS_DESC', 'SUPPLIER_RESPONSE_DETAIL'];
                            keys.forEach(key => {
                                const td = document.createElement('td');
                                td.textContent = formatData(isqObj[key]);
                                vRow.appendChild(td);
                            });
                        }

                        vendorTableBody.appendChild(vRow);
                    });

                } else {
                    statusMessage.textContent = 'Error: Image_Original_Path not found in the first API response.';
                    statusMessage.style.color = 'red';
                    imagePathDisplay.textContent = '---'; // Indicate that the path was not found
                    showJsonBtn.style.display = 'inline-block';
                }

            } catch (error) {
                console.error('Error during API calls:', error);
                statusMessage.textContent = `An error occurred: ${error.message}`;
                statusMessage.style.color = 'red';
                apiResponseDisplay.textContent = `An error occurred: ${error.message}`;
                showJsonBtn.style.display = 'inline-block';
            } finally {
                // Log results to CSV via Python backend
                try {
                    await fetch('/log-result', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            fileName: fileName,
                            firstApiRequest: firstApiRequestPayloadString,
                            firstApiResponse: JSON.stringify(firstApiResponseData),
                            firstApiTime: firstApiTimeTaken,
                            secondApiRequest: JSON.stringify(secondApiRequestPayload),
                            secondApiResponse: JSON.stringify(secondApiResponseData),
                            secondApiTime: secondApiTimeTaken
                        })
                    });
                } catch (logError) {
                    console.error('Error sending log data to backend:', logError);
                }
            }
        });
    </script>
</body>
</html>
"""

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            # For any other GET request, return 404
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/proxy-api':
            self.proxy_request()
        elif self.path == '/log-result':
            self.log_result()
        else:
            # For any other POST request, return 404
            self.send_response(404)
            self.end_headers()

    def log_result(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            log_data = json.loads(post_data.decode('utf-8'))
            
            # Write to CSV
            with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    log_data.get('fileName', ''),
                    log_data.get('firstApiRequest', ''),
                    log_data.get('firstApiResponse', ''),
                    log_data.get('firstApiTime', ''),
                    log_data.get('secondApiRequest', ''),
                    log_data.get('secondApiResponse', ''),
                    log_data.get('secondApiTime', '')
                ])
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_message = {"error": f"Logging failed: {str(e)}"}
            self.wfile.write(json.dumps(error_message).encode('utf-8'))

    def proxy_request(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            # The frontend now sends only the secondApiPayload to /proxy-api
            actual_payload = json.loads(post_data.decode('utf-8'))
            
            # Forward the request to the actual API
            headers = {'Content-Type': 'application/json'}
            response = requests.post(SECOND_API_URL, json=actual_payload, headers=headers)

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
        except Exception as e:
             self.send_response(500)
             self.send_header('Content-type', 'application/json')
             self.end_headers()
             error_message = {"error": f"Server error: {str(e)}"}
             self.wfile.write(json.dumps(error_message).encode('utf-8'))

# Custom TCPServer to set SO_REUSEADDR
class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    current_port = PORT
    while True:
        try:
            with ReusableTCPServer(("", current_port), MyHandler) as httpd:
                print(f"Serving at port {current_port}")
                print(f"Proxying requests for {SECOND_API_URL} via /proxy-api")
                print(f"Logging results to {CSV_FILE_PATH} via /log-result")
                print(f"Open your browser to http://localhost:{current_port}")
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 48:
                print(f"Port {current_port} is already in use. Trying port {current_port + 1}...")
                current_port += 1
            else:
                raise
