from loguru import logger
from constants import (
    FileLogsConfig, FAILED_CSV,
)
import csv
import os
def configure_logger(*, create_log_file):
    logger.remove()
    logfile_config = FileLogsConfig.FILE_ARGS.copy()
    logger.add(**logfile_config,backtrace=True)

import os
import csv
from datetime import datetime


def log_failed_file(filename, failure_reason):
    """Log failed files to a CSV file. Create the file if it doesn't exist."""
    try:
        file_exists = os.path.exists(FAILED_CSV)
        print("FAILED_CSV==>",FAILED_CSV)

        with open(FAILED_CSV, mode="a", newline="") as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(["Filename", "Failure Reason", "Timestamp"])

            writer.writerow([filename, failure_reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    except Exception as e:
        print(f"Failed to log error to CSV: {e}")