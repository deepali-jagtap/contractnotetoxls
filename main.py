# main.py
from constants import (
    DOCS_FOLDER_PATH,
    COMPLETED_FOLDER_PATH,
    PDF_PASS,
    BOUGHT_STOCKS_CSV,
    SOLD_STOCKS_CSV,
    PROFIT_LOSS_CSV,
    BUY_LEDGER_CSV,
    SELL_LEDGER_CSV, BROKER_NAME
)
from logger import configure_logger

from process.process_pdf import process_hdfc_securities
import os
configure_logger(create_log_file=True)

def main():
    # Clear existing CSV files to start fresh
    if os.path.exists(BOUGHT_STOCKS_CSV):
        os.remove(BOUGHT_STOCKS_CSV)
    if os.path.exists(SOLD_STOCKS_CSV):
        os.remove(SOLD_STOCKS_CSV)
    if os.path.exists(PROFIT_LOSS_CSV):
        os.remove(PROFIT_LOSS_CSV)
    if os.path.exists(BUY_LEDGER_CSV):
        os.remove(BUY_LEDGER_CSV)
    if os.path.exists(SELL_LEDGER_CSV):
        os.remove(SELL_LEDGER_CSV)

    # Process each file in the folder
    match BROKER_NAME:
        case "HDFC Securities Limited":
            process_hdfc_securities(DOCS_FOLDER_PATH, COMPLETED_FOLDER_PATH, PDF_PASS)
        case _:
            print(f"Our system does not support {BROKER_NAME}")


if __name__ == "__main__":
    main()
