#!/usr/bin/env python
# coding: utf-8

import pdfplumber
import pandas as pd
import re
import os
import pikepdf
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

from constants import (
    # File and folder paths
    TEMP_UNLOCKED_PDF, CSV_FOLDER_PATH, PDF_EXT, CSV_EXT,

    # CSV-related constants
    CSV_ENCODING, CSV_MODE_APPEND, NUM_COLUMNS, BOUGHT_STOCKS_CSV, SOLD_STOCKS_CSV,
    BUY_LEDGER_CSV, SELL_LEDGER_CSV, LEDGER_COLUMNS,

    # Column names and patterns
    SEGMENT_COLUMN, SECURITY_DESCRIPTION, PARENTHESES_PATTERN, SUB_TOTAL_STRING,
    COLUMN_SECURITY_DESC, COLUMN_QUANTITY_BOUGHT, COLUMN_QUANTITY_SOLD,
    COLUMN_TOTAL_GROSS, COLUMN_AVERAGE_RATE,

    # Ledger constants
    LEDGER_DATE, LEDGER_VOUCHER_TYPE, LEDGER_DAY, LEDGER_MONTH, LEDGER_REF_NO,
    LEDGER_DR_LEDGER, LEDGER_CR_LEDGER, LEDGER_AMOUNT, LEDGER_NARRATION,
    VOUCHER_TYPE, SHARES_LABEL,

    # Narration-related
    NARRATION_QUANTITY, NARRATION_RATE, EMPTY_STRING, CREATE_LEDGER_XML, BROKER_NAME,

    # Ledger creation related
    XML_ENVELOPE, XML_HEADER, XML_TALLYREQUEST, XML_BODY, XML_IMPORT_DATA, XML_REQUESTDESC,
    XML_REQUESTNAME, REPORT_NAME_ALL_MASTERS, XML_REQUESTDATA, XML_TALLYMESSAGE, TALLY_UDF_NAMESPACE,
    TALLY_GROUP_NAME, XML_ACTION, XML_ACTION_CREATE, XML_GROUP, XML_NAME, XML_PARENT, TALLY_GROUP_PARENT,
    CSV_COLUMN_DR_LEDGER, XML_LEDGER, XML_OPENINGBALANCE, CSV_COLUMN_AMOUNT, CSV_COLUMN_NARRATION, XML_NARRATION,
)
from logger import  log_failed_file
from loguru import logger



def move_file(src, dest):
    try:
        # Attempt to move the file
        shutil.move(src, dest)
        # Check if the move was successful
        if not os.path.exists(src) and os.path.exists(dest):
            print("")
        else:
            logger.error(" Source still exists or destination does not exist. FalseNo exist !")
            print("Move failed: Source still exists or destination does not exist. {dest}")
    except Exception as e:
        logger.opt(exception=True).error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")


# Function to clean values based on regex pattern
def clean_value(value):
    # Check if the value is a string and matches the pattern
    if isinstance(value, str):
        # Remove parentheses if they enclose a number
        return re.sub(PARENTHESES_PATTERN, r'\1', value)
    return value  # Return the value unchanged if it's not a string


# Function to unlock a PDF and save it as a temporary unlocked version
def unlock_pdf(locked_pdf, passwd):
    try:
        with pikepdf.open(locked_pdf, password=passwd) as pdf:
            pdf.save(TEMP_UNLOCKED_PDF)
        return True
    except Exception as e:
        print(f"Error unlocking PDF: {e}")
        logger.opt(exception=True).error(f"Error unlocking PDF: {e}")
        return False


def extract_date_components(trade_date):
    """
    Extracts 'Date', 'Day', and 'Month' from a trade date in the format 'DD-MMM-YYYY'.

    Parameters:
        trade_date (str): The trade date string in the format 'DD-MMM-YYYY'.

    Returns:
        dict: A dictionary containing 'Date', 'Day', and 'Month' as numbers.
    """
    try:
        # Parse the date string into a datetime object
        date_obj = datetime.strptime(trade_date, '%d-%b-%Y')

        # Extract components
        date = date_obj.strftime('%d-%m-%Y')  # Convert to 'DD-MM-YYYY'
        day = date_obj.day  # Numerical day of the month (1-31)
        month = date_obj.month  # Numerical month (1-12)

        return {"Date": date, "Day": day, "Month": month}

    except ValueError:
        # logger.opt(exception=True).error(f"Invalid date format: {trade_date}")
        print(f"Invalid date format: {trade_date}")
        return {"Date": "", "Day": "", "Month": ""}


def process_hdfc_securities(folder_path, completed_folder, passwd):
    """Function to process all files in a folder and move them to the completed folder."""
    if not os.path.exists(completed_folder):
        os.makedirs(completed_folder)

    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(PDF_EXT):  # Only process PDF files
            file_path = os.path.join(folder_path, filename)
            print(f"Processing file: {file_path}")
        try:
            if unlock_pdf(file_path, passwd):
                filtered_tables, trade_date = extract_tables_from_pdf(TEMP_UNLOCKED_PDF,file_path,completed_folder,filename)
                date_components = extract_date_components(trade_date)
                print("mapped_data==>", filtered_tables, trade_date)

                if filtered_tables:
                    print("22==> found filtered_tables " )
                    process_pdfs_to_ledger_with_new_format(filtered_tables, BUY_LEDGER_CSV, SELL_LEDGER_CSV,
                                                           date_components)
                    generate_ledger_xml(BUY_LEDGER_CSV,SELL_LEDGER_CSV)
                    move_file(file_path, os.path.join(completed_folder, filename))
                    logger.success(f"SUCCESS: Processed {filename}")
                    print(f"SUCCESS: Processed {filename}")
                else:
                    logger.warning(f"No valid tables found in {filename}")
                    log_failed_file(filename, f"No valid tables found in {filename}")
                    print(f"No valid tables found in {filename}")
            else:
                logger.error(f"Failed to unlock PDF: {filename}")
                print(f"Failed to unlock PDF: {filename}")
        except Exception as e:
            logger.opt(exception=True).error(f"Error processing file {filename}: {e}")
            log_failed_file(filename, f"Error processing file {filename}: {e}")
            print(f"Error processing file {filename}: {e}")
            continue


# Open the PDF file
def process_file(lockedpdf, passwd):
    try:
        filtered_tables = []
        with pikepdf.open(lockedpdf, password=passwd) as pdf:
            pdf.save(TEMP_UNLOCKED_PDF)
        with pdfplumber.open(TEMP_UNLOCKED_PDF) as pdf:

            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()

                for table_idx, table in enumerate(tables):
                    if table:  # Check if table is not empty
                        header = table[0]  # Assuming first row is the header

                    # Check if the header contains a column named 'Segment' and has 11 columns
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

            if not filtered_tables:
                print("No tables with the specified criteria found in the document.")
                logger.info("No tables with the specified criteria found in the document.")

        # Export each filtered table to a CSV file using pandas
        file_name = os.path.splitext(os.path.basename(lockedpdf))[0]
        csv_filename = f'{CSV_FOLDER_PATH}/{file_name}{CSV_EXT}'

        for idx, table in enumerate(filtered_tables):
            df = pd.DataFrame(table[1:], columns=table[0])  # Convert to DataFrame with header

            # Strip leading and trailing spaces from all string columns
            string_columns = df.select_dtypes(include=['object']).columns  # Get all string columns

            df[string_columns] = df[string_columns].apply(lambda x: x.str.strip())

            # For the first table, write header:
            if idx == 0:
                df.to_csv(csv_filename, index=False, encoding=CSV_ENCODING)
            else:
                # For subsequent tables, append without header:
                df.to_csv(csv_filename, index=False, mode=CSV_MODE_APPEND, header=False)

        identify_speculation(csv_filename)
        return True
    except Exception as e:
        logger.opt(exception=True).error(f"ERROR: {lockedpdf} An unexpected error occurred: {e}")
        print(f"ERROR: {lockedpdf} An unexpected error occurred: {e}")


# Function to process a single PDF file and extract tables
def extract_tables_from_pdf(pdf_path,file_path,completed_folder,filename):
    filtered_tables = []
    trade_date = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            trade_date_match = re.search(r"Trade Date\s*(\d{1,2}-[a-zA-Z]{3}-\d{4})", page.extract_text(), re.IGNORECASE)
            if trade_date_match:
                if trade_date == '':
                    trade_date = trade_date_match.group(1)
                    print('Trade date: ', trade_date)

            for table_idx, table in enumerate(tables):
                if table:
                    print("length of table i s==>",len(table[0]))
                    date_components = extract_date_components(trade_date)
                    if 'ISIN' in table[1] or len(table[1]) == 14 or len(table[0]) == 14:
                        filtered_table = [row for row in table if len(row) == 14]
                        mapped_data = transform_equity_data(filtered_table)
                        if mapped_data:
                            df = create_dataframe(mapped_data)
                            process_dataframe(df)
                            save_ledger_entries(df,date_components)
                            generate_ledger_xml(BUY_LEDGER_CSV, SELL_LEDGER_CSV)
                            move_file(file_path, os.path.join(completed_folder, filename))
                        else:
                            print("mapped_data is empty")
                    elif len(table[0]) == 10:
                        date_components = extract_date_components(trade_date)
                        filtered_table = [row for row in table if len(row) == 10]
                        mapped_data = transform_derivative_data(filtered_table)
                        if mapped_data:
                            df = create_dataframe(mapped_data)
                            process_dataframe(df)
                            save_ledger_entries(df,date_components)
                            generate_ledger_xml(BUY_LEDGER_CSV, SELL_LEDGER_CSV)
                            move_file(file_path, os.path.join(completed_folder, filename))
                        else:
                            print("mapped_data is empty")

                    header = table[0]
                    if SEGMENT_COLUMN in header and len(header) == NUM_COLUMNS:
                        filtered_table = [row for row in table if len(row) == NUM_COLUMNS]
                        filtered_table = [
                            [clean_value(cell) for cell in row] for row in filtered_table
                            if SUB_TOTAL_STRING not in row
                        ]

                        if filtered_table:
                            filtered_tables.append(filtered_table)
                            logger.info(f"Table {table_idx + 1} on page {page_number} meets the criteria.")
                            print(f"Table {table_idx + 1} on page {page_number} meets the criteria.")
    return filtered_tables, trade_date


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
        logger.opt(exception=True).error("Columns for 'bought' or 'sold' quantities not found in the dataset.")
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
            logger.info(f"Speculation detected for stock:\n {stock} | Bought: {bought_qty} | Sold: {sold_qty}")
    else:
        print("No speculative trades found.")
        logger.warning("No speculative trades found.")


def process_pdfs_to_ledger_with_new_format(filtered_tables, buy_ledger_csv, sell_ledger_csv, date_components):
    """
    Processes filtered tables from PDFs and creates buy and sell ledger CSV files with the specified format.

    Parameters:
        filtered_tables (list): List of tables extracted from PDFs.
        buy_ledger_csv (str): Path to the CSV file where the buy ledger will be saved.
        sell_ledger_csv (str): Path to the CSV file where the sell ledger will be saved.
        date_components (dict): Value of Date, Day and Month calculated from trade date.
    """
    try:
        # Initialize lists to store buy and sell ledger entries
        buy_ledger_entries = []
        sell_ledger_entries = []
        print("33 ===>",buy_ledger_csv,sell_ledger_csv,date_components)
        # Process each table in the filtered tables
        for table in filtered_tables:
            print("44 ===> table", table)

            # Convert the table (a list of lists) into a DataFrame
            df = pd.DataFrame(table[1:], columns=table[0])  # Create DataFrame with headers
            print(" 55 ==> dfTable==>",df)

            # Clean and standardize column names
            df.columns = (
                df.columns.str.strip()
                .str.replace(r'\s+', ' ', regex=True)  # Replace multiple spaces with single space
            )
            print("66==>", df.columns )
            # Strip spaces from all string columns
            string_columns = df.select_dtypes(include=["object"]).columns
            df[string_columns] = df[string_columns].apply(lambda x: x.str.strip())

            # Ensure relevant columns are numeric (replace invalid entries with 0)
            numeric_columns = [COLUMN_QUANTITY_BOUGHT, COLUMN_QUANTITY_SOLD, COLUMN_TOTAL_GROSS, COLUMN_AVERAGE_RATE]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            print("dfRows",df.iterrows())
            # Process each row in the DataFrame
            for _, row in df.iterrows():
                # Check for Buy Entries
                print("array==>", row)

                if row[COLUMN_QUANTITY_BOUGHT] > 0:
                    # Extract and process the security description
                    security_desc = row[COLUMN_SECURITY_DESC].split('-')[0].strip() + ' ' + SHARES_LABEL

                    buy_ledger_entries.append({
                        LEDGER_DATE: date_components[LEDGER_DATE],
                        LEDGER_VOUCHER_TYPE: VOUCHER_TYPE,
                        LEDGER_DAY: date_components[LEDGER_DAY],
                        LEDGER_MONTH: date_components[LEDGER_MONTH],
                        LEDGER_REF_NO: EMPTY_STRING,
                        LEDGER_DR_LEDGER: security_desc,
                        LEDGER_CR_LEDGER: BROKER_NAME,
                        LEDGER_AMOUNT: row[COLUMN_TOTAL_GROSS],
                        LEDGER_NARRATION: f"{NARRATION_QUANTITY}: {row[COLUMN_QUANTITY_BOUGHT]}, "
                                          f"{NARRATION_RATE}: {row[COLUMN_AVERAGE_RATE]}"
                    })

                # Check for Sell Entries
                if row[COLUMN_QUANTITY_SOLD] > 0:
                    # Extract and process the security description
                    security_desc = row[COLUMN_SECURITY_DESC].split('-')[0].strip() + ' ' + SHARES_LABEL
                    sell_ledger_entries.append({
                        LEDGER_DATE: date_components[LEDGER_DATE],
                        LEDGER_VOUCHER_TYPE: VOUCHER_TYPE,
                        LEDGER_DAY: date_components[LEDGER_DAY],
                        LEDGER_MONTH: date_components[LEDGER_MONTH],
                        LEDGER_REF_NO: EMPTY_STRING,
                        LEDGER_DR_LEDGER: BROKER_NAME,
                        LEDGER_CR_LEDGER: security_desc,
                        LEDGER_AMOUNT: row[COLUMN_TOTAL_GROSS],
                        LEDGER_NARRATION: f"{NARRATION_QUANTITY}: {row[COLUMN_QUANTITY_SOLD]}, "
                                          f"{NARRATION_RATE}: {row[COLUMN_AVERAGE_RATE]}"
                    })

        # Save the buy ledger entries to the specified CSV file
        if not os.path.exists(buy_ledger_csv):
            buy_ledger_df = pd.DataFrame([], columns=LEDGER_COLUMNS)
            buy_ledger_df.to_csv(buy_ledger_csv, index=False, encoding=CSV_ENCODING, mode='a',
                                 header=not os.path.exists(buy_ledger_csv))

        if buy_ledger_entries:
            buy_ledger_df = pd.DataFrame(buy_ledger_entries, columns=LEDGER_COLUMNS)
            buy_ledger_df.to_csv(buy_ledger_csv, index=False, encoding=CSV_ENCODING, mode='a',
                                 header=not os.path.exists(buy_ledger_csv))
            logger.success("Data processing succeeded!")
            print(f"Buy ledger saved to: {buy_ledger_csv}")
        else:
            logger.error("No buy data found. Buy ledger CSV not created.")
            print("No buy data found. Buy ledger CSV not created.")

        # Save the sell ledger entries to the specified CSV file
        if sell_ledger_entries:
            sell_ledger_df = pd.DataFrame(sell_ledger_entries, columns=LEDGER_COLUMNS)
            sell_ledger_df.to_csv(sell_ledger_csv, index=False, encoding=CSV_ENCODING, mode='a',
                                  header=not os.path.exists(sell_ledger_csv))
            logger.success(f"Sell ledger saved to: {sell_ledger_csv}")
            print(f"Sell ledger saved to: {sell_ledger_csv}")
        else:
            logger.warning("No sell data found. Sell ledger CSV not created.")
            print("No sell data found. Sell ledger CSV not created.")

    except Exception as e:
        logger.opt(exception=True).error(f"Error occurred during ledger processing: {e}")


def generate_ledger_xml(buy_csv_path, sell_csv_path):
    print("buy_csv_path==>",buy_csv_path)
    print("sell_csv_path",sell_csv_path)
    buy_df = pd.read_csv(buy_csv_path)
    sell_df = pd.read_csv(sell_csv_path)

    # Drop completely empty rows (all NaN values)
    buy_df.dropna(how="all", inplace=True)
    sell_df.dropna(how="all", inplace=True)

    # Check if both dataframes are empty
    if buy_df.empty and sell_df.empty:
        logger.warning("Both Buy and Sell ledgers are empty. Skipping XML generation.")
        print("WARNING: Both Buy and Sell ledgers are empty. Skipping XML generation.")
        return

    # Concatenate only non-empty DataFrames
    dataframes_to_concat = [df for df in [buy_df, sell_df] if not df.empty]
    combined_df = pd.concat(dataframes_to_concat, ignore_index=True)

    envelope = ET.Element(XML_ENVELOPE)
    header = ET.SubElement(envelope, XML_HEADER)
    ET.SubElement(header, XML_TALLYREQUEST).text = "Import Data"

    body = ET.SubElement(envelope, XML_BODY)
    import_data = ET.SubElement(body, XML_IMPORT_DATA)
    request_desc = ET.SubElement(import_data, XML_REQUESTDESC)
    ET.SubElement(request_desc, XML_REQUESTNAME).text = REPORT_NAME_ALL_MASTERS

    request_data = ET.SubElement(import_data, XML_REQUESTDATA)

    # Create Tally Group
    tally_message_group = ET.SubElement(request_data, XML_TALLYMESSAGE, {"xmlns:UDF": TALLY_UDF_NAMESPACE})
    group = ET.SubElement(tally_message_group, XML_GROUP, {"NAME": TALLY_GROUP_NAME, XML_ACTION: XML_ACTION_CREATE })
    ET.SubElement(group, XML_NAME).text = TALLY_GROUP_NAME
    ET.SubElement(group, XML_PARENT).text = TALLY_GROUP_PARENT

    # Process all ledger entries from the combined dataset
    for _, row in combined_df.iterrows():
        dr_ledger = str(row[CSV_COLUMN_DR_LEDGER]).replace("\n", "").strip() if pd.notna(row[CSV_COLUMN_DR_LEDGER]) else ""
        cr_ledger = str(row["Cr. Ledger Name"]).replace("\n", "").strip() if pd.notna(row["Cr. Ledger Name"]) else ""

        # Use the Cr. Ledger if Dr. Ledger is "HDFC Securities Limited"
        ledger_name = cr_ledger if dr_ledger == "HDFC Securities Limited" else dr_ledger

        if not ledger_name:  # Skip if ledger_name is empty
            continue

        # Add the entry to XML
        tally_message_ledger = ET.SubElement(request_data, XML_TALLYMESSAGE, {"xmlns:UDF": TALLY_UDF_NAMESPACE,})
        ledger = ET.SubElement(tally_message_ledger, XML_LEDGER, {"NAME": ledger_name, XML_ACTION: XML_ACTION_CREATE,"IGNOREALTER":"Yes"})
        ET.SubElement(ledger, XML_NAME).text = ledger_name
        ET.SubElement(ledger, XML_PARENT).text = TALLY_GROUP_NAME
        # ET.SubElement(ledger, XML_OPENINGBALANCE).text = str(row[CSV_COLUMN_AMOUNT])
        ET.SubElement(ledger, XML_NARRATION).text = row[CSV_COLUMN_NARRATION]

    # Convert to pretty XML format
    xml_str = ET.tostring(envelope, encoding='unicode')
    parsed_xml = parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")

    with open(CREATE_LEDGER_XML, "w") as xml_file:
        xml_file.write(pretty_xml)

    print("SUCCESS: Ledger XML generated from both Buy & Sell ledgers")
    logger.success("Both Buy and Sell ledgers are empty. Skipping XML generation.")

def transform_equity_data(data):
    """
    Transforms the given data into the desired format.

    Args:
      data: A list of lists representing the input data.

    Returns:
      A list of lists of lists representing the transformed data.
    """

    transformed_data = []
    for i, row in enumerate(data):
        if i <= 1:  # Skip the first two header rows
            continue

        buy_quantity = int(row[2]) if row[2].isdigit() else 0
        sell_quantity = int(row[7]) if row[7].isdigit() else 0

        # Handle potential ValueError for Total BUY Value
        try:
            total_buy_value = float(row[6])
        except ValueError:
            total_buy_value = 0.0

        # Handle potential ValueError for Total SELL Value
        try:
            total_sell_value = float(row[11])
        except ValueError:
            total_sell_value = 0.0

        # Handle potential ValueError for Net Obligation
        try:
            net_obligation = float(row[13])
        except ValueError:
            net_obligation = 0.0

        # Handle potential ValueError for Brokerage per share.
        try:
            buy_brokerage = float(row[4])
        except ValueError:
            buy_brokerage = 0.0

        try:
            sell_brokerage = float(row[9])
        except ValueError:
            sell_brokerage = 0.0

        try:
            buy_wap = float(row[3])
        except ValueError:
            buy_wap = 0.0

        try:
            sell_wap = float(row[8])
        except ValueError:
            sell_wap = 0.0

        segment_data = [
            [
                "Segment",
                "Security description",
                "Quantity\nBought for you",
                "Quantity Sold\nfor you",
                "Total gross\n(Rs.)",
                "Average rate\n(Rs.)",
                "Brokerage\n(Total)",
                "**GST on\nBrokerage (Rs.)",
                "Total Security\nTransaction\nTax(Rs.)",
                "Other\nStatutory\n*Levies(Rs.)",
                "Net Amount\n(Rs.)"
            ],
            [
                "Equity",  # Assuming all are Equity for simplicity. You might need logic to determine the segment.
                row[1].replace('-\n', '-'),  # Security description
                str(buy_quantity),
                str(sell_quantity),
                str(abs(total_buy_value if total_buy_value != 0 else total_sell_value)),  # Total gross (using buy or sell value)
                str(buy_wap if buy_wap != 0 else sell_wap),  # Average rate (using buy or sell WAP)
                str(abs(buy_brokerage if buy_brokerage != 0 else sell_brokerage)),  # Brokerage (using buy or sell value)
                "0.00",  # GST on Brokerage (assuming 0 for simplicity)
                "0.00",  # Total Security Transaction Tax (assuming 0 for simplicity)
                "0.00",  # Other Statutory *Levies (assuming 0 for simplicity)
                str(abs(net_obligation)),  # Net Amount
            ]
        ]
        transformed_data.append(segment_data)
    return transformed_data


def create_dataframe(mapped_data):
    """Creates a Pandas DataFrame from mapped data."""
    data_rows = [item[1] for item in mapped_data]
    headers = mapped_data[0][0]
    df = pd.DataFrame(data_rows, columns=headers)
    print("55 ==> dfTable==>", df)
    return df

def process_dataframe(df):
    """Cleans, standardizes, and converts data in the DataFrame."""
    df.columns = (
        df.columns.str.strip().str.replace(r'\s+', ' ', regex=True)
    )
    print("66==>", df.columns)

    string_columns = df.select_dtypes(include=["object"]).columns
    df[string_columns] = df[string_columns].apply(lambda x: x.str.strip())

    numeric_columns = [COLUMN_QUANTITY_BOUGHT, COLUMN_QUANTITY_SOLD, COLUMN_TOTAL_GROSS, COLUMN_AVERAGE_RATE]
    print("77 ==>", numeric_columns)
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    print("dfRows", df.iterrows())

def save_ledger_entries(df,date_components):
    """Generates and saves buy and sell ledger entries to CSV files."""
    sell_ledger_entries = []
    buy_ledger_entries = []
    for _, row in df.iterrows():
        if row[COLUMN_QUANTITY_BOUGHT] > 0:
            result = re.sub(r'\s+', ' ', re.sub(r'([a-zA-Z])\1+', r'\1',
                                                row[COLUMN_SECURITY_DESC].replace('\n', ''))).strip().title()
            security_desc = result.split('-')[0].strip() + ' ' + SHARES_LABEL
            buy_ledger_entries.append({
                LEDGER_DATE: date_components[LEDGER_DATE],
                LEDGER_VOUCHER_TYPE: VOUCHER_TYPE,
                LEDGER_DAY: date_components[LEDGER_DAY],
                LEDGER_MONTH: date_components[LEDGER_MONTH],
                LEDGER_REF_NO: EMPTY_STRING,
                LEDGER_DR_LEDGER: security_desc,
                LEDGER_CR_LEDGER: BROKER_NAME,
                LEDGER_AMOUNT: row[COLUMN_TOTAL_GROSS],
                LEDGER_NARRATION: f"{NARRATION_QUANTITY}: {row[COLUMN_QUANTITY_BOUGHT]}, {NARRATION_RATE}: {row[COLUMN_AVERAGE_RATE]}"
            })

        if row[COLUMN_QUANTITY_SOLD] > 0:

            result = re.sub(r'\s+', ' ', re.sub(r'([a-zA-Z])\1+', r'\1', row[COLUMN_SECURITY_DESC].replace('\n', ''))).strip().title()
            security_desc = result.split('-')[0].strip() + ' ' + SHARES_LABEL
            sell_ledger_entries.append({
                LEDGER_DATE: date_components[LEDGER_DATE],
                LEDGER_VOUCHER_TYPE: VOUCHER_TYPE,
                LEDGER_DAY: date_components[LEDGER_DAY],
                LEDGER_MONTH: date_components[LEDGER_MONTH],
                LEDGER_REF_NO: EMPTY_STRING,
                LEDGER_DR_LEDGER: BROKER_NAME,
                LEDGER_CR_LEDGER: security_desc,
                LEDGER_AMOUNT: row[COLUMN_TOTAL_GROSS],
                LEDGER_NARRATION: f"{NARRATION_QUANTITY}: {row[COLUMN_QUANTITY_SOLD]}, {NARRATION_RATE}: {row[COLUMN_AVERAGE_RATE]}"
            })

    # Save buy ledger
    if not os.path.exists(BUY_LEDGER_CSV):
        buy_ledger_df = pd.DataFrame([], columns=LEDGER_COLUMNS)
        buy_ledger_df.to_csv(BUY_LEDGER_CSV, index=False, encoding=CSV_ENCODING, mode='a', header=True)

    if buy_ledger_entries:
        buy_ledger_df = pd.DataFrame(buy_ledger_entries, columns=LEDGER_COLUMNS)
        buy_ledger_df.to_csv(BUY_LEDGER_CSV, index=False, encoding=CSV_ENCODING, mode='a', header=False)
        logger.success(f"Buy ledger saved to: {BUY_LEDGER_CSV}")
        print(f"Buy ledger saved to: {BUY_LEDGER_CSV}")
    else:
        logger.error("No buy data found. Buy ledger CSV not created.")
        print("No buy data found. Buy ledger CSV not created.")

    # Save sell ledger
    if not os.path.exists(SELL_LEDGER_CSV):
        sell_ledger_df = pd.DataFrame([], columns=LEDGER_COLUMNS)
        sell_ledger_df.to_csv(SELL_LEDGER_CSV, index=False, encoding=CSV_ENCODING, mode='a', header=True)

    if sell_ledger_entries:
        sell_ledger_df = pd.DataFrame(sell_ledger_entries, columns=LEDGER_COLUMNS)
        sell_ledger_df.to_csv(SELL_LEDGER_CSV, index=False, encoding=CSV_ENCODING, mode='a', header=False)
        logger.success(f"Sell ledger saved to: {SELL_LEDGER_CSV}")
        print(f"Sell ledger saved to: {SELL_LEDGER_CSV}")
    else:
        logger.warning("No sell data found. Sell ledger CSV not created.")
        print("No sell data found. Sell ledger CSV not created.")
def transform_derivative_data(input_data):
    """
    Transforms derivative data into the desired format, specifically for the given input structure.

    Args:
        input_data: A list of lists representing the derivative data.

    Returns:
        A list of lists of lists representing the transformed derivative data,
        or an empty list if there's an error.
    """

    transformed_data = []

    if not input_data or len(input_data) < 2:
        return []  # Return empty list for invalid input

    row = input_data[1]  # Extract the data row

    # Directly use the known indices for the data
    security_description = row[0].replace('-\n', '-')
    buy_quantity = int(row[2]) if isinstance(row[2], str) and row[2].isdigit() else 0
    wap_rs = float(row[4]) if isinstance(row[4], (int, float, str)) and str(row[4]).replace('.', '', 1).isdigit() else 0.0
    brokerage_per_unit = float(row[5]) if isinstance(row[5], (int, float, str)) and str(row[5]).replace('.', '', 1).isdigit() else 0.0
    net_total = float(row[8]) if isinstance(row[8], (int, float, str)) and str(row[8]).replace('.', '', 1).isdigit() else 0.0

    segment_data = [
        [
            "Segment",
            "Security description",
            "Quantity\nBought for you",
            "Quantity Sold\nfor you",
            "Total gross\n(Rs.)",
            "Average rate\n(Rs.)",
            "Brokerage\n(Total)",
            "**GST on\nBrokerage (Rs.)",
            "Total Security\nTransaction\nTax(Rs.)",
            "Other\nStatutory\n*Levies(Rs.)",
            "Net Amount\n(Rs.)"
        ],
        [
            "Derivative",
            security_description,
            str(buy_quantity),
            "0",  # Quantity Sold is 0 for derivatives in this context
            str(abs(net_total)),
            str(wap_rs),
            str(abs(buy_quantity * brokerage_per_unit)),
            "0.00",
            "0.00",
            "0.00",
            str(abs(net_total)),
        ]
    ]

    transformed_data.append(segment_data)
    return transformed_data