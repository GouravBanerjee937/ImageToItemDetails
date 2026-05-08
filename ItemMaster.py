import http.server
import socketserver
import os
import json
import csv
import traceback

PORT = int(os.environ.get('PORT', 8002))
ITEM_MASTER_CSV = 'item_master_logs.csv'

# Initialize CSV if it doesn't exist
if not os.path.exists(ITEM_MASTER_CSV):
    with open(ITEM_MASTER_CSV, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            'ID', 'Name', 'Description', 'HSN', 'Quantity', 'Purchase Price', 'List Price', 'Discount (%)', 'Selling Price', 'Image (Base64)'
        ])

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Item Master</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background-color: #f4f4f9;}
        .btn { padding: 8px 12px; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; background-color: #fff; font-size: 14px;}
        .btn:hover { background-color: #e9e9e9; }
        .btn-primary { background-color: #4CAF50; color: white; border: none; }
        .btn-primary:hover { background-color: #45a049; }
        .btn-danger { background-color: #f44336; color: white; border: none; }
        .btn-danger:hover { background-color: #d32f2f; }

        /* Modal styles */
        .modal {
            display: none; position: fixed; z-index: 10; left: 0; top: 0;
            width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: #fefefe; margin: 5% auto; padding: 20px;
            border: 1px solid #888; width: 50%; border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: black; }

        /* Form styles */
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px;}
        .form-group input, .form-group textarea { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;}
        .form-row { display: flex; gap: 15px; }
        .form-row .form-group { flex: 1; }

        /* Items Grid styles */
        #itemsList {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }

        /* Item Card styles */
        .item-card {
            border: 1px solid #ddd; border-radius: 8px; padding: 15px;
            background-color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            display: flex; flex-direction: column; align-items: center; text-align: center;
            position: relative;
        }
        .item-card .actions {
            position: absolute; top: 10px; right: 10px; display: flex; gap: 5px;
        }
        .item-card .actions button {
            padding: 4px 8px; font-size: 12px;
        }
        
        .item-card img { width: 100%; height: 200px; border-radius: 4px; object-fit: contain; margin-bottom: 15px;}
        .no-image { width: 100%; height: 200px; background: #eee; display: flex; align-items: center; justify-content: center; border: 1px solid #ccc; border-radius: 4px; color: #888; margin-bottom: 15px;}
        
        .item-details { width: 100%; text-align: left;}
        .item-details h3 { margin: 0 0 10px 0; color: #333; font-size: 18px; text-align: center;}
        .item-details p { margin: 4px 0; color: #555; font-size: 13px; line-height: 1.4;}
        .price-highlight { font-size: 14px !important; color: #2e7d32 !important; font-weight: bold; margin-top: 8px !important;}
        .detail-row { display: flex; justify-content: space-between; border-bottom: 1px solid #f0f0f0; padding-bottom: 4px; margin-bottom: 4px;}
        .detail-row:last-child { border-bottom: none;}
    </style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ccc; padding-bottom: 10px;">
        <h1 style="margin: 0;">Item Master</h1>
        <button id="addItemBtn" class="btn btn-primary" type="button">+ Add item</button>
    </div>

    <div id="itemsList">
        <!-- Items will be rendered here dynamically -->
    </div>

    <!-- Add/Edit Item Modal -->
    <div id="itemModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2 id="modalTitle">Add New Item</h2>
            <form id="itemForm">
                <input type="hidden" id="itemId">
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
                        <label for="itemQty">Available Quantity</label>
                        <input type="number" id="itemQty" min="0">
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
                        <label for="sellingPrice">Selling Price</label>
                        <input type="number" id="sellingPrice" readonly style="background-color: #e0e0e0;">
                    </div>
                </div>

                <div class="form-group">
                    <label for="itemImage">Item Image</label>
                    <input type="file" id="itemImage" accept="image/*">
                    <img id="imagePreview" style="max-width: 150px; max-height: 150px; display: none; margin-top: 10px; border: 1px solid #ccc; border-radius: 4px;" />
                </div>

                <div class="form-group" style="text-align: right; margin-top: 20px;">
                    <button type="button" id="cancelBtn" class="btn">Cancel</button>
                    <button type="submit" class="btn btn-primary" style="margin-left: 10px;">Save</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Helper to log to Python backend
        async function logToBackend(errorObj) {
            try {
                await fetch('/log-error', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(errorObj)
                });
            } catch(e) {
                console.error("Failed to send log to backend:", e);
            }
        }

        // Helper to log item to CSV via backend
        async function logItemToCSV(itemData) {
            try {
                const response = await fetch('/log-item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(itemData)
                });
                if (!response.ok) {
                     const errText = await response.text();
                     logToBackend({error: "CSV Log failed", stack: errText});
                }
            } catch(e) {
                console.error("Failed to log item to CSV:", e);
                logToBackend({ error: "CSV Fetch Error: " + e.message, stack: e.stack });
            }
        }
        
        async function deleteItemFromCSV(itemId) {
            try {
                const response = await fetch('/delete-item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({id: itemId})
                });
                if (!response.ok) {
                     console.error("Failed to delete from CSV");
                }
            } catch(e) {
                console.error("Failed to delete item from CSV:", e);
            }
        }

        // DOM Elements
        const modal = document.getElementById('itemModal');
        const modalTitle = document.getElementById('modalTitle');
        const addItemBtn = document.getElementById('addItemBtn');
        const closeBtn = document.getElementsByClassName('close')[0];
        const cancelBtn = document.getElementById('cancelBtn');
        const itemForm = document.getElementById('itemForm');
        const itemsList = document.getElementById('itemsList');

        const itemIdInput = document.getElementById('itemId');
        const purchasePriceInput = document.getElementById('purchasePrice');
        const listPriceInput = document.getElementById('listPrice');
        const discountInput = document.getElementById('discount');
        const sellingPriceInput = document.getElementById('sellingPrice');
        const itemImageInput = document.getElementById('itemImage');
        const imagePreview = document.getElementById('imagePreview');

        let currentImageBase64 = '';

        // 1. Initialize items from backend CSV
        let items = [];
        async function loadItems() {
            try {
                const response = await fetch('/get-items');
                if (response.ok) {
                    const data = await response.json();
                    items = data.items;
                    localStorage.setItem('itemMasterData', JSON.stringify(items)); // Sync local storage
                    renderItems();
                } else {
                    console.error("Failed to fetch items from server.");
                }
            } catch(e) {
                console.error("Error fetching items:", e);
                logToBackend({ error: "Fetch Items Error: " + e.message, stack: e.stack });
            }
        }

        // 2. Calculate Selling Price
        function calculateSellingPrice() {
            const listPrice = parseFloat(listPriceInput.value) || 0;
            const discount = parseFloat(discountInput.value) || 0;
            const sellingPrice = listPrice - (listPrice * (discount / 100));
            sellingPriceInput.value = sellingPrice > 0 ? sellingPrice.toFixed(2) : 0;
        }

        listPriceInput.addEventListener('input', calculateSellingPrice);
        discountInput.addEventListener('input', calculateSellingPrice);

        // 3. Handle Image Preview and Base64 Conversion (With Compression)
        itemImageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    // Compress image to prevent QuotaExceededError in localStorage
                    const img = new Image();
                    img.onload = function() {
                        try {
                            const canvas = document.createElement('canvas');
                            let width = img.width;
                            let height = img.height;
                            const MAX_SIZE = 800; // Resize to max 800px

                            if (width > height && width > MAX_SIZE) {
                                height *= MAX_SIZE / width;
                                width = MAX_SIZE;
                            } else if (height > MAX_SIZE) {
                                width *= MAX_SIZE / height;
                                height = MAX_SIZE;
                            }

                            canvas.width = width;
                            canvas.height = height;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0, width, height);

                            currentImageBase64 = canvas.toDataURL('image/jpeg', 0.8);
                            imagePreview.src = currentImageBase64;
                            imagePreview.style.display = 'block';
                        } catch(err) {
                            logToBackend({ error: "Image Compression Error: " + err.message, stack: err.stack });
                        }
                    };
                    img.onerror = function() {
                        logToBackend({ error: "Image Load Error", stack: "Could not load image into Image object." });
                    }
                    img.src = event.target.result;
                };
                reader.onerror = function(error) {
                    console.error("Error reading file:", error);
                    logToBackend({ error: "FileReader Error", stack: "Could not read file as data URL." });
                };
                reader.readAsDataURL(file);
            } else {
                // Keep existing image if they cancel file selection while editing
                if (!currentImageBase64) {
                    imagePreview.style.display = 'none';
                    imagePreview.src = '';
                }
            }
        });

        // 4. Modal Open/Close Logic
        function openModal(isEdit = false) {
            modal.style.display = 'block';
            modalTitle.textContent = isEdit ? 'Edit Item' : 'Add New Item';
        }

        function closeModal() {
            modal.style.display = 'none';
            itemForm.reset();
            itemIdInput.value = '';
            currentImageBase64 = '';
            itemImageInput.value = ''; // Reset file input
            imagePreview.style.display = 'none';
            imagePreview.src = '';
        }

        addItemBtn.onclick = (e) => {
            e.preventDefault();
            closeModal(); // Reset form first
            openModal(false);
        };
        
        closeBtn.onclick = closeModal;
        cancelBtn.onclick = closeModal;
        window.onclick = (e) => { if (e.target == modal) closeModal(); };

        // 5. Handle Form Submission (Save/Update Item)
        itemForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            try {
                const id = itemIdInput.value;
                const itemData = {
                    name: document.getElementById('itemName').value,
                    description: document.getElementById('itemDesc').value,
                    hsn: document.getElementById('itemHSN').value,
                    quantity: document.getElementById('itemQty').value,
                    purchasePrice: document.getElementById('purchasePrice').value,
                    listPrice: document.getElementById('listPrice').value,
                    discount: document.getElementById('discount').value,
                    sellingPrice: document.getElementById('sellingPrice').value,
                    image: currentImageBase64
                };

                if (id) {
                    // Update existing
                    const index = items.findIndex(i => i.id == id);
                    if (index !== -1) {
                        itemData.id = items[index].id; // Preserve original ID
                        items[index] = { ...items[index], ...itemData };
                    }
                } else {
                    // Add new
                    itemData.id = Date.now().toString();
                    items.push(itemData);
                }

                localStorage.setItem('itemMasterData', JSON.stringify(items));
                
                // Log to backend CSV (upserts instead of purely appending)
                await logItemToCSV(itemData);

                renderItems();
                closeModal();
            } catch(error) {
                console.error("Error saving item:", error);
                logToBackend({ error: error.message, stack: error.stack });

                if (error.name === 'QuotaExceededError') {
                    alert("Failed to save: Image is too large for local storage! Try a smaller image.");
                } else {
                    alert("An error occurred while saving. Check terminal for details.");
                }
            }
        });

        // Delete Item
        window.deleteItem = async function(id) {
            if (confirm("Are you sure you want to delete this item?")) {
                items = items.filter(item => item.id != id);
                try {
                    localStorage.setItem('itemMasterData', JSON.stringify(items));
                } catch(e) {
                    logToBackend({ error: "Delete Error: " + e.message, stack: e.stack });
                }
                
                await deleteItemFromCSV(id);
                renderItems();
            }
        };

        // Edit Item
        window.editItem = function(id) {
            const item = items.find(i => i.id == id);
            if (item) {
                itemIdInput.value = item.id;
                document.getElementById('itemName').value = item.name;
                document.getElementById('itemDesc').value = item.description;
                document.getElementById('itemHSN').value = item.hsn;
                document.getElementById('itemQty').value = item.quantity;
                document.getElementById('purchasePrice').value = item.purchasePrice || '';
                document.getElementById('listPrice').value = item.listPrice;
                document.getElementById('discount').value = item.discount;
                document.getElementById('sellingPrice').value = item.sellingPrice;
                
                currentImageBase64 = item.image || '';
                if (currentImageBase64) {
                    imagePreview.src = currentImageBase64;
                    imagePreview.style.display = 'block';
                } else {
                    imagePreview.style.display = 'none';
                    imagePreview.src = '';
                }
                
                openModal(true);
            }
        };

        // 6. Render Items to the Screen
        function renderItems() {
            itemsList.innerHTML = ''; 

            if (items.length === 0) {
                itemsList.style.display = 'block';
                itemsList.innerHTML = '<p style="color: #666; text-align:center; width:100%;">No items available. Click "+ Add item" to create one.</p>';
                return;
            }
            
            itemsList.style.display = 'grid';

            // Loop through items in reverse to show newest first
            [...items].reverse().forEach(item => {
                const card = document.createElement('div');
                card.className = 'item-card';

                const imgHtml = item.image
                    ? `<img src="${item.image}" alt="${item.name}">`
                    : `<div class="no-image">No Image</div>`;

                card.innerHTML = `
                    <div class="actions">
                        <button class="btn" onclick="editItem('${item.id}')" title="Edit">✎</button>
                        <button class="btn btn-danger" onclick="deleteItem('${item.id}')" title="Delete">✖</button>
                    </div>
                    ${imgHtml}
                    <div class="item-details">
                        <h3>${item.name}</h3>
                        <p style="margin-bottom:10px;">${item.description || 'No description'}</p>
                        
                        <div class="detail-row">
                            <span><strong>HSN:</strong> ${item.hsn || '-'}</span>
                            <span><strong>Qty:</strong> ${item.quantity || '0'}</span>
                        </div>
                        <div class="detail-row">
                            <span><strong>Purch. Price:</strong> ₹${item.purchasePrice || '0'}</span>
                            <span><strong>List Price:</strong> ₹${item.listPrice || '0'}</span>
                        </div>
                        <div class="detail-row">
                            <span><strong>Disc:</strong> ${item.discount || '0'}%</span>
                            <span class="price-highlight">Selling Price: ₹${item.sellingPrice || '0'}</span>
                        </div>
                    </div>
                `;
                itemsList.appendChild(card);
            });
        }

        // Run render function on initial load
        loadItems();
    </script>
</body>
</html>
"""

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif self.path == '/get-items':
            items = []
            if os.path.exists(ITEM_MASTER_CSV):
                try:
                    with open(ITEM_MASTER_CSV, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Map CSV headers back to JS object keys
                            items.append({
                                'id': row.get('ID', ''),
                                'name': row.get('Name', ''),
                                'description': row.get('Description', ''),
                                'hsn': row.get('HSN', ''),
                                'quantity': row.get('Quantity', ''),
                                'purchasePrice': row.get('Purchase Price', row.get('Purchase price', '')),
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
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/log-error':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                error_data = json.loads(post_data.decode('utf-8'))
                print(f"\n" + "="*50)
                print(f"❌ FRONTEND ERROR LOGGED:")
                print(f"Message: {error_data.get('error')}")
                print(f"Stack:   {error_data.get('stack')}")
                print("="*50 + "\n")
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                print(f"Failed to parse frontend error log: {e}")
                self.send_response(500)
                self.end_headers()
        elif self.path == '/delete-item':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                target_id = str(data.get('id'))
                if os.path.exists(ITEM_MASTER_CSV):
                    rows = []
                    with open(ITEM_MASTER_CSV, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        header = next(reader, None)
                        if header:
                            rows.append(header)
                        for row in reader:
                            if row and str(row[0]) != target_id:
                                rows.append(row)
                                
                    with open(ITEM_MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                print(f"Failed to delete item from CSV: {e}")
                self.send_response(500)
                self.end_headers()
        elif self.path == '/log-item':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                item_data = json.loads(post_data.decode('utf-8'))
                item_id = str(item_data.get('id', ''))
                
                rows = []
                updated = False
                header = [
                    'ID', 'Name', 'Description', 'HSN', 'Quantity', 'Purchase Price', 'List Price', 'Discount (%)', 'Selling Price', 'Image (Base64)'
                ]
                
                # Check if it exists and update it
                if os.path.exists(ITEM_MASTER_CSV):
                    with open(ITEM_MASTER_CSV, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        header = reader.fieldnames or header
                        for row in reader:
                            if str(row.get('ID')) == item_id:
                                # Overwrite this row
                                rows.append({
                                    'ID': item_id,
                                    'Name': item_data.get('name', ''),
                                    'Description': item_data.get('description', ''),
                                    'HSN': item_data.get('hsn', ''),
                                    'Quantity': item_data.get('quantity', ''),
                                    'Purchase Price': item_data.get('purchasePrice', ''),
                                    'List Price': item_data.get('listPrice', ''),
                                    'Discount (%)': item_data.get('discount', ''),
                                    'Selling Price': item_data.get('sellingPrice', ''),
                                    'Image (Base64)': item_data.get('image', '')
                                })
                                updated = True
                            else:
                                rows.append(row)
                
                # If it wasn't found (or file didn't exist), append it
                if not updated:
                    rows.append({
                        'ID': item_id,
                        'Name': item_data.get('name', ''),
                        'Description': item_data.get('description', ''),
                        'HSN': item_data.get('hsn', ''),
                        'Quantity': item_data.get('quantity', ''),
                        'Purchase Price': item_data.get('purchasePrice', ''),
                        'List Price': item_data.get('listPrice', ''),
                        'Discount (%)': item_data.get('discount', ''),
                        'Selling Price': item_data.get('sellingPrice', ''),
                        'Image (Base64)': item_data.get('image', '')
                    })
                
                # Rewrite entire file to ensure updates take place
                with open(ITEM_MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    writer.writerows(rows)

                self.send_response(200)
                self.end_headers()
            except Exception as e:
                print(f"Failed to log item to CSV: {e}")
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
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
                    print(f"Serving Item Master at port {current_port}")
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