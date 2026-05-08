import http.server
import socketserver
import requests
import json
import csv
import os
import time
import traceback
from openai import OpenAI

PORT = int(os.environ.get('PORT', 8003))
SECOND_API_URL = 'https://lens.indiamart.com/ajaxrequest/CombineSearchGateway'
CSV_FILE_PATH = 'api_logs.csv'
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
INVOICE_MASTER_CSV = 'invoice_master.csv'

# Ensure OpenAI client is initialized
client = OpenAI(api_key=OPENAI_API_KEY)

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

# Initialize Invoice Master CSV if it doesn't exist
if not os.path.exists(INVOICE_MASTER_CSV):
    with open(INVOICE_MASTER_CSV, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            'Image (Base64)', 'Name', 'Description', 'HSN', 'Quantity', 'Purchase Price', 'List Price', 'Discount (%)', 'Final Price', 'Amount', 'Vendor Data', 'id'
        ])

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice Creation</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background-color: #f4f4f9;}
        /* Modal styles */
        .modal {
            display: none; 
            position: fixed; 
            z-index: 100; 
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
            max-height: 80vh;
            overflow-y: auto;
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
            background-color: #fff;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
            white-space: nowrap;
        }
        th {
            background-color: #f2f2f2;
        }
        .table-container {
            overflow-x: auto;
            margin-bottom: 20px;
        }
        .btn { padding: 8px 12px; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; background-color: #fff; font-size: 14px;}
        .btn:hover { background-color: #e9e9e9; }
        .btn-primary { background-color: #4CAF50; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; font-size: 16px;}
        .btn-primary:hover { background-color: #45a049; }
        .btn-info { background-color: #2196F3; color: white; border: none; padding: 8px 12px; cursor: pointer; border-radius: 4px;}
        .btn-info:hover { background-color: #0b7dda; }
        .btn-danger { background-color: #f44336; color: white; border: none; padding: 8px 12px; cursor: pointer; border-radius: 4px;}
        .btn-danger:hover { background-color: #d32f2f; }

        /* Item match modal styles */
        .match-card {
            border: 1px solid #ddd; border-radius: 8px; padding: 15px;
            margin-bottom: 15px; display: flex; gap: 20px; align-items: center; background-color: #fff;
        }
        .match-card img { width: 100px; height: 100px; object-fit: contain; border-radius: 4px; border: 1px solid #eee;}
        .match-details { flex-grow: 1; }
        .match-details h3 { margin: 0 0 5px 0; }
        .match-details p { margin: 3px 0; color: #555; }
        
        /* Form styles for final add */
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px;}
        .form-group input, .form-group textarea { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;}
        .form-row { display: flex; gap: 15px; }
        .form-row .form-group { flex: 1; }
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ccc; padding-bottom: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0;">Invoice Creation</h1>
        <div>
            <button id="createInvoiceBtn" class="btn-primary">+ Create Invoice</button>
            <input type="file" id="imageUpload" accept="image/*" style="display: none;">
        </div>
    </div>

    <!-- Status message -->
    <div id="statusMessage" style="margin-bottom: 20px; font-weight: bold; color: blue;"></div>

    <div style="display: flex; gap: 20px; align-items: flex-start;">
        <img id="imagePreview" src="" alt="Image Preview" style="max-width: 300px; max-height: 300px; display: none; border: 1px solid #ccc; border-radius: 4px; background-color: #fff;">
        <div id="actionButtons" style="display: none; flex-direction: column; gap: 10px;">
            <button id="showResultsBtn" class="btn btn-info">Show Extracted Results</button>
        </div>
    </div>

    <!-- The Modals -->
    <!-- Results Modal -->
    <div id="resultsModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="document.getElementById('resultsModal').style.display='none'">&times;</span>
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
        </div>
    </div>

    <!-- Vendors Modal -->
    <div id="vendorsModal" class="modal">
        <div class="modal-content" style="width: 95%;">
            <span class="close" onclick="document.getElementById('vendorsModal').style.display='none'">&times;</span>
            <h2>Vendor Options</h2>
            <div class="table-container" id="vendorModalContainer">
                <!-- Dynamically populated vendor tables go here -->
            </div>
        </div>
    </div>

    <!-- Match Selection Modal -->
    <div id="matchSelectionModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="document.getElementById('matchSelectionModal').style.display='none'">&times;</span>
            <h2>Matching Items Found</h2>
            <p id="matchContext" style="color: #666; margin-bottom: 15px;"></p>
            <div id="matchListContainer">
                <!-- Match cards will go here -->
            </div>
        </div>
    </div>

    <!-- Final Add Item Modal (Editable Form) -->
    <div id="finalAddItemModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="document.getElementById('finalAddItemModal').style.display='none'">&times;</span>
            <h2 id="finalAddTitle">Create Invoice</h2>
            <form id="finalItemForm">
                <div class="form-group">
                    <label for="itemName">Item Name *</label>
                    <input type="text" id="itemName" required>
                </div>
                <div class="form-group">
                    <label for="itemDesc">Item Description</label>
                    <textarea id="itemDesc" rows="3"></textarea>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="itemHSN">HSN</label>
                        <input type="text" id="itemHSN">
                    </div>
                    <div class="form-group">
                        <label for="itemQty">Quantity for Invoice</label>
                        <input type="number" id="itemQty" min="1" value="1" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="purchasePrice">Purchase Price</label>
                        <input type="number" id="purchasePrice" min="0" step="0.01">
                    </div>
                    <div class="form-group">
                        <label for="listPrice">List Price</label>
                        <input type="number" id="listPrice" min="0" step="0.01">
                    </div>
                    <div class="form-group">
                        <label for="discount">Discount (%)</label>
                        <input type="number" id="discount" min="0" max="100" step="0.01">
                    </div>
                    <div class="form-group">
                        <label for="sellingPrice">Final Price (Per Unit)</label>
                        <input type="number" id="sellingPrice" readonly style="background-color: #e0e0e0;">
                    </div>
                </div>
                
                <input type="hidden" id="hiddenItemImage">

                <div class="form-group" style="text-align: right; margin-top: 20px;">
                    <button type="button" class="btn" onclick="document.getElementById('finalAddItemModal').style.display='none'">Cancel</button>
                    <button type="submit" class="btn btn-primary" style="margin-left: 10px;">Save to Invoice</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Invoice Master Table -->
    <h2 style="margin-top: 50px;">Invoice Master</h2>
    <div class="table-container">
        <table id="invoiceTable">
            <thead>
                <tr>
                    <th>Image</th>
                    <th>Name</th>
                    <th>Description</th>
                    <th>HSN</th>
                    <th>Qty</th>
                    <th>Purchase Price</th>
                    <th>List Price</th>
                    <th>Discount (%)</th>
                    <th>Final Price</th>
                    <th>Amount</th>
                    <th>See Vendors</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <!-- Saved items go here -->
            </tbody>
        </table>
    </div>

    <script>
        let globalItemMasterData = [];
        let currentVendorDataHTML = ""; // Store current vendor table HTML (json representation)
        let currentInsightsData = {};

        // Function to fetch Item Master data from the backend CSV
        async function fetchItemMasterData() {
            try {
                const response = await fetch('/get-item-master');
                if (response.ok) {
                    const data = await response.json();
                    globalItemMasterData = data.items;
                    console.log("Fetched items from backend:", globalItemMasterData);
                } else {
                    console.error("Failed to fetch item master data from backend.");
                }
            } catch(e) {
                console.error("Error fetching item master:", e);
            }
        }
        
        // Ensure to fetch item master data on load
        fetchItemMasterData();
        
        async function fetchInvoiceData() {
            try {
                const response = await fetch('/get-invoice-data');
                if(response.ok){
                    const data = await response.json();
                    const tbody = document.querySelector('#invoiceTable tbody');
                    tbody.innerHTML = '';
                    data.items.forEach((item, index) => {
                         const tr = document.createElement('tr');
                         tr.id = `invoice-row-${item.id}`;
                         
                         let imgSrc = item.image;
                         // Check if it's a valid data URL or external URL, otherwise show nothing
                         if (!imgSrc || (!imgSrc.startsWith('data:image') && !imgSrc.startsWith('http'))) {
                             imgSrc = '';
                         }
                         const imgHtml = imgSrc ? `<img src="${imgSrc}" style="width: 50px; height: 50px; object-fit: contain;">` : 'No Image';
                         
                         // The vendorData was saved as JSON string, we just pass it to the onclick handler via data attribute
                         const vendorDataSafe = (item.vendorData || "").replace(/"/g, '&quot;');
                         const vendorHtml = `
                                <button class="btn btn-info" onclick="showVendorOptionsPop('${item.id}')" data-vendor="${vendorDataSafe}" id="btn-vendor-${item.id}">Show Vendor Options</button>
                         `;
                         
                         const amount = (parseFloat(item.quantity || 0) * parseFloat(item.finalPrice || 0)).toFixed(2);
                         
                         tr.innerHTML = `
                            <td>${imgHtml}</td>
                            <td>${item.name}</td>
                            <td>${item.description}</td>
                            <td>${item.hsn}</td>
                            <td>${item.quantity}</td>
                            <td>₹${item.purchasePrice}</td>
                            <td>₹${item.listPrice}</td>
                            <td>${item.discount}%</td>
                            <td style="font-weight: bold; color: #2e7d32;">₹${item.finalPrice}</td>
                            <td style="font-weight: bold; color: #2e7d32;">₹${amount}</td>
                            <td>
                                ${vendorHtml}
                            </td>
                            <td>
                                <button class="btn btn-danger" onclick="deleteInvoiceItem('${item.id}')">Delete</button>
                            </td>
                         `;
                         tbody.appendChild(tr);
                    });
                }
            } catch(e){
                console.error("Error fetching invoice data:", e);
            }
        }
        
        window.deleteInvoiceItem = async function(id) {
            if (confirm("Are you sure you want to delete this invoice item?")) {
                try {
                    const response = await fetch('/delete-invoice-item', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: id })
                    });
                    
                    if (response.ok) {
                        // Remove row from UI without full refresh to feel snappier
                        const row = document.getElementById(`invoice-row-${id}`);
                        if (row) row.remove();
                        console.log(`Deleted item ${id}`);
                    } else {
                        alert("Failed to delete item.");
                    }
                } catch(e) {
                    console.error("Error deleting item:", e);
                    alert("Error deleting item.");
                }
            }
        }
        
        window.showVendorOptionsPop = function(id) {
            const btn = document.getElementById(`btn-vendor-${id}`);
            if(!btn) return;
            const vendorDataStr = btn.getAttribute('data-vendor');
            
            if(!vendorDataStr) {
                alert("No vendor data available for this item.");
                return;
            }
            
            let vendorDataObj;
            try {
                vendorDataObj = JSON.parse(vendorDataStr);
            } catch(e) {
                console.error("Failed to parse vendor data:", e);
                alert("Failed to parse vendor data.");
                return;
            }
            
            const container = document.getElementById('vendorModalContainer');
            container.innerHTML = '';
            
            if(vendorDataObj.headers && vendorDataObj.rows && vendorDataObj.rows.length > 0){
                let vendorHtml = `<table class="vendorTablePop"><thead><tr>`;
                vendorDataObj.headers.forEach(h => {
                    vendorHtml += `<th>${h}</th>`;
                });
                vendorHtml += `</tr></thead><tbody>`;
                vendorDataObj.rows.forEach(r => {
                     vendorHtml += `<tr>`;
                     r.forEach(c => {
                         // re-render links and images
                         if (typeof c === 'string' && c.startsWith('http') && c.match(/\.(jpeg|jpg|gif|png|webp)$/i) != null) {
                            vendorHtml += `<td><img src="${c}" style="max-width: 100px;"></td>`;
                         } else if (typeof c === 'string' && c.startsWith('http')) {
                            vendorHtml += `<td><a href="${c}" target="_blank">Link</a></td>`;
                         } else {
                            vendorHtml += `<td>${c}</td>`;
                         }
                     });
                     vendorHtml += `</tr>`;
                });
                vendorHtml += `</tbody></table>`;
                container.innerHTML = vendorHtml;
                document.getElementById('vendorsModal').style.display = 'block';
            } else {
                alert("No vendor data available for this item.");
            }
        }
        
        // Initial fetch of invoice data
        fetchInvoiceData();

        // Modal handlers
        window.onclick = function(event) {
            const modals = [
                document.getElementById('resultsModal'), 
                document.getElementById('vendorsModal'),
                document.getElementById('matchSelectionModal'),
                document.getElementById('finalAddItemModal')
            ];
            modals.forEach(m => {
                if (event.target == m) {
                    m.style.display = "none";
                }
            });
        }
        
        // Buttons to show modals
        document.getElementById('showResultsBtn').onclick = () => document.getElementById('resultsModal').style.display = 'block';

        // Trigger file input when Create Invoice is clicked
        const createInvoiceBtn = document.getElementById('createInvoiceBtn');
        const imageUpload = document.getElementById('imageUpload');
        
        createInvoiceBtn.addEventListener('click', () => {
            imageUpload.value = ''; // Clear previous selection so 'change' fires even for the same file
            imageUpload.click();
        });

        imageUpload.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            
            if (!file) return;

            const imagePreview = document.getElementById('imagePreview');
            
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                imagePreview.style.display = 'block';
            }
            reader.readAsDataURL(file);
            
            // Automatically trigger the flow
            await processImageUpload(file);
            
            // Clear input value so selecting the same file again triggers change event
            event.target.value = '';
        });

        // Price calculation for final form
        const listPriceInput = document.getElementById('listPrice');
        const discountInput = document.getElementById('discount');
        const sellingPriceInput = document.getElementById('sellingPrice');

        function calculateSellingPrice() {
            const listPrice = parseFloat(listPriceInput.value) || 0;
            const discount = parseFloat(discountInput.value) || 0;
            const sellingPrice = listPrice - (listPrice * (discount / 100));
            sellingPriceInput.value = sellingPrice > 0 ? sellingPrice.toFixed(2) : 0;
        }

        listPriceInput.addEventListener('input', calculateSellingPrice);
        discountInput.addEventListener('input', calculateSellingPrice);

        // Save Invoice Item
        document.getElementById('finalItemForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const itemData = {
                id: Date.now().toString(), // Generate a unique ID for deletion
                name: document.getElementById('itemName').value,
                description: document.getElementById('itemDesc').value,
                hsn: document.getElementById('itemHSN').value,
                quantity: document.getElementById('itemQty').value,
                purchasePrice: document.getElementById('purchasePrice').value,
                listPrice: document.getElementById('listPrice').value,
                discount: document.getElementById('discount').value,
                finalPrice: document.getElementById('sellingPrice').value,
                image: document.getElementById('hiddenItemImage').value,
                vendorData: currentVendorDataHTML // The saved JSON string of vendor data
            };
            
            try {
                const response = await fetch('/save-invoice-item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(itemData)
                });
                
                if (response.ok) {
                    await fetchInvoiceData(); // Refresh the table
                    document.getElementById('finalAddItemModal').style.display = 'none';
                    document.getElementById('statusMessage').textContent = 'Item added to invoice!';
                    document.getElementById('statusMessage').style.color = 'green';
                } else {
                    throw new Error("Failed to save on server");
                }
            } catch(error) {
                console.error('Error saving invoice item:', error);
                document.getElementById('statusMessage').textContent = 'Failed to save item.';
                document.getElementById('statusMessage').style.color = 'red';
            }
        });

        async function processImageUpload(imageFile) {
            const statusMessage = document.getElementById('statusMessage');
            const actionButtons = document.getElementById('actionButtons');
            const resultsTableBody = document.querySelector('#resultsTable tbody');

            // Reset
            statusMessage.textContent = '';
            actionButtons.style.display = 'none';
            // KEEP results table row count at 1, replace previous result
            resultsTableBody.innerHTML = ''; 
            currentVendorDataHTML = "";
            currentInsightsData = {};

            const fileName = imageFile.name;
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
                // 1. First API Call
                const startTime1 = performance.now();
                const response1 = await fetch('https://uploading-external.imimg.com/uploadimage', {
                    method: 'POST',
                    body: formData
                });
                const endTime1 = performance.now();
                firstApiTimeTaken = (endTime1 - startTime1).toFixed(2);

                const response1Text = await response1.text();
                try {
                    firstApiResponseData = JSON.parse(response1Text);
                } catch (e) {
                    throw new Error("First API returned invalid JSON: " + response1Text);
                }

                const imageOriginalPath = firstApiResponseData.Data?.AwsPath?.Image_Original_Path;

                if (!imageOriginalPath) {
                    throw new Error('Image_Original_Path not found in the first API response.');
                }

                statusMessage.textContent = 'Image uploaded. Now calling second API...';

                // 2. Second API call payload
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

                const startTime2 = performance.now();
                const response2 = await fetch('/proxy-api', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(secondApiRequestPayload)
                });
                const endTime2 = performance.now();
                secondApiTimeTaken = (endTime2 - startTime2).toFixed(2);

                const response2Text = await response2.text();
                
                if (response2.status !== 200) {
                    try {
                        const errorJson = JSON.parse(response2Text);
                        throw new Error(errorJson.error || "Proxy request failed");
                    } catch(e) {
                            throw new Error("Proxy request failed: " + response2Text);
                    }
                }

                try {
                    secondApiResponseData = JSON.parse(response2Text);
                } catch (e) {
                    if (typeof response2Text === 'string' && response2Text.trim() === 'Too many requests') {
                        throw new Error("Too many requests");
                    }
                    throw new Error(response2Text || "Second API returned invalid JSON.");
                }
                
                statusMessage.textContent = 'Matching with Item Master...';
                actionButtons.style.display = 'flex'; // Show the buttons to view results

                // --- Extract and Populate Results Table ---
                const dataObj = secondApiResponseData.data || {};
                const analyzeImgObj = secondApiResponseData.analyze_img || {};
                const vlmPredictedTitle = dataObj.vlm_predicted_title || "";

                const formatData = (val) => {
                    if (val === undefined || val === null) return '';
                    if (typeof val === 'object') return JSON.stringify(val);
                    return val;
                };

                const newRow = document.createElement('tr');
                [
                    fileName,
                    vlmPredictedTitle,
                    dataObj.subcat_name,
                    secondApiResponseData.response_time,
                    dataObj.mcat_name,
                    analyzeImgObj.search_term
                ].forEach(cellData => {
                    const td = document.createElement('td');
                    td.textContent = formatData(cellData);
                    newRow.appendChild(td);
                });
                resultsTableBody.appendChild(newRow);

                // --- Extract Vendor Table Data ---
                const vendorResults = dataObj.results || [];
                let maxIsqCount = 0;
                vendorResults.forEach(vendor => {
                    if (vendor.ISQ_RESPONSE && Array.isArray(vendor.ISQ_RESPONSE)) {
                        if (vendor.ISQ_RESPONSE.length > maxIsqCount) {
                            maxIsqCount = vendor.ISQ_RESPONSE.length;
                        }
                    }
                });

                const baseHeaders = [
                    'Insights', // Added Insights at start
                    'COMPANYNAME', 'CITY_NAME', 'STATE_NAME', 'CONTACT_NUMBER',
                    'IMAGE_ORIGINAL', 'PC_ITEM_DISPLAY_NAME', 'PDP_URL', 'PRICE_SEO'
                ];
                
                let savedVendorHeaders = [...baseHeaders];
                
                let savedVendorRows = [];

                vendorResults.forEach(vendor => {
                    const vColsData = [
                        '', // Insights placeholder
                        vendor.COMPANYNAME, vendor.CITY_NAME, vendor.STATE_NAME, vendor.CONTACT_NUMBER,
                        vendor.IMAGE_ORIGINAL, vendor.PC_ITEM_DISPLAY_NAME, vendor.PDP_URL, vendor.PRICE_SEO
                    ];
                    
                    let savedRowData = [...vColsData];
                    savedVendorRows.push(savedRowData);
                });
                
                // Store vendor data as JSON string for later use when saving invoice.
                // We'll update the insights column in performLlmMatch when an item is selected.
                currentInsightsData = {
                    headers: savedVendorHeaders,
                    rows: savedVendorRows
                };

                // 3. Fetch Item Master Data from Backend before matching
                await fetchItemMasterData();

                // 4. LLM Matching Logic
                if (vlmPredictedTitle) {
                    await performLlmMatch(vlmPredictedTitle);
                } else {
                    statusMessage.textContent = 'Process completed, but no predicted title found to match.';
                    statusMessage.style.color = 'orange';
                }

            } catch (error) {
                console.error('Error during API calls:', error);
                statusMessage.textContent = `An error occurred: ${error.message}`;
                statusMessage.style.color = 'red';
            } finally {
                // Log to CSV
                try {
                    await fetch('/log-result', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
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
        }

        async function performLlmMatch(predictedTitle) {
            const statusMessage = document.getElementById('statusMessage');
            
            if (globalItemMasterData.length === 0) {
                alert(`Cannot match: You have no items saved in the Item Master.\nPlease go to the Item Master page and add some items first.`);
                statusMessage.textContent = `Predicted Title: "${predictedTitle}". No items in Item Master to match with.`;
                statusMessage.style.color = 'orange';
                return;
            }

            const itemNames = globalItemMasterData.map(item => item.name);

            // Call backend endpoint to do the LLM work
            try {
                const llmResponse = await fetch('/llm-match', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        predicted_title: predictedTitle,
                        item_names: itemNames
                    })
                });

                if (!llmResponse.ok) throw new Error("LLM match request failed");
                const llmResult = await llmResponse.json();

                // Parse the matched names returned by the LLM
                let matches = [];
                try {
                    matches = JSON.parse(llmResult.matches);
                } catch(e) {
                    console.error("Could not parse LLM output as JSON:", llmResult.matches);
                }

                if (!matches || matches.length === 0) {
                    statusMessage.textContent = `Predicted: "${predictedTitle}". No matches found in Item Master.`;
                    statusMessage.style.color = 'orange';
                    return;
                }
                
                // Sort matches by similarity_score descending
                matches.sort((a, b) => b.similarity_score - a.similarity_score);

                // Extract names from the sorted JSON format
                let matchedNames = matches.map(m => m.item_name);

                // Get full item details for the matched names, keeping the sorted order
                const matchedItems = matchedNames.map(name => globalItemMasterData.find(item => item.name === name)).filter(item => item !== undefined);

                if (matchedItems.length === 1) {
                    // Only one match, auto-fill final form
                    selectMatchForVendorInsights(matchedItems[0]);
                    openFinalAddModal(matchedItems[0]);
                    statusMessage.textContent = `Matched perfectly with "${matchedItems[0].name}"!`;
                    statusMessage.style.color = 'green';
                } else if (matchedItems.length > 1) {
                    // Multiple matches, show selection modal
                    showMatchSelectionModal(predictedTitle, matchedItems, matches);
                    statusMessage.textContent = `Found ${matchedItems.length} potential matches for "${predictedTitle}". Please select one.`;
                    statusMessage.style.color = 'blue';
                }

            } catch (error) {
                console.error("LLM Matching error:", error);
                statusMessage.textContent = "Error occurred during item matching.";
                statusMessage.style.color = 'red';
            }
        }

        function showMatchSelectionModal(predictedTitle, matchedItems, llmMatches) {
            document.getElementById('matchContext').textContent = `Predicted Item: "${predictedTitle}". We found multiple similar items in your inventory:`;
            const container = document.getElementById('matchListContainer');
            container.innerHTML = '';

            matchedItems.forEach(item => {
                // Find similarity score from LLM output
                const matchObj = llmMatches.find(m => m.item_name === item.name);
                const score = matchObj ? matchObj.similarity_score : "N/A";

                const card = document.createElement('div');
                card.className = 'match-card';
                
                const imgSrc = item.image || '';
                const imgHtml = imgSrc ? `<img src="${imgSrc}">` : `<div style="width:100px;height:100px;background:#eee;display:flex;align-items:center;justify-content:center;border:1px solid #ccc;border-radius:4px;color:#888;">No Img</div>`;

                card.innerHTML = `
                    ${imgHtml}
                    <div class="match-details">
                        <h3>${item.name}</h3>
                        <p>${item.description || 'No description'}</p>
                        <p><strong>Qty:</strong> ${item.quantity || 0} | <strong>Price:</strong> ₹${item.sellingPrice || 0}</p>
                        <p style="color: blue; font-weight: bold;">Similarity Score: ${score}</p>
                    </div>
                    <button class="btn btn-primary" onclick='selectMatch(${JSON.stringify(item).replace(/'/g, "&#39;")})'>Add</button>
                `;
                container.appendChild(card);
            });

            document.getElementById('matchSelectionModal').style.display = 'block';
        }

        function selectMatchForVendorInsights(itemObj) {
            // Calculate insights for each vendor row
            if(currentInsightsData && currentInsightsData.rows) {
                currentInsightsData.rows.forEach(row => {
                    const priceSEO = row[8] || ''; // PRICE_SEO is index 8 now
                    const purchasePrice = parseFloat(itemObj.purchasePrice || 0);
                    let savingsText = '';
                    
                    if (priceSEO && purchasePrice) {
                        const vendorPriceMatch = priceSEO.match(/₹\s*([0-9.,]+)/);
                        if (vendorPriceMatch) {
                            const vendorPrice = parseFloat(vendorPriceMatch[1].replace(/,/g, ''));
                            const diff = vendorPrice - purchasePrice;
                            if (diff > 0) {
                                savingsText = `<span style="color: red;">More by ₹${diff.toFixed(2)}</span>`;
                            } else if (diff < 0) {
                                savingsText = `<span style="color: green;">Saved ₹${Math.abs(diff).toFixed(2)}</span>`;
                            } else {
                                savingsText = `Same Price`;
                            }
                        }
                    } else if (purchasePrice) {
                        savingsText = `PP: ₹${purchasePrice}`;
                    }

                    const insightHtml = `
                        <ul style="margin:0; padding-left: 15px; font-size:0.9em;">
                            <li><strong>Savings:</strong> ${savingsText}</li>
                            <li><strong>GST Score:</strong> </li>
                            <li><strong>Customer Review:</strong> </li>
                        </ul>
                    `;
                    row[0] = insightHtml; // update Insights column
                });
                currentVendorDataHTML = JSON.stringify(currentInsightsData);
            }
        }

        // Must be global for the inline onclick to work
        window.selectMatch = function(itemObj) {
            document.getElementById('matchSelectionModal').style.display = 'none';
            selectMatchForVendorInsights(itemObj);
            openFinalAddModal(itemObj);
        };

        function openFinalAddModal(item) {
            document.getElementById('finalAddTitle').textContent = 'Create Invoice';
            document.getElementById('itemName').value = item.name || '';
            document.getElementById('itemDesc').value = item.description || '';
            document.getElementById('itemHSN').value = item.hsn || '';
            document.getElementById('itemQty').value = '1'; // Default invoice quantity to 1
            document.getElementById('purchasePrice').value = item.purchasePrice || '';
            document.getElementById('listPrice').value = item.listPrice || '';
            document.getElementById('discount').value = item.discount || '';
            document.getElementById('sellingPrice').value = item.sellingPrice || '';
            document.getElementById('hiddenItemImage').value = item.image || '';
            
            document.getElementById('finalAddItemModal').style.display = 'block';
        }

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
        elif self.path == '/get-item-master':
            items = []
            ITEM_MASTER_CSV = 'item_master_logs.csv'
            if os.path.exists(ITEM_MASTER_CSV):
                try:
                    with open(ITEM_MASTER_CSV, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            items.append({
                                'id': row.get('ID', ''),
                                'name': row.get('Name', ''),
                                'description': row.get('Description', ''),
                                'hsn': row.get('HSN', ''),
                                'quantity': row.get('Quantity', ''),
                                'purchasePrice': row.get('Purchase Price', ''),
                                'listPrice': row.get('List Price', ''),
                                'discount': row.get('Discount (%)', ''),
                                'sellingPrice': row.get('Selling Price', ''),
                                'image': row.get('Image (Base64)', '')
                            })
                except Exception as e:
                    print(f"Error reading item master CSV: {e}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"items": items}).encode('utf-8'))
        elif self.path == '/get-invoice-data':
            items = []
            if os.path.exists(INVOICE_MASTER_CSV):
                try:
                    with open(INVOICE_MASTER_CSV, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            items.append({
                                'id': row.get('id', str(time.time())), # fallback if old row
                                'image': row.get('Image (Base64)', ''),
                                'name': row.get('Name', ''),
                                'description': row.get('Description', ''),
                                'hsn': row.get('HSN', ''),
                                'quantity': row.get('Quantity', ''),
                                'purchasePrice': row.get('Purchase Price', ''),
                                'listPrice': row.get('List Price', ''),
                                'discount': row.get('Discount (%)', ''),
                                'finalPrice': row.get('Final Price', ''),
                                'amount': row.get('Amount', ''),
                                'vendorData': row.get('Vendor Data', '')
                            })
                except Exception as e:
                    print(f"Error reading invoice master CSV: {e}")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"items": items}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/proxy-api':
            self.proxy_request()
        elif self.path == '/log-result':
            self.log_result()
        elif self.path == '/llm-match':
            self.llm_match()
        elif self.path == '/save-invoice-item':
            self.save_invoice_item()
        elif self.path == '/delete-invoice-item':
            self.delete_invoice_item()
        else:
            self.send_response(404)
            self.end_headers()

    def delete_invoice_item(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode('utf-8'))
            target_id = data.get('id')
            
            if os.path.exists(INVOICE_MASTER_CSV):
                rows = []
                with open(INVOICE_MASTER_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        if row.get('id') != target_id:
                            rows.append(row)
                
                with open(INVOICE_MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                    
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print("Delete invoice error:", e)
            self.send_response(500)
            self.end_headers()

    def save_invoice_item(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            item_data = json.loads(post_data.decode('utf-8'))
            
            # calculate amount 
            try:
                qty = float(item_data.get('quantity', 0) or 0)
                final_price = float(item_data.get('finalPrice', 0) or 0)
                amount = round(qty * final_price, 2)
            except ValueError:
                amount = 0.00
                
            # If CSV doesn't have 'id' column yet, it's handled in initialization, but we append safely
            file_exists_and_has_headers = False
            if os.path.exists(INVOICE_MASTER_CSV):
                with open(INVOICE_MASTER_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    first_row = next(reader, None)
                    if first_row and 'id' in first_row:
                        file_exists_and_has_headers = True

            # If headers somehow mismatch, rewrite
            if not file_exists_and_has_headers:
                 pass # For robustness, we assume the init handles this now

            with open(INVOICE_MASTER_CSV, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    item_data.get('image', ''),
                    item_data.get('name', ''),
                    item_data.get('description', ''),
                    item_data.get('hsn', ''),
                    item_data.get('quantity', ''),
                    item_data.get('purchasePrice', ''),
                    item_data.get('listPrice', ''),
                    item_data.get('discount', ''),
                    item_data.get('finalPrice', ''),
                    str(amount),
                    item_data.get('vendorData', ''),
                    item_data.get('id', str(time.time()))
                ])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print("Invoice logging error:", e)
            self.send_response(500)
            self.end_headers()

    def log_result(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            log_data = json.loads(post_data.decode('utf-8'))
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
            print("Logging error:", e)
            self.send_response(500)
            self.end_headers()

    def proxy_request(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            actual_payload = json.loads(post_data.decode('utf-8'))
            headers = {'Content-Type': 'application/json'}
            response = requests.post(SECOND_API_URL, json=actual_payload, headers=headers)

            if response.status_code == 429 or response.text.strip() == "Too many requests":
                 self.send_response(429)
                 self.send_header('Content-type', 'application/json')
                 self.end_headers()
                 self.wfile.write(json.dumps({"error": "Too many requests"}).encode('utf-8'))
                 return

            self.send_response(response.status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as e:
             self.send_response(500)
             self.end_headers()

    def llm_match(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode('utf-8'))
            predicted_title = data.get('predicted_title')
            item_names = data.get('item_names', [])

            print("\n" + "="*50)
            print("🤖 LLM MATCHING INITIATED")
            print(f"VLM Predicted Title: '{predicted_title}'")
            print(f"Item Master Names: {item_names}")
            print("="*50)

            prompt = f"""
            You are an AI that evaluates the similarity between a predicted item title from an image search and a database of existing item names.
            
            Predicted Title: "{predicted_title}"
            
            Database Item Names:
            {json.dumps(item_names)}
            
            Evaluate if the database item names represent a similar item to the predicted title. 
            Allow for variations in naming as you think is a possiblity. Do this for every item name and then return a simiarity score for every item.
            
            Return ONLY a valid JSON array of objects for all objects(item names).
            Each object must have the following keys:
            - "item_name": The exact name from the database.
            - "similarity_score": A score from 0 to 100 indicating how similar the items are conceptually.
            - "reason": A very brief 1-sentence reason for the score.
            
            Example output format:
            [
              {{"item_name": "Coca Cola Cold Drink", "similarity_score": 95, "reason": "Both are cola beverages."}},
              {{"item_name": "Generic Cold Drink", "similarity_score": 60, "reason": "Both are cold drinks, but specific brand is missing."}}
            ]
            
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You output only raw valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            matched_output = response.choices[0].message.content.strip()
            
            # Format the raw output for frontend display
            raw_response_text = f"Sent: \nPredicted: '{predicted_title}'\nDB: {item_names}\n\nReceived: \n{matched_output}"
            
            print("\n" + "="*50)
            print("🧠 LLM RESPONSE RECEIVED")
            print(f"Raw Output:\n{matched_output}")
            print("="*50 + "\n")

            # Clean up potential markdown formatting if the model disobeys
            if matched_output.startswith("```json"):
                matched_output = matched_output[7:]
            if matched_output.endswith("```"):
                matched_output = matched_output[:-3]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "matches": matched_output.strip(),
                "raw_llm_response": raw_response_text # Send the formatted text back
            }).encode('utf-8'))

        except Exception as e:
            print("LLM Match error:", e)
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


# Custom TCPServer to set SO_REUSEADDR
class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    is_on_cloud = os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud"

    if not is_on_cloud:
        current_port = PORT
        while True:
            try:
                with ReusableTCPServer(("", current_port), MyHandler) as httpd:
                    print(f"Serving at port {current_port}")
                    print(f"Open your browser to http://localhost:{current_port}")
                    httpd.serve_forever()
            except OSError as e:
                if e.errno == 48 or (os.name == 'nt' and e.errno == 10048):
                    print(f"Port {current_port} is already in use. Trying port {current_port + 1}...")
                    current_port += 1
                else:
                    raise
    else:
        print("Detected Streamlit Cloud environment. Skipping local TCP server.")
