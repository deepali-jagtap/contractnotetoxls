import imaplib
import email
from email.header import decode_header
import os
import datetime

# Connect to an IMAP server
def connect_to_imap(username, password, imap_url='imap.gmail.com'):
    mail = imaplib.IMAP4_SSL(imap_url)
    mail.login(username, password)
    return mail

# Search emails between certain dates
def search_emails_between_dates(mail, start_date, end_date):
    # Select the mailbox you want to search in. 'inbox' is the default mailbox.
    mail.select("inbox")
    
    # Convert the dates to the format required by IMAP (DD-MMM-YYYY)
    start_date_str = start_date.strftime('%d-%b-%Y')
    end_date_str = end_date.strftime('%d-%b-%Y')
    
    # Search for emails between dates using the "SINCE" and "BEFORE" commands
    result, data = mail.search(None, f'(SINCE "{start_date_str}" BEFORE "{end_date_str}")')
    
    if result == "OK":
        return data[0].split()
    else:
        return []

# Safely decode the email subject, handling potential encoding issues
def safe_decode(value, encoding):
    try:
        if isinstance(value, bytes):
            # Handle 'unknown-8bit' encoding by manually trying latin-1
            if encoding == 'unknown-8bit':
                return value.decode('latin-1', errors='replace')  # Latin-1 is more tolerant of 8-bit encodings
            return value.decode(encoding if encoding else 'utf-8', errors='replace')
        return value
    except LookupError:  # Handle any other encoding errors
        return value.decode('utf-8', errors='replace')  # Fallback to utf-8

# Download attachments from emails that match the criteria
def fetch_and_download_attachments(mail, email_ids, subject_substring, download_folder="attachments"):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)  # Create folder if it doesn't exist
    
    for email_id in email_ids:
        result, message_data = mail.fetch(email_id, "(RFC822)")
        
        if result == "OK":
            for response_part in message_data:
                if isinstance(response_part, tuple):
                    # Parse the email message
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    
                    # Safely decode the subject to avoid errors
                    subject = safe_decode(subject, encoding)
                    
                    # Filter by subject substring
                    if subject_substring.lower() in subject.lower():  # Case-insensitive search
                        from_ = msg.get("From")
                        print(f"Downloading attachments from: {from_}, Subject: {subject}")

                        # Check if the email has attachments
                        if msg.is_multipart():
                            for part in msg.walk():
                                # If the part is an attachment
                                if part.get_content_disposition() == "attachment":
                                    filename = part.get_filename()
                                    if filename:
                                        # Decode the filename if necessary
                                        filename = decode_header(filename)[0][0]
                                        if isinstance(filename, bytes):
                                            filename = filename.decode()

                                        # Save the attachment
                                        filepath = os.path.join(download_folder, filename)
                                        with open(filepath, "wb") as f:
                                            f.write(part.get_payload(decode=True))
                                        print(f"Attachment downloaded: {filename}")

# Example usage
if __name__ == "__main__":
    username = "deepali.jagtap@gmail.com"
    password = "psuz ggwn jros aaau"
    
    # Connect to the server
    mail = connect_to_imap(username, password)
    
    # Specify the date range
    start_date = datetime.datetime(2024,8, 24)  # Start date (YYYY, MM, DD)
    end_date = datetime.datetime(2024, 10, 1)   # End date (YYYY, MM, DD)
    
    # Specify the substring to search for in the subject line
    subject_substring = "Contract Note for Acc No 3794559"
    
    # Search emails between the dates
    email_ids = search_emails_between_dates(mail, start_date, end_date)
    
    # Download attachments from emails that match the criteria
    fetch_and_download_attachments(mail, email_ids, subject_substring, download_folder="my_attachments")
    
    # Logout
    mail.logout()

