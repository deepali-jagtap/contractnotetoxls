#!/usr/bin/env python
# coding: utf-8

# In[5]:


import pdfplumber
import pandas as pd
import re

# Function to clean values based on regex pattern
def clean_value(value):
    # Check if the value is a string and matches the pattern
    if isinstance(value, str):
        # Remove parentheses if they enclose a number
        return re.sub(r'\(([\d.,]+)\)', r'\1', value)
    return value  # Return the value unchanged if it's not a string

# Open the PDF file
with pdfplumber.open("decrypted.pdf") as pdf:
    filtered_tables = []

    # Loop through each page
    for page_number, page in enumerate(pdf.pages, start=1):
        tables = page.extract_tables()
        print("Tables found: ", len(pdf.pages))

        # Loop through each table in the page
        for table_idx, table in enumerate(tables):
            if table:  # Check if table is not empty
                header = table[0]  # Assuming first row is the header

                # Check if the header contains a column named 'Segment' and has 11 columns
                if "Segment" in header and len(header) == 11:
                    # Filter rows with exactly 11 columns
                    filtered_table = [row for row in table if len(row) == 11]

                    # Remove rows that contain "Sub Total"
                    filtered_table = [row for row in filtered_table if "Sub Total" not in row]

                    # Apply the cleaning function to all values in the filtered table
                    filtered_table = [[clean_value(cell) for cell in row] for row in filtered_table]

                    # Only append the table if rows still remain after filtering
                    if filtered_table:
                        filtered_tables.append(filtered_table)
                        print(f"Table {table_idx+1} on page {page_number} meets the criteria.")
                        #print("=================================")
                        #print(filtered_table)

    if not filtered_tables:
        print("No tables with the specified criteria found in the document.")

# Export each filtered table to a CSV file using pandas
for idx, table in enumerate(filtered_tables):
    df = pd.DataFrame(table[1:], columns=table[0])  # Convert to DataFrame with header
    csv_filename = f"table_{idx+1}.csv"  # Unique filename for each table
    df.to_csv(csv_filename, index=False, encoding='utf-8')  # Export DataFrame to CSV
    print(f"Exported table {idx+1} to {csv_filename}")


# 

# In[ ]:





# In[ ]:




