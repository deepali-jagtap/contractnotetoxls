# main.py

from process.process_pdf import process_folder


def main():
    # Define paths for the source folder and the completed folder
    folder_path = "./docs"  # Folder containing the PDF files
    completed_folder = "./completed"  # Folder where processed files will be moved
    passwd = "DEE0702"

    # Process each file in the folder
    process_folder(folder_path, completed_folder, passwd)


if __name__ == "__main__":
    main()
