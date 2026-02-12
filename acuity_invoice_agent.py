"""
Acuity Invoice Parser Agent
Agent-ready module for integration with Iqo layer
Provides both synchronous and async interfaces
"""

import asyncio
from typing import Dict, List, Optional, Union
import pandas as pd
from pathlib import Path
import json
from datetime import datetime


class AcuityInvoiceAgent:
    """
    Agent for parsing Acuity invoices
    Designed for integration with Iqo layer automation
    """
    
    # Country code conversion mapping
    COUNTRY_CODES = {
        'MEX': 'MX', 'USA': 'US', 'CAN': 'CA', 'CHN': 'CN', 'JPN': 'JP',
        'DEU': 'DE', 'GBR': 'GB', 'FRA': 'FR', 'ITA': 'IT', 'ESP': 'ES',
        'BRA': 'BR', 'IND': 'IN', 'KOR': 'KR', 'TWN': 'TW', 'THA': 'TH',
        'VNM': 'VN', 'MYS': 'MY', 'SGP': 'SG', 'IDN': 'ID', 'PHL': 'PH',
    }
    
    # Unit conversion mapping
    UNIT_CODES = {
        'PZS': 'PCS', 'PZA': 'PCS', 'KGS': 'KG', 'KGM': 'KG',
        'LBS': 'LB', 'MTS': 'M', 'MTR': 'M', 'LTS': 'L',
        'LTR': 'L', 'UNI': 'EA', 'CAJ': 'CS', 'PAR': 'PR',
    }
    
    # Column indices mapping
    COLUMN_MAP = {
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
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the agent
        
        Args:
            config: Optional configuration dictionary
                - validate: bool - Enable validation (default: True)
                - log_level: str - Logging level (default: 'INFO')
                - max_items: int - Max line items to process (default: None/unlimited)
        """
        self.config = config or {}
        self.validate = self.config.get('validate', True)
        self.max_items = self.config.get('max_items', None)
        self.metadata = {}
    
    def convert_country_code(self, code: str) -> str:
        """Convert 3-letter to 2-letter ISO country code"""
        if not code or pd.isna(code):
            return ''
        code = str(code).strip().upper()
        return self.COUNTRY_CODES.get(code, code) if len(code) != 2 else code
    
    def convert_unit(self, unit: str) -> str:
        """Convert Spanish unit to English"""
        if not unit or pd.isna(unit):
            return ''
        unit = str(unit).strip().upper()
        return self.UNIT_CODES.get(unit, unit)
    
    def aggregate_by_sku(self, line_items: List[Dict]) -> List[Dict]:
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
        non_numeric_cols = ['description', 'hts', 'country_of_origin', 'qty_unit']
        for col in non_numeric_cols:
            if col in df.columns:
                agg_dict[col] = 'first'
        
        # Group by SKU and aggregate
        aggregated = df.groupby('sku', as_index=False).agg(agg_dict)
        
        # Recalculate unit price based on aggregated values
        # Unit price = total value / total quantity
        mask = aggregated['quantity'] > 0
        aggregated.loc[mask, 'unit_price'] = aggregated.loc[mask, 'value'] / aggregated.loc[mask, 'quantity']
        
        # Renumber lines
        aggregated['line_number'] = range(1, len(aggregated) + 1)
        
        # Convert back to list of dictionaries
        return aggregated.to_dict('records')
    
    def clean_numeric(self, value) -> Optional[float]:
        """Clean and convert numeric values"""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def extract_metadata(self, df: pd.DataFrame) -> Dict:
        """Extract invoice-level metadata"""
        if len(df) == 0:
            return {}
        
        # Assuming first row contains header info
        first_row = df.iloc[0]
        
        metadata = {}
        
        # Map known header columns
        header_cols = {
            'invoice_number': 1,    # B: Factura
            'pedimento': 0,          # A: Pedimento
            'cove': 2,               # C: COVE
            'date': 3,               # D: Fecha
            'vendor': 7,             # H: Nombre
            'incoterm': 14,          # O: Incoterm
            'currency': 15,          # P: Moneda
            'total_value': 16,       # Q: Dolares
        }
        
        for key, idx in header_cols.items():
            if idx < len(first_row):
                val = first_row.iloc[idx]
                if not pd.isna(val):
                    metadata[key] = str(val) if not isinstance(val, (int, float)) else val
        
        return metadata
    
    def parse_file(self, file_path: Union[str, Path], aggregate: bool = False) -> Dict:
        """
        Parse Acuity invoice file (synchronous)
        
        Args:
            file_path: Path to XLS file
            aggregate: If True, aggregate line items by SKU
            
        Returns:
            Dict with 'items', 'metadata', 'summary', 'errors'
        """
        try:
            # Read Excel file
            df = pd.read_excel(str(file_path))
            
            # Extract metadata
            self.metadata = self.extract_metadata(df)
            
            # Parse line items
            line_items = []
            errors = []
            
            for idx, row in df.iterrows():
                # Check max items limit
                if self.max_items and len(line_items) >= self.max_items:
                    break
                
                # Skip rows without SKU
                sku = row.iloc[self.COLUMN_MAP['sku']]
                if pd.isna(sku) or str(sku).strip() == '':
                    continue
                
                try:
                    # Extract and convert data
                    item = {
                        'line_number': idx + 1,
                        'sku': str(sku).strip(),
                        'description': str(row.iloc[self.COLUMN_MAP['description']]).strip() 
                            if not pd.isna(row.iloc[self.COLUMN_MAP['description']]) else '',
                        'hts': str(row.iloc[self.COLUMN_MAP['hts']]).strip() 
                            if not pd.isna(row.iloc[self.COLUMN_MAP['hts']]) else '',
                        'country_of_origin': self.convert_country_code(
                            row.iloc[self.COLUMN_MAP['country_of_origin']]
                        ),
                        'quantity': self.clean_numeric(row.iloc[self.COLUMN_MAP['quantity']]),
                        'qty_unit': self.convert_unit(row.iloc[self.COLUMN_MAP['qty_unit']]),
                        'net_weight': self.clean_numeric(row.iloc[self.COLUMN_MAP['net_weight']]),
                        'gross_weight': self.clean_numeric(row.iloc[self.COLUMN_MAP['gross_weight']]),
                        'unit_price': self.clean_numeric(row.iloc[self.COLUMN_MAP['unit_price']]),
                        'value': self.clean_numeric(row.iloc[self.COLUMN_MAP['value']]),
                    }
                    
                    # Validate if enabled
                    if self.validate:
                        validation_errors = self._validate_item(item)
                        if validation_errors:
                            errors.append({
                                'line': idx + 1,
                                'errors': validation_errors
                            })
                    
                    line_items.append(item)
                    
                except Exception as e:
                    errors.append({
                        'line': idx + 1,
                        'error': f'Parse error: {str(e)}'
                    })
            
            # Aggregate by SKU if requested
            if aggregate:
                line_items = self.aggregate_by_sku(line_items)
            
            # Generate summary
            summary = self._generate_summary(line_items)
            
            return {
                'success': True,
                'items': line_items,
                'metadata': self.metadata,
                'summary': summary,
                'errors': errors,
                'aggregated': aggregate,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def parse_file_async(self, file_path: Union[str, Path], aggregate: bool = False) -> Dict:
        """Async version of parse_file"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.parse_file(file_path, aggregate))
    
    def _validate_item(self, item: Dict) -> List[str]:
        """Validate a line item"""
        errors = []
        
        if not item.get('sku'):
            errors.append('Missing SKU')
        
        if not item.get('hts'):
            errors.append('Missing HTS code')
        
        if not item.get('country_of_origin'):
            errors.append('Missing country of origin')
        
        if item.get('quantity') is None:
            errors.append('Missing quantity')
        elif item['quantity'] <= 0:
            errors.append('Invalid quantity (must be > 0)')
        
        if item.get('value') is None:
            errors.append('Missing value')
        elif item['value'] < 0:
            errors.append('Invalid value (must be >= 0)')
        
        return errors
    
    def _generate_summary(self, items: List[Dict]) -> Dict:
        """Generate summary statistics"""
        if not items:
            return {}
        
        total_qty = sum(item.get('quantity', 0) or 0 for item in items)
        total_value = sum(item.get('value', 0) or 0 for item in items)
        total_weight = sum(item.get('net_weight', 0) or 0 for item in items)
        
        unique_skus = len(set(item['sku'] for item in items))
        unique_hts = len(set(item['hts'] for item in items if item.get('hts')))
        unique_origins = len(set(item['country_of_origin'] for item in items 
                                 if item.get('country_of_origin')))
        
        return {
            'total_items': len(items),
            'total_quantity': round(total_qty, 2),
            'total_value': round(total_value, 2),
            'total_weight_kg': round(total_weight, 2),
            'unique_skus': unique_skus,
            'unique_hts_codes': unique_hts,
            'unique_origins': unique_origins,
        }
    
    def to_json(self, result: Dict) -> str:
        """Convert result to JSON string"""
        return json.dumps(result, indent=2)
    
    def to_dataframe(self, result: Dict) -> pd.DataFrame:
        """Convert result items to pandas DataFrame"""
        if not result.get('items'):
            return pd.DataFrame()
        return pd.DataFrame(result['items'])
    
    def export_csv(self, result: Dict, output_path: Union[str, Path]) -> None:
        """Export items to CSV"""
        df = self.to_dataframe(result)
        df.to_csv(str(output_path), index=False)
    
    def export_excel(self, result: Dict, output_path: Union[str, Path]) -> None:
        """Export items to Excel with multiple sheets"""
        df = self.to_dataframe(result)
        
        with pd.ExcelWriter(str(output_path), engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Line Items', index=False)
            
            # Add metadata sheet
            if result.get('metadata'):
                meta_df = pd.DataFrame([result['metadata']])
                meta_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Add summary sheet
            if result.get('summary'):
                summary_df = pd.DataFrame([result['summary']])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)


# Agent Interface for Iqo Layer
class AcuityParserIqoAgent:
    """
    Simplified interface for Iqo layer integration
    Follows Iqo agent protocol
    """
    
    def __init__(self):
        self.agent = AcuityInvoiceAgent()
        self.name = "acuity_invoice_parser"
        self.version = "1.0.0"
        self.capabilities = [
            "parse_acuity_xls",
            "extract_line_items",
            "convert_country_codes",
            "convert_units",
            "generate_summary"
        ]
    
    async def execute(self, action: str, params: Dict) -> Dict:
        """
        Execute agent action (Iqo protocol)
        
        Args:
            action: Action to perform
            params: Action parameters
            
        Returns:
            Dict with 'success', 'result', 'error'
        """
        try:
            if action == "parse_invoice":
                file_path = params.get('file_path')
                if not file_path:
                    return {
                        'success': False,
                        'error': 'Missing file_path parameter'
                    }
                
                aggregate = params.get('aggregate', False)
                result = await self.agent.parse_file_async(file_path, aggregate=aggregate)
                return result
            
            elif action == "export_csv":
                result = params.get('result')
                output_path = params.get('output_path')
                if not result or not output_path:
                    return {
                        'success': False,
                        'error': 'Missing result or output_path parameter'
                    }
                
                self.agent.export_csv(result, output_path)
                return {
                    'success': True,
                    'result': f'Exported to {output_path}'
                }
            
            elif action == "export_excel":
                result = params.get('result')
                output_path = params.get('output_path')
                if not result or not output_path:
                    return {
                        'success': False,
                        'error': 'Missing result or output_path parameter'
                    }
                
                self.agent.export_excel(result, output_path)
                return {
                    'success': True,
                    'result': f'Exported to {output_path}'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown action: {action}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_info(self) -> Dict:
        """Get agent information"""
        return {
            'name': self.name,
            'version': self.version,
            'capabilities': self.capabilities,
            'description': 'Parses Acuity XLS invoices and extracts line items'
        }


# Example usage
async def example_usage():
    """Example of how to use the agent"""
    
    # Create agent
    agent = AcuityInvoiceAgent(config={'validate': True})
    
    # Parse invoice (async)
    result = await agent.parse_file_async('Acuity_Invoice.xls')
    
    if result['success']:
        print(f"✓ Parsed {result['summary']['total_items']} items")
        print(f"  Total Value: ${result['summary']['total_value']:.2f}")
        print(f"  Total Weight: {result['summary']['total_weight_kg']:.2f} kg")
        
        # Export to CSV
        agent.export_csv(result, 'output.csv')
        
        # Export to Excel
        agent.export_excel(result, 'output.xlsx')
        
        # Get JSON
        json_output = agent.to_json(result)
        print(json_output)
    else:
        print(f"✗ Error: {result['error']}")


# Iqo integration example
async def iqo_integration_example():
    """Example of Iqo layer integration"""
    
    # Create Iqo-compatible agent
    iqo_agent = AcuityParserIqoAgent()
    
    # Get agent info
    info = iqo_agent.get_info()
    print(f"Agent: {info['name']} v{info['version']}")
    
    # Execute parsing action
    result = await iqo_agent.execute('parse_invoice', {
        'file_path': 'Acuity_Invoice.xls'
    })
    
    if result['success']:
        print(f"✓ Success: {result['summary']['total_items']} items parsed")
        
        # Export to CSV
        await iqo_agent.execute('export_csv', {
            'result': result,
            'output_path': 'output.csv'
        })
    else:
        print(f"✗ Error: {result['error']}")


if __name__ == '__main__':
    # Run example
    asyncio.run(example_usage())
