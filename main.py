# main.py
from constants import (
    DOCS_FOLDER_PATH,
    COMPLETED_FOLDER_PATH,
    DEFAULT_PDF_PASS,
    BOUGHT_STOCKS_CSV,
    SOLD_STOCKS_CSV,
    PROFIT_LOSS_CSV,
    BUY_LEDGER_CSV,
    SELL_LEDGER_CSV
)

from process.process_pdf import calculate_profit_loss, process_folder
import os


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
    process_folder(DOCS_FOLDER_PATH, COMPLETED_FOLDER_PATH, DEFAULT_PDF_PASS)

    # calculate_profit_loss(BOUGHT_STOCKS_CSV, SOLD_STOCKS_CSV, PROFIT_LOSS_CSV)


if __name__ == "__main__":
    main()
