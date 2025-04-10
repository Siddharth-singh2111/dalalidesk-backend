import subprocess
from datetime import datetime
import os
import gzip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

def backup_postgresql_database(username, database_name, password, backup_file_path):
    """Creates a backup of the PostgreSQL database using pg_dump and returns the backup status."""
    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        command = ['pg_dump', '-U', username, '-d', database_name, '--no-owner', '--no-acl', '-f', backup_file_path]
        subprocess.run(command, check=True, env=env)
        print('Backup created successfully!')
        return {'status': 'okay', 'message': 'Backup Created'}
    except subprocess.CalledProcessError as e:
        print(f'Error creating backup: {e}')
        return {'status': 'error', 'message': 'Backup Failed'}

def compress_file(file_path):
    """Compress a file using gzip"""
    compressed_path = f"{file_path}.gz"
    with open(file_path, 'rb') as f_in:
        with gzip.open(compressed_path, 'wb') as f_out:
            f_out.writelines(f_in)
    print(f"File compressed: {compressed_path}")
    return compressed_path

def upload_to_gdrive(file_path, credentials_file, folder_id=None):
    """Upload a file to Google Drive
    
    :param file_path: File to upload
    :param credentials_file: Path to Google service account JSON credentials file
    :param folder_id: Optional Google Drive folder ID to upload to
    :return: True if file was uploaded, else False
    """
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES)
        
        service = build('drive', 'v3', credentials=credentials)
        
        file_metadata = {
            'name': os.path.basename(file_path)
        }
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"File uploaded to Google Drive with ID: {file.get('id')}")
        return True
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return False

def backup_and_upload_to_gdrive(db_username, db_name, db_password, credentials_file, backup_file_path, folder_id=None):
    """Backup PostgreSQL database and upload to Google Drive
    
    :param db_username: PostgreSQL username
    :param db_name: Database name to backup
    :param db_password: PostgreSQL password
    :param credentials_file: Path to Google service account JSON credentials file
    :param backup_file_path: The desired path for the backup file
    :param folder_id: Optional Google Drive folder ID to upload to
    :return: Dict with status and message
    """
    # Create backup
    backup_result = backup_postgresql_database(db_username, db_name, db_password, backup_file_path)
    
    if backup_result['status'] == 'okay':
        try:
            # Compress the backup to save space
            compressed_file = compress_file(backup_file_path)
            
            # Upload compressed backup to Google Drive
            upload_success = upload_to_gdrive(compressed_file, credentials_file, folder_id)
            
            # Clean up local files
            if upload_success:
                os.remove(compressed_file)
                return {'status': 'okay', 'message': 'Backup created and uploaded successfully to Google Drive'}
            else:
                # Keep the local files if upload failed
                return {'status': 'partial', 'message': 'Backup created but upload to Google Drive failed'}
        except Exception as e:
            return {'status': 'partial', 'message': f'Backup created but error during compression/upload: {e}'}
    else:
        return backup_result

# Example usage
if __name__ == "__main__":
    # These values should be supplied as environment variables or a config file in a real setup
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()  # This will load variables from .env file
    
    # Use environment variables for database connection and Google Drive settings
    db_name = os.environ.get('DB_NAME')
    # Create timestamped backup filename before calling the function
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{db_name}_backup_{timestamp}.sql"

    result = backup_and_upload_to_gdrive(
        db_username=os.environ.get('DB_USER'),
        db_name=db_name,
        db_password=os.environ.get('DB_PASSWORD'),
        credentials_file=os.environ.get('GDRIVE_CRED_PATH'),
        backup_file_path=backup_file, # Pass the generated backup file path
        folder_id=os.environ.get('GDRIVE_FOLDER_ID')
    )
    print(result)