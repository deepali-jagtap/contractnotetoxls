#!/usr/bin/env python
# coding: utf-8

# In[5]:


import pdfplumber
import pandas as pd
import re
import os
import pikepdf
import shutil
from constants import (
    TEMP_UNLOCKED_PDF,
    SEGMENT_COLUMN,
    CSV_ENCODING,
    CSV_MODE_APPEND,
    NUM_COLUMNS,
    CSV_FOLDER_PATH,
    SECURITY_DESCRIPTION,
    PARENTHESES_PATTERN,
    PDF_EXT,
    SUB_TOTAL_STRING,
    CSV_EXT,
)


def move_file(src, dest):
    try:
        # Attempt to move the file
        shutil.move(src, dest)
        # Check if the move was successful
        if not os.path.exists(src) and os.path.exists(dest):
            print("")
        else:
            print("Move failed: Source still exists or destination does not exist. {dest}")
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to clean values based on regex pattern
def clean_value(value):
    # Check if the value is a string and matches the pattern
    if isinstance(value, str):
        # Remove parentheses if they enclose a number
        return re.sub(PARENTHESES_PATTERN, r'\1', value)
    return value  # Return the value unchanged if it's not a string


def process_folder(folder_path, completed_folder, passwd):
    """Function to process all files in a folder and move them to the completed folder."""
    # Ensure the completed folder exists
    if not os.path.exists(completed_folder):
        os.makedirs(completed_folder)

    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(PDF_EXT):  # Only process PDF files
            file_path = os.path.join(folder_path, filename)
            print(f"Processing file: {file_path}")

            # Process the file
            text = process_file(file_path, passwd)
            if text:
                print(f"SUCCESS: Successfully processed {filename}\n")
                # Optionally, save the text content or handle it here

                # Move the processed file to the completed folder
                completed_file_path = os.path.join(completed_folder, filename)
                move_file(file_path, completed_file_path)
            else:
                print(f"Failed to process {filename}\n")


# Open the PDF file
def process_file(lockedpdf, passwd):
    try:
        filtered_tables = []
        #print("Processing file ", lockedpdf)
        # pdffile = TEMP_UNLOCKED_PDF
        with pikepdf.open(lockedpdf, password=passwd) as pdf:
            pdf.save(TEMP_UNLOCKED_PDF)
        with pdfplumber.open(TEMP_UNLOCKED_PDF) as pdf:

            # Loop through each page
            #print("Pages: ", len(pdf.pages))
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                #print("Tables found on page ", page_number,  len(tables))

                # Loop through each table in the page
                for table_idx, table in enumerate(tables):
                    if table:  # Check if table is not empty
                        header = table[0]  # Assuming first row is the header

                    # Check if the header contains a column named 'Segment' and has 11 columns
                    #print("Header: ", header)
                    if SEGMENT_COLUMN in header and len(header) == NUM_COLUMNS:
                        # Filter rows with exactly 11 columns
                        filtered_table = [row for row in table if len(row) == NUM_COLUMNS]

                        # Remove rows that contain "Sub Total"
                        filtered_table = [row for row in filtered_table if SUB_TOTAL_STRING not in row]

                        # Apply the cleaning function to all values in the filtered table
                        filtered_table = [[clean_value(cell) for cell in row] for row in filtered_table]

                        # Only append the table if rows still remain after filtering
                        if filtered_table:
                            filtered_tables.append(filtered_table)
                        print(f"Table {table_idx + 1} on page {page_number} meets the criteria.")
                        print("=================================")
                        print(filtered_table)

            if not filtered_tables:
                print("No tables with the specified criteria found in the document.")

        # Export each filtered table to a CSV file using pandas
        file_name = os.path.splitext(os.path.basename(lockedpdf))[0]
        csv_filename = f'{CSV_FOLDER_PATH}/{file_name}{CSV_EXT}'

        for idx, table in enumerate(filtered_tables):
            df = pd.DataFrame(table[1:], columns=table[0])  # Convert to DataFrame with header
            #csv_filename = f"table_{idx+1}.csv"  # Unique filename for each table

            # Strip leading and trailing spaces from all string columns
            string_columns = df.select_dtypes(include=['object']).columns  # Get all string columns

            df[string_columns] = df[string_columns].apply(lambda x: x.str.strip())

            # For the first table, write header:
            if idx == 0:
                df.to_csv(csv_filename, index=False, encoding=CSV_ENCODING)
            else:
                # For subsequent tables, append without header:
                df.to_csv(csv_filename, index=False, mode=CSV_MODE_APPEND, header=False)

            # if (idx > 1):
            #     df.to_csv(csv_filename, index=False, mode='a', header=False)
            # else:
            #     df.to_csv(csv_filename, index=False, encoding='utf-8')  # Export DataFrame to CSV
            #print(f"Exported table {idx+1} to {csv_filename}")

        # identify_speculation('./docs\\unlockedModified.csv')
        identify_speculation(csv_filename)
        return True
    except Exception as e:
        print(f"ERROR: {lockedpdf} An unexpected error occurred: {e}")


def identify_speculation(file_path):
    print(f"Identifying speculative trades in a CSV file: ", file_path)

    data = pd.read_csv(file_path)
    data.columns = [col.strip() for col in data.columns]

    # Clean up the "Security description" column by removing newlines and extra spaces
    data[SECURITY_DESCRIPTION] = data[SECURITY_DESCRIPTION].str.replace('\n', ' ', regex=False).str.strip()

    # Adjust column names to match dataset
    bought_col = [col for col in data.columns if "Bought" in col]
    sold_col = [col for col in data.columns if "Sold" in col]

    if not bought_col or not sold_col:
        raise ValueError("Columns for 'bought' or 'sold' quantities not found in the dataset.")

    bought_col = bought_col[0]
    sold_col = sold_col[0]

    # Group by "Security description" and sum the bought and sold quantities
    grouped = data.groupby(SECURITY_DESCRIPTION)[[bought_col, sold_col]].sum()

    # Filter stocks where both bought and sold quantities are greater than 0
    speculation = grouped[(grouped[bought_col] > 0) & (grouped[sold_col] > 0)]

    # Print the speculative stocks with bought and sold quantities
    if not speculation.empty:
        for stock in speculation.index:
            bought_qty = speculation.loc[stock, bought_col]
            sold_qty = speculation.loc[stock, sold_col]
            print(f"Speculation detected for stock:\n {stock} | Bought: {bought_qty} | Sold: {sold_qty}")
    else:
        print("No speculative trades found.")
