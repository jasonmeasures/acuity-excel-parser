# Acuity Invoice Parser - Cursor Build Guide

## 📋 Overview
This project parses Acuity XLS invoices and extracts line items into a standardized format. It includes a web UI for easy uploading and exporting of parsed data.

## 🏗️ Project Structure
```
acuity-invoice-parser/
├── acuity_invoice_parser.py    # Core parsing logic
├── acuity_parser_ui.py          # Flask web interface
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🚀 Quick Start in Cursor

### 1. Install Dependencies
```bash
pip install flask pandas xlrd openpyxl werkzeug
```

Or using requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Run the Web UI
```bash
python acuity_parser_ui.py
```

Then open: http://localhost:5000

### 3. Use as Python Module
```python
from acuity_invoice_parser import parse_acuity_invoice

# Parse an invoice
items = parse_acuity_invoice('path/to/invoice.xls')

# Access parsed data
for item in items:
    print(f"SKU: {item['sku']}, HTS: {item['hts']}")
```

## 📊 Field Mapping

| Output Field | Source Column | Excel Col | Conversion |
|--------------|---------------|-----------|------------|
| SKU | Numero_de_parte | T | None |
| Description | Descripcion_Ingles | X | None |
| HTS | HTS | AQ | None |
| Country of Origin | Origen | AM | 3-letter → 2-letter ISO |
| Quantity | Cantidad | U | None |
| Net Weight | Neto | AH | None |
| Gross Weight | Bruto | AI | None |
| Unit Price | Costo_unitario | Z | None |
| Value | Valor_de_partida | AC | None |
| Qty Unit | UM | V | Spanish → English |

## 🔄 Conversion Maps

### Country Codes (3-letter → 2-letter)
- MEX → MX (Mexico)
- USA → US (United States)
- CAN → CA (Canada)
- CHN → CN (China)
- And more...

### Unit Codes (Spanish → English)
- PZS → PCS (Piezas → Pieces)
- KGS → KG (Kilogramos → Kilograms)
- MTS → M (Metros → Meters)
- And more...

## 🎨 Features

### Web UI Features
- ✅ Drag & drop file upload
- ✅ Real-time parsing
- ✅ Summary statistics dashboard
- ✅ Interactive results table
- ✅ Export to JSON, CSV, or Excel
- ✅ Responsive design
- ✅ Error handling

### Parser Features
- ✅ Robust error handling
- ✅ Automatic country code conversion
- ✅ Unit conversion (Spanish → English)
- ✅ Clean numeric value parsing
- ✅ Skips invalid rows
- ✅ JSON output format
- ✅ **SKU aggregation** - Combine duplicate SKUs with summed quantities/values

## 🧪 Testing

### Test the Parser
```bash
python acuity_invoice_parser.py path/to/invoice.xls

# With aggregation (combine duplicate SKUs)
python acuity_invoice_parser.py path/to/invoice.xls --aggregate
```

### Test with Sample Data
```python
from acuity_invoice_parser import parse_acuity_invoice

# Without aggregation
items = parse_acuity_invoice('Acuity_Invoice.xls', aggregate=False)
print(f"Parsed {len(items)} items")

# With aggregation
items_agg = parse_acuity_invoice('Acuity_Invoice.xls', aggregate=True)
print(f"Aggregated to {len(items_agg)} unique SKUs")

# Verify first item
first = items[0]
assert 'sku' in first
assert 'hts' in first
assert first['country_of_origin'] == 'MX'  # Should be 2-letter code
assert first['qty_unit'] == 'PCS'  # Should be converted from PZS
```

## 🔄 Aggregation Feature

Combine duplicate SKUs by summing quantities, weights, and values:

```python
# Aggregation reduces line items while preserving totals
items = parse_acuity_invoice('invoice.xls', aggregate=True)

# Example: 202 line items → 119 unique SKUs
# All quantities, values, and weights are preserved
```

**What gets aggregated:**
- Quantity (summed)
- Net Weight (summed)
- Gross Weight (summed)
- Value (summed)
- Unit Price (recalculated as total_value / total_quantity)

**What gets preserved:**
- Description (from first occurrence)
- HTS code (from first occurrence)
- Country of Origin (from first occurrence)
- Quantity Unit (from first occurrence)

See `AGGREGATION_GUIDE.md` for complete documentation.

## 🔌 API Integration

### REST API Endpoints

#### Parse Invoice
```http
POST /parse
Content-Type: multipart/form-data

file: <acuity_invoice.xls>
```

Response:
```json
{
  "items": [
    {
      "line_number": 1,
      "sku": "*184PF8",
      "description": "WVR PDT 16 WH-OCCUPATION...",
      "hts": "8536.50.7000",
      "country_of_origin": "MX",
      "quantity": 1.0,
      "qty_unit": "PCS",
      "net_weight": 0.3057,
      "gross_weight": 990.0,
      "unit_price": 81.83,
      "value": 81.83
    }
  ],
  "count": 202
}
```

#### Export to CSV
```http
POST /export/csv
Content-Type: application/json

{
  "items": [...]
}
```

#### Export to Excel
```http
POST /export/excel
Content-Type: application/json

{
  "items": [...]
}
```

## 🐛 Common Issues & Solutions

### Issue: "No module named 'xlrd'"
**Solution:**
```bash
pip install xlrd
```

### Issue: "Unsupported format"
**Solution:** Ensure the file is .xls format (not .xlsx). Acuity exports use the older XLS format.

### Issue: "Column not found"
**Solution:** Check that the invoice structure matches the expected format. Column indices are 0-based.

### Issue: Country code not converting
**Solution:** Add the country code to `COUNTRY_CODE_MAP` in the parser.

## 🔧 Customization

### Add More Country Codes
Edit `acuity_invoice_parser.py`:
```python
COUNTRY_CODE_MAP = {
    'MEX': 'MX',
    'YOUR_CODE': 'XX',  # Add here
    # ...
}
```

### Add More Unit Conversions
Edit `acuity_invoice_parser.py`:
```python
UNIT_CONVERSION_MAP = {
    'PZS': 'PCS',
    'YOUR_UNIT': 'TARGET',  # Add here
    # ...
}
```

### Change Port
Edit `acuity_parser_ui.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)  # Change port
```

## 📦 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 acuity_parser_ui:app
```

### Using Docker
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY acuity_invoice_parser.py .
COPY acuity_parser_ui.py .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "acuity_parser_ui:app"]
```

### Environment Variables
```bash
FLASK_ENV=production
FLASK_DEBUG=false
MAX_CONTENT_LENGTH=16777216  # 16MB
```

## 📝 Requirements File
```txt
flask>=3.0.0
pandas>=2.0.0
xlrd>=2.0.1
openpyxl>=3.1.0
werkzeug>=3.0.0
```

## 🎯 Use Cases

1. **Manual Upload**: Use web UI for one-off invoice processing
2. **Batch Processing**: Use Python module to process multiple files
3. **API Integration**: Integrate with existing systems via REST API
4. **Data Pipeline**: Incorporate into ETL workflows
5. **Customs Automation**: Feed parsed data into customs systems

## 🔒 Security Considerations

- File size limited to 16MB
- Only .xls files accepted
- Files are deleted after processing
- No persistent storage of uploaded files
- Input validation on all fields
- SQL injection not applicable (no database)

## 📊 Performance

- Average parsing time: <1 second for typical invoice
- Memory usage: ~50MB for 200-line invoice
- Concurrent requests: 4 workers recommended
- Max file size: 16MB (configurable)

## 🤝 Integration with Other Systems

### KlearNow Integration
```python
# Example: Send to KlearNow API
import requests

items = parse_acuity_invoice('invoice.xls')

response = requests.post(
    'https://api.klearnow.com/v1/invoices',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={'line_items': items}
)
```

### Database Storage
```python
import sqlite3

items = parse_acuity_invoice('invoice.xls')

conn = sqlite3.connect('invoices.db')
cursor = conn.cursor()

for item in items:
    cursor.execute('''
        INSERT INTO line_items 
        (sku, description, hts, country, quantity, value)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        item['sku'], 
        item['description'],
        item['hts'],
        item['country_of_origin'],
        item['quantity'],
        item['value']
    ))

conn.commit()
```

## 🎓 Learning Resources

- Flask Documentation: https://flask.palletsprojects.com/
- Pandas Documentation: https://pandas.pydata.org/docs/
- Customs Automation: Contact KlearNow team

## 📞 Support

For issues or questions:
1. Check this README
2. Review error messages carefully
3. Contact development team
4. File a bug report with sample data (redacted)

---

**Built with ❤️ for KlearNow Customs Automation**
