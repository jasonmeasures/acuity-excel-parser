"""
Acuity Invoice Parser - Flask Web UI
Simple web interface for uploading and parsing Acuity invoices
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import os
import json
from werkzeug.utils import secure_filename
import pandas as pd
from acuity_invoice_parser import parse_acuity_invoice
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/acuity_uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acuity Invoice Parser</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .content { padding: 30px; }
        .upload-section {
            border: 3px dashed #667eea;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            background: #f8f9ff;
            margin-bottom: 30px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-section:hover { background: #f0f2ff; border-color: #764ba2; }
        .upload-section.dragover { background: #e8ebff; border-color: #667eea; transform: scale(1.02); }
        .file-input { display: none; }
        .upload-icon { font-size: 48px; margin-bottom: 15px; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
            display: inline-block;
            text-decoration: none;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .results { display: none; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card .value { font-size: 32px; font-weight: bold; margin-bottom: 5px; }
        .stat-card .label { font-size: 14px; opacity: 0.9; }
        .table-container {
            overflow-x: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-top: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
            position: sticky;
            top: 0;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #f0f0f0;
        }
        tr:hover { background: #f9f9f9; }
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            background: #fee;
            border: 1px solid #fcc;
            color: #c00;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
        }
        .success {
            background: #efe;
            border: 1px solid #cfc;
            color: #060;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 Acuity Invoice Parser</h1>
            <p>Upload Acuity XLS invoices to extract and convert line items</p>
        </div>
        
        <div class="content">
            <div class="error" id="error"></div>
            
            <div class="upload-section" id="uploadSection">
                <div class="upload-icon">📄</div>
                <h3>Drop your Acuity invoice here or click to browse</h3>
                <p style="margin-top: 10px; color: #666;">Supported formats: .xls, .xlsx</p>
                <input type="file" id="fileInput" class="file-input" accept=".xls,.xlsx">
                <div style="margin-top: 20px;">
                    <label style="display: flex; align-items: center; justify-content: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" id="noAggregateCheckbox" style="width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-size: 14px; font-weight: 600;">Keep all line items (no aggregation)</span>
                    </label>
                    <p style="margin-top: 5px; color: #666; font-size: 12px;">Uncheck to aggregate duplicate SKUs by default</p>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Parsing invoice...</p>
            </div>
            
            <div class="results" id="results">
                <div class="success">
                    ✓ Successfully parsed <strong id="itemCount">0</strong> line items
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="value" id="totalItems">0</div>
                        <div class="label">Total Items</div>
                    </div>
                    <div class="stat-card">
                        <div class="value" id="totalQuantity">0</div>
                        <div class="label">Total Quantity</div>
                    </div>
                    <div class="stat-card">
                        <div class="value" id="totalValue">$0</div>
                        <div class="label">Total Value</div>
                    </div>
                    <div class="stat-card">
                        <div class="value" id="totalWeight">0</div>
                        <div class="label">Total Weight (kg)</div>
                    </div>
                </div>
                
                <div class="action-buttons">
                    <button class="btn" onclick="downloadJSON()">Download JSON</button>
                    <button class="btn" onclick="downloadCSV()">Download CSV</button>
                    <button class="btn" onclick="downloadExcel()">Download Excel</button>
                    <button class="btn" onclick="location.reload()">Parse Another</button>
                </div>
                
                <div class="table-container">
                    <table id="resultsTable">
                        <thead>
                            <tr>
                                <th>SKU</th>
                                <th>Description</th>
                                <th>HTS</th>
                                <th>Country of Origin</th>
                                <th>No. of Package</th>
                                <th>Quantity</th>
                                <th>Net Weight</th>
                                <th>Gross Weight</th>
                                <th>Unit Price</th>
                                <th>Value</th>
                                <th>Qty Unit</th>
                                <th>Package Type</th>
                                <th>Container Number</th>
                                <th>PO Number</th>
                                <th>PO Reference</th>
                            </tr>
                        </thead>
                        <tbody id="resultsBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let parsedData = [];
        
        const uploadSection = document.getElementById('uploadSection');
        const fileInput = document.getElementById('fileInput');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const errorDiv = document.getElementById('error');
        
        uploadSection.addEventListener('click', () => fileInput.click());
        
        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadSection.classList.add('dragover');
        });
        
        uploadSection.addEventListener('dragleave', () => {
            uploadSection.classList.remove('dragover');
        });
        
        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleFile(e.dataTransfer.files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleFile(e.target.files[0]);
            }
        });
        
        async function handleFile(file) {
            if (!file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
                showError('Please upload a .xls or .xlsx file');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            // Aggregate by default unless "no aggregation" is checked
            const noAggregateCheckbox = document.getElementById('noAggregateCheckbox');
            if (!noAggregateCheckbox || !noAggregateCheckbox.checked) {
                formData.append('aggregate', 'true');
            }
            
            uploadSection.style.display = 'none';
            loading.style.display = 'block';
            errorDiv.style.display = 'none';
            
            try {
                const response = await fetch('/parse', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Upload failed');
                }
                
                parsedData = data.items;
                displayResults(data.items);
                
            } catch (error) {
                showError(error.message);
                uploadSection.style.display = 'block';
            } finally {
                loading.style.display = 'none';
            }
        }
        
        function displayResults(items) {
            const totalQty = items.reduce((sum, item) => sum + (item.quantity || 0), 0);
            const totalVal = items.reduce((sum, item) => sum + (item.value || 0), 0);
            const totalWt = items.reduce((sum, item) => sum + (item.net_weight || 0), 0);
            
            document.getElementById('itemCount').textContent = items.length;
            document.getElementById('totalItems').textContent = items.length;
            document.getElementById('totalQuantity').textContent = totalQty.toFixed(0);
            document.getElementById('totalValue').textContent = '$' + totalVal.toFixed(2);
            document.getElementById('totalWeight').textContent = totalWt.toFixed(2);
            
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = items.map(item => `
                <tr>
                    <td>${item.sku}</td>
                    <td>${item.description}</td>
                    <td>${item.hts}</td>
                    <td>${item.country_of_origin}</td>
                    <td>${item.no_of_package || ''}</td>
                    <td>${item.quantity?.toFixed(0) || ''}</td>
                    <td>${item.net_weight?.toFixed(2) || ''}</td>
                    <td>${item.gross_weight?.toFixed(2) || ''}</td>
                    <td>$${item.unit_price?.toFixed(2) || ''}</td>
                    <td>$${item.value?.toFixed(2) || ''}</td>
                    <td>${item.qty_unit}</td>
                    <td>${item.package_type || ''}</td>
                    <td>${item.container_number || ''}</td>
                    <td>${item.po_number || ''}</td>
                    <td>${item.po_reference || ''}</td>
                </tr>
            `).join('');
            
            results.style.display = 'block';
        }
        
        function showError(message) {
            errorDiv.textContent = '✗ Error: ' + message;
            errorDiv.style.display = 'block';
        }
        
        function downloadJSON() {
            const blob = new Blob([JSON.stringify(parsedData, null, 2)], { type: 'application/json' });
            downloadBlob(blob, 'acuity_invoice.json');
        }
        
        async function downloadCSV() {
            const response = await fetch('/export/csv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: parsedData })
            });
            const blob = await response.blob();
            downloadBlob(blob, 'acuity_invoice.csv');
        }
        
        async function downloadExcel() {
            const response = await fetch('/export/excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: parsedData })
            });
            const blob = await response.blob();
            downloadBlob(blob, 'acuity_invoice.xlsx');
        }
        
        function downloadBlob(blob, filename) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/parse', methods=['POST'])
def parse_invoice():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith(('.xls', '.xlsx')):
            return jsonify({'error': 'Only .xls and .xlsx files are supported'}), 400
        
        # Check if aggregation is requested
        aggregate = request.form.get('aggregate', '').lower() == 'true'
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse the invoice
        items = parse_acuity_invoice(filepath, aggregate=aggregate)
        
        # Clean up temp file
        os.remove(filepath)
        
        return jsonify({
            'items': items, 
            'count': len(items),
            'aggregated': aggregate
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Column order and display names matching Invoice Tab template
EXPORT_COLUMN_ORDER = [
    'sku', 'description', 'hts', 'country_of_origin', 'no_of_package',
    'quantity', 'net_weight', 'gross_weight', 'unit_price', 'value',
    'qty_unit', 'package_type', 'container_number', 'po_number', 'po_reference'
]
EXPORT_COLUMN_NAMES = {
    'sku': 'SKU', 'description': 'DESCRIPTION', 'hts': 'HTS',
    'country_of_origin': 'COUNTRY OF ORIGIN', 'no_of_package': 'NO. OF PACKAGE',
    'quantity': 'QUANTITY', 'net_weight': 'NET WEIGHT', 'gross_weight': 'GROSS WEIGHT',
    'unit_price': 'UNIT PRICE', 'value': 'VALUE', 'qty_unit': 'QTY UNIT',
    'package_type': 'PACKAGE TYPE', 'container_number': 'CONTAINER NUMBER',
    'po_number': 'PO NUMBER', 'po_reference': 'PO REFERENCE'
}


def _prepare_export_df(items):
    """Prepare a DataFrame with correct column order and names for export."""
    df = pd.DataFrame(items)
    cols = [c for c in EXPORT_COLUMN_ORDER if c in df.columns]
    df = df[cols]
    df = df.rename(columns=EXPORT_COLUMN_NAMES)
    return df


@app.route('/export/csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        items = data.get('items', [])

        df = _prepare_export_df(items)

        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='acuity_invoice.csv'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/export/excel', methods=['POST'])
def export_excel():
    try:
        data = request.json
        items = data.get('items', [])

        df = _prepare_export_df(items)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='invoice')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='acuity_invoice.xlsx'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4000)
