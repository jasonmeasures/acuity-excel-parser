"""
Acuity Invoice Parser
Extracts line items from Acuity XLS invoices and converts to standardized format
"""

import pandas as pd
import sys
from typing import Dict, List, Optional
import json


# Country code conversion mapping (Spanish 3-letter to ISO 2-letter)
COUNTRY_CODE_MAP = {
    'MEX': 'MX',  # Mexico
    'USA': 'US',  # United States
    'CAN': 'CA',  # Canada
    'CHN': 'CN',  # China
    'JPN': 'JP',  # Japan
    'DEU': 'DE',  # Germany
    'GBR': 'GB',  # United Kingdom
    'FRA': 'FR',  # France
    'ITA': 'IT',  # Italy
    'ESP': 'ES',  # Spain
    'BRA': 'BR',  # Brazil
    'IND': 'IN',  # India
    'KOR': 'KR',  # South Korea
    'TWN': 'TW',  # Taiwan
    'THA': 'TH',  # Thailand
    'VNM': 'VN',  # Vietnam
    'MYS': 'MY',  # Malaysia
    'SGP': 'SG',  # Singapore
    'IDN': 'ID',  # Indonesia
    'PHL': 'PH',  # Philippines
}

# Unit conversion mapping (Spanish to English)
UNIT_CONVERSION_MAP = {
    'PZS': 'PCS',   # Piezas to Pieces
    'PZA': 'PCS',   # Pieza to Pieces
    'KGS': 'KG',    # Kilogramos to Kilograms
    'KGM': 'KG',    # Kilogramo to Kilograms
    'LBS': 'LB',    # Libras to Pounds
    'MTS': 'M',     # Metros to Meters
    'MTR': 'M',     # Metro to Meters
    'LTS': 'L',     # Litros to Liters
    'LTR': 'L',     # Litro to Liters
    'UNI': 'EA',    # Unidad to Each
    'CAJ': 'CS',    # Cajas to Cases
    'PAR': 'PR',    # Pares to Pairs
}


def convert_country_code(country_code: str) -> str:
    """Convert 3-letter country code to 2-letter ISO code"""
    if not country_code or pd.isna(country_code):
        return ''
    
    code = str(country_code).strip().upper()
    
    # If already 2 letters, return as-is
    if len(code) == 2:
        return code
    
    # Otherwise, look up in mapping
    return COUNTRY_CODE_MAP.get(code, code)


def convert_unit(unit: str) -> str:
    """Convert Spanish unit to English equivalent"""
    if not unit or pd.isna(unit):
        return ''
    
    unit_upper = str(unit).strip().upper()
    return UNIT_CONVERSION_MAP.get(unit_upper, unit_upper)


def clean_value(value) -> Optional[float]:
    """Clean and convert numeric values"""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def aggregate_by_sku(line_items: List[Dict]) -> List[Dict]:
    """
    Aggregate line items by SKU, summing quantities, weights, and values.
    
    Args:
        line_items: List of parsed line items
        
    Returns:
        List of aggregated line items grouped by SKU
    """
    if not line_items:
        return []
    
    # Convert to DataFrame for easier aggregation
    df = pd.DataFrame(line_items)
    
    # Define aggregation rules
    agg_dict = {
        'quantity': 'sum',
        'net_weight': 'sum',
        'gross_weight': 'sum',
        'value': 'sum',
    }

    # Keep first occurrence of non-numeric columns
    non_numeric_cols = ['description', 'hts', 'country_of_origin', 'qty_unit',
                        'no_of_package', 'package_type', 'container_number',
                        'po_number', 'po_reference']
    for col in non_numeric_cols:
        if col in df.columns:
            agg_dict[col] = 'first'

    # Group by SKU and aggregate
    aggregated = df.groupby('sku', as_index=False).agg(agg_dict)

    # Recalculate unit price based on aggregated values
    mask = aggregated['quantity'] > 0
    aggregated.loc[mask, 'unit_price'] = aggregated.loc[mask, 'value'] / aggregated.loc[mask, 'quantity']

    # Reorder columns to match Invoice Tab template
    correct_column_order = [
        'sku', 'description', 'hts', 'country_of_origin', 'no_of_package',
        'quantity', 'net_weight', 'gross_weight', 'unit_price', 'value',
        'qty_unit', 'package_type', 'container_number', 'po_number', 'po_reference'
    ]
    existing_columns = [col for col in correct_column_order if col in aggregated.columns]
    aggregated = aggregated[existing_columns]

    return aggregated.to_dict('records')


def parse_acuity_invoice(file_path: str, aggregate: bool = False) -> List[Dict]:
    """
    Parse Acuity invoice XLS file and extract line items
    
    Args:
        file_path: Path to the Acuity invoice XLS file
        aggregate: If True, aggregate line items by SKU
        
    Returns:
        List of dictionaries containing parsed line items
    """
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Column mapping (0-indexed)
        column_mapping = {
            'sku': 19,              # T: Numero_de_parte
            'description': 23,      # X: Descripcion_Ingles
            'hts': 42,              # AQ: HTS
            'country_of_origin': 38, # AM: Origen
            'quantity': 20,         # U: Cantidad
            'net_weight': 33,       # AH: Neto
            'gross_weight': 34,     # AI: Bruto
            'unit_price': 25,       # Z: Costo_unitario
            'value': 28,            # AC: Valor_de_partida
            'qty_unit': 21,         # V: UM
        }
        
        # Extract line items
        line_items = []
        
        for idx, row in df.iterrows():
            # Skip rows without SKU
            sku = row.iloc[column_mapping['sku']]
            if pd.isna(sku) or str(sku).strip() == '':
                continue
            
            # Extract and convert data (ordered per Invoice Tab template)
            line_item = {
                'sku': str(sku).strip(),
                'description': str(row.iloc[column_mapping['description']]).strip() if not pd.isna(row.iloc[column_mapping['description']]) else '',
                'hts': str(row.iloc[column_mapping['hts']]).strip() if not pd.isna(row.iloc[column_mapping['hts']]) else '',
                'country_of_origin': convert_country_code(row.iloc[column_mapping['country_of_origin']]),
                'no_of_package': '',
                'quantity': clean_value(row.iloc[column_mapping['quantity']]),
                'net_weight': clean_value(row.iloc[column_mapping['net_weight']]),
                'gross_weight': clean_value(row.iloc[column_mapping['gross_weight']]),
                'unit_price': clean_value(row.iloc[column_mapping['unit_price']]),
                'value': clean_value(row.iloc[column_mapping['value']]),
                'qty_unit': convert_unit(row.iloc[column_mapping['qty_unit']]),
                'package_type': '',
                'container_number': '',
                'po_number': '',
                'po_reference': '',
            }
            
            line_items.append(line_item)
        
        # Aggregate by SKU if requested
        if aggregate:
            line_items = aggregate_by_sku(line_items)
        
        return line_items
        
    except Exception as e:
        print(f"Error parsing invoice: {str(e)}", file=sys.stderr)
        raise


def main():
    """Main entry point for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python acuity_invoice_parser.py <path_to_invoice.xls> [--aggregate]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    aggregate = '--aggregate' in sys.argv
    
    try:
        line_items = parse_acuity_invoice(file_path, aggregate=aggregate)
        
        # Output as JSON
        print(json.dumps(line_items, indent=2))
        
        agg_msg = " (aggregated by SKU)" if aggregate else ""
        print(f"\n✓ Successfully parsed {len(line_items)} line items{agg_msg}", file=sys.stderr)
        
    except Exception as e:
        print(f"✗ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
