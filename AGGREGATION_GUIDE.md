# Acuity Parser - Aggregation Feature

## 📊 Overview

The aggregation feature combines duplicate SKUs by summing quantities, weights, and values while preserving key product information. This is useful when you need consolidated line items grouped by unique SKUs.

## ✅ Validation Results

**Test with your Acuity invoice:**
- **Original:** 202 line items
- **Aggregated:** 119 unique SKUs
- **Totals match:** ✓ Quantities, values, and weights all preserved
- **Example:** SKU *233C8U appeared 7 times, now consolidated into 1 line

## 🎯 How It Works

### Aggregation Rules

**Summed Fields:**
- `QUANTITY` - Total quantity across all occurrences
- `NET WEIGHT` - Total net weight (kg)
- `GROSS WEIGHT` - Total gross weight (kg)  
- `VALUE` - Total value (USD)

**Preserved Fields (first occurrence):**
- `DESCRIPTION` - Product description
- `HTS` - Harmonized Tariff Schedule code
- `COUNTRY OF ORIGIN` - 2-letter ISO country code
- `QTY UNIT` - Quantity unit (PCS, KG, etc.)

**Recalculated Fields:**
- `UNIT PRICE` = Total Value ÷ Total Quantity

## 💻 Usage Examples

### Command Line
```bash
# Without aggregation (default)
python acuity_invoice_parser.py invoice.xls

# With aggregation
python acuity_invoice_parser.py invoice.xls --aggregate
```

### Python Module
```python
from acuity_invoice_parser import parse_acuity_invoice

# Without aggregation
items = parse_acuity_invoice('invoice.xls', aggregate=False)

# With aggregation
items = parse_acuity_invoice('invoice.xls', aggregate=True)
```

### Web UI
1. Upload your invoice
2. **Check the "Aggregate by SKU" checkbox**
3. Submit to get consolidated results

### Agent (Iqo Layer)
```python
from acuity_invoice_agent import AcuityInvoiceAgent

agent = AcuityInvoiceAgent()

# With aggregation
result = agent.parse_file('invoice.xls', aggregate=True)

print(f"Reduced from {result['summary']['total_items']} items")
```

### Async Agent
```python
import asyncio
from acuity_invoice_agent import AcuityParserIqoAgent

async def main():
    agent = AcuityParserIqoAgent()
    result = await agent.execute('parse_invoice', {
        'file_path': 'invoice.xls',
        'aggregate': True
    })
    print(result)

asyncio.run(main())
```

## 📋 Example Output Comparison

### Before Aggregation (7 entries for SKU *233C8U)
```json
[
  {"sku": "*233C8U", "quantity": 25, "value": 333.97},
  {"sku": "*233C8U", "quantity": 25, "value": 333.97},
  {"sku": "*233C8U", "quantity": 25, "value": 333.97},
  {"sku": "*233C8U", "quantity": 25, "value": 333.97},
  {"sku": "*233C8U", "quantity": 25, "value": 333.97},
  {"sku": "*233C8U", "quantity": 25, "value": 333.97},
  {"sku": "*233C8U", "quantity": 25, "value": 333.97}
]
```

### After Aggregation (1 entry)
```json
[
  {
    "sku": "*233C8U",
    "quantity": 175.0,
    "value": 2337.79,
    "unit_price": 13.36,
    "net_weight": 53.58,
    "gross_weight": 56.0
  }
]
```

## 🎨 Web UI Changes

New checkbox added to upload section:
- **Label:** "Aggregate by SKU"
- **Description:** "Combine duplicate SKUs and sum quantities/values"
- **Default:** Unchecked (preserves original behavior)

## 🔄 REST API

### Parse Endpoint
```http
POST /parse
Content-Type: multipart/form-data

file: <invoice.xls>
aggregate: true
```

Response includes aggregation flag:
```json
{
  "items": [...],
  "count": 119,
  "aggregated": true
}
```

## ⚠️ Important Notes

1. **Unit Price Recalculation:** When aggregating, unit prices are recalculated as `total_value / total_quantity`. This ensures accuracy when combining items with different unit prices.

2. **Data Preservation:** First occurrence of non-numeric fields (description, HTS, country, unit) is kept. All occurrences should have the same values for these fields.

3. **Validation:** All totals (quantity, value, weight) are preserved during aggregation. The system validates this automatically.

4. **Line Numbers:** Line numbers are renumbered sequentially after aggregation (1 to N where N = unique SKUs).

## 🧪 Testing Aggregation

```python
from acuity_invoice_agent import AcuityInvoiceAgent

agent = AcuityInvoiceAgent()

# Parse without aggregation
result_original = agent.parse_file('invoice.xls', aggregate=False)

# Parse with aggregation  
result_aggregated = agent.parse_file('invoice.xls', aggregate=True)

# Validate totals match
assert result_original['summary']['total_quantity'] == \
       result_aggregated['summary']['total_quantity']
       
assert result_original['summary']['total_value'] == \
       result_aggregated['summary']['total_value']

print(f"✓ Reduced from {len(result_original['items'])} to {len(result_aggregated['items'])} items")
```

## 🎯 Use Cases

1. **Customs Documentation:** Consolidated view for customs entries
2. **Summary Reports:** Executive summaries with unique products
3. **Data Analysis:** Cleaner datasets for analytics
4. **Invoice Reconciliation:** Compare against purchase orders
5. **Inventory Management:** Track unique products vs. line items

## 📊 Performance

- **Speed:** Aggregation adds minimal overhead (<10ms typical)
- **Memory:** Uses pandas groupby (efficient for datasets up to 100K rows)
- **Accuracy:** Maintains floating-point precision for all calculations

---

**Built with validation on real Acuity invoice data**
