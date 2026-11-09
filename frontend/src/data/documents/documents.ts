export const SUPPORTED_EXTENSIONS = ['.csv'];

export const EXPECTED_CSV_COLUMNS = [
  { name: 'date', description: 'Transaction or record timestamp (YYYY-MM-DD or standard format)' },
  { name: 'revenue / amount / sales', description: 'Gross sales value per transaction' },
  { name: 'cost / profit', description: 'Cost or profit value to calculate deterministic margin' },
  { name: 'product / item / order_id', description: 'Unique identifier or item description' },
  { name: 'status', description: 'Status of the transaction (e.g., Completed, In Process)' },
];
