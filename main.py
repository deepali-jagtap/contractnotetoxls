# main.py
from constants import (
    DOCS_FOLDER_PATH,
    COMPLETED_FOLDER_PATH,
    DEFAULT_PDF_PASS,
)
from process.process_pdf import process_folder


def main():
    # Process each file in the folder
    process_folder(DOCS_FOLDER_PATH, COMPLETED_FOLDER_PATH, DEFAULT_PDF_PASS)


if __name__ == "__main__":
    main()
