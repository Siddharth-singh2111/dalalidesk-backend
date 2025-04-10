import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the Python path to find the 'backup' module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Now import the backup module
from backup import backup

load_dotenv()

def _perform_backup():
    """Core logic to perform the database backup and upload.
    Logs errors internally.
    Returns: Dict with status and message/result.
    """
    print("Attempting scheduled backup...")
    try:
        current_date = datetime.now()
        formatted_date = current_date.strftime('%d_%b_%Y')
        
        # Retrieve and validate environment variables
        dbname = os.getenv('DB_NAME')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        gdrive_cred_path = os.getenv('GDRIVE_CRED_PATH')
        gdrive_folder_id = os.getenv('GDRIVE_FOLDER_ID')

        missing_vars = []
        if not dbname: missing_vars.append('DB_NAME')
        if not user: missing_vars.append('DB_USER')
        if not password: missing_vars.append('DB_PASSWORD')
        if not gdrive_cred_path: missing_vars.append('GDRIVE_CRED_PATH')
        if not gdrive_folder_id: missing_vars.append('GDRIVE_FOLDER_ID')

        if missing_vars:
            error_message = f'Scheduled Backup Failed: Missing required environment variables: {", ".join(missing_vars)}'
            print(error_message)
            return {'status': 'error', 'message': error_message}

        # Ensure the backups directory exists relative to this script's location or project root
        backups_dir = os.path.join(parent_dir, 'backups') # Assuming backups dir is in the project root
        os.makedirs(backups_dir, exist_ok=True)
        backup_file_path = os.path.join(backups_dir, f'backup_{formatted_date}.sql')

        # Call the backup function
        result = backup.backup_and_upload_to_gdrive(user, dbname, password, gdrive_cred_path, backup_file_path, gdrive_folder_id)
        print(f"Scheduled Backup Result: {result}")
        return result

    except ImportError as e:
        error_message = f'Scheduled Backup Failed: Could not import backup module. Check PYTHONPATH. Details: {str(e)}'
        print(error_message)
        return {'status': 'error', 'message': error_message}
    except Exception as e:
        error_message = f'Scheduled Backup Failed: An error occurred during the backup process: {str(e)}'
        print(error_message)
        # Log the error for debugging
        print(f"Error during backup process: {str(e)}")
        return {'status': 'error', 'message': error_message} 