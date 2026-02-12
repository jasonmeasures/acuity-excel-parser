# Acuity Invoice Parser - Quick Start

## ✅ Test Results

Successfully parsed your Acuity invoice:
- **202 line items** extracted
- **119 unique SKUs**
- **26 unique HTS codes**
- **Total value:** $160,486.04
- **Total weight:** 13,460.71 kg

All conversions validated:
- ✅ Country codes: MEX → MX
- ✅ Units: PZS → PCS
- ✅ All required fields extracted correctly
- ✅ **Aggregation tested:** 202 items → 119 SKUs (totals preserved)

## 📦 Package Contents

1. **acuity_invoice_parser.py** - Core parsing logic (standalone)
2. **acuity_parser_ui.py** - Flask web UI with drag & drop
3. **acuity_invoice_agent.py** - Agent version for Iqo layer integration
4. **ACUITY_PARSER_README.md** - Complete documentation
5. **requirements.txt** - Python dependencies

## 🚀 Quick Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Web UI
```bash
python acuity_parser_ui.py
# Open http://localhost:5000
# Upload invoice and optionally check "Aggregate by SKU"
```

### Use as Python Module
```python
from acuity_invoice_parser import parse_acuity_invoice

# Without aggregation (default)
items = parse_acuity_invoice('Acuity_Invoice.xls')
print(f"Parsed {len(items)} items")

# With aggregation (combine duplicate SKUs)
items = parse_acuity_invoice('Acuity_Invoice.xls', aggregate=True)
print(f"Aggregated to {len(items)} unique SKUs")
```

### Use Command Line
```bash
# Parse normally
python acuity_invoice_parser.py invoice.xls

# Parse with aggregation
python acuity_invoice_parser.py invoice.xls --aggregate
```

### Use Agent (Iqo Layer)
```python
import asyncio
from acuity_invoice_agent import AcuityParserIqoAgent

async def main():
    agent = AcuityParserIqoAgent()
    result = await agent.execute('parse_invoice', {
        'file_path': 'invoice.xls'
    })
    print(result)

asyncio.run(main())
```

## 🎯 Cursor Development

1. **Create new project:**
   ```bash
   mkdir acuity-parser && cd acuity-parser
   ```

2. **Copy all files to project directory**

3. **In Cursor:**
   - Open the project folder
   - Install dependencies: `pip install -r requirements.txt`
   - Run the UI: `python acuity_parser_ui.py`
   - Edit and customize as needed

4. **Key files to customize:**
   - `COUNTRY_CODE_MAP` - Add more country codes
   - `UNIT_CONVERSION_MAP` - Add more unit conversions
   - `COLUMN_MAP` - If invoice format changes
   - UI styling in `acuity_parser_ui.py` HTML_TEMPLATE

## 📊 Field Mapping Reference

| Field | Source Column | Excel | Notes |
|-------|---------------|-------|-------|
| SKU | Numero_de_parte | T | Required |
| Description | Descripcion_Ingles | X | Required |
| HTS | HTS | AQ | ⚠️ Was AO in specs, actually AQ |
| Country | Origen | AM | Converts MEX→MX |
| Quantity | Cantidad | U | Numeric |
| Net Weight | Neto | AH | kg |
| Gross Weight | Bruto | AI | kg |
| Unit Price | Costo_unitario | Z | USD |
| Value | Valor_de_partida | AC | USD |
| Qty Unit | UM | V | Converts PZS→PCS |

## 🔌 Integration Examples

### REST API (Flask UI)
```bash
curl -X POST http://localhost:5000/parse \
  -F "file=@Acuity_Invoice.xls" \
  -F "aggregate=true"
```

### Python Script
```python
from acuity_invoice_parser import parse_acuity_invoice
import json

result = parse_acuity_invoice('invoice.xls', aggregate=True)
with open('output.json', 'w') as f:
    json.dump(result, f, indent=2)
```

### Async Agent
```python
from acuity_invoice_agent import AcuityInvoiceAgent
import asyncio

async def process():
    agent = AcuityInvoiceAgent()
    result = await agent.parse_file_async('invoice.xls', aggregate=True)
    agent.export_excel(result, 'output.xlsx')

asyncio.run(process())
```

## 🔄 Aggregation Feature

**NEW: Combine duplicate SKUs automatically**

Aggregation reduces 202 line items to 119 unique SKUs while preserving all totals:
- ✅ Quantities summed
- ✅ Values summed  
- ✅ Weights summed
- ✅ Unit prices recalculated
- ✅ All totals validated and match

**Usage:**
- **Web UI:** Check the "Aggregate by SKU" checkbox
- **Command Line:** Add `--aggregate` flag
- **Python:** Pass `aggregate=True` parameter
- **Agent:** Include `'aggregate': True` in params

See `AGGREGATION_GUIDE.md` for full documentation.

## 🐛 Troubleshooting

### "No module named 'xlrd'"
```bash
pip install xlrd --break-system-packages
```

### "Column not found"
The HTS column is at **AQ (index 42)**, not AO. This has been corrected in the code.

### Wrong country codes
Add them to `COUNTRY_CODE_MAP` in the parser file.

### Wrong unit conversions
Add them to `UNIT_CONVERSION_MAP` in the parser file.

## 📞 Support

Check ACUITY_PARSER_README.md for comprehensive documentation.

---

**Ready to use in Cursor or deploy to production!**
