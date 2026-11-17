"""CSV export utilities."""

import csv
import io
from typing import Iterator, List


def generate_csv(columns: List[str], rows: List[List]) -> Iterator[str]:
    """Generate CSV rows from columns and data.

    Args:
        columns: List of column names
        rows: List of row data (each row is a list of values)

    Yields:
        CSV-formatted string lines
    """
    # Write UTF-8 BOM for Excel compatibility
    yield "\ufeff"

    # Create string buffer
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    # Write header
    writer.writerow(columns)
    output = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    yield output

    # Write rows
    for row in rows:
        # Convert None to empty string, handle non-string values
        clean_row = [str(value) if value is not None else "" for value in row]
        writer.writerow(clean_row)
        output = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        yield output
    
    buffer.close()

