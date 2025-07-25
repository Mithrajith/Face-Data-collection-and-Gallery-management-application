import os
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define project root and paths
PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DB = PROJECT_ROOT / 'data' / 'app.db'
SOURCE_DATA_DIR = PROJECT_ROOT / 'data' / 'student_data'
BACKUP_DIR = PROJECT_ROOT / 'backups'
BACKUP_DB_PATH = BACKUP_DIR / 'database' / 'app.db'
BACKUP_DATA_PATH = BACKUP_DIR / 'student_data'

def should_overwrite(src, dst):
    """
    Determines if a file should be overwritten based on modification time.
    Returns True if the source is newer than the destination or if the destination
    does not exist.
    """
    if not os.path.exists(dst):
        return True
    return os.path.getmtime(src) > os.path.getmtime(dst)

def backup_database():
    """
    Backs up the main application database (app.db), overwriting only if the
    source is newer.
    """
    try:
        logger.info(f"Backing up database from {SOURCE_DB} to {BACKUP_DB_PATH}...")
        BACKUP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        if should_overwrite(SOURCE_DB, BACKUP_DB_PATH):
            shutil.copy2(SOURCE_DB, BACKUP_DB_PATH)
            logger.info("Database backup completed successfully (overwritten).")
        else:
            logger.info("Database backup skipped (no changes detected).")
            
    except FileNotFoundError:
        logger.error(f"Database file not found at {SOURCE_DB}. Backup failed.")
    except Exception as e:
        logger.error(f"An error occurred during database backup: {e}", exc_info=True)

def backup_student_data():
    """
    Backs up the student_data directory, intelligently updating only new or
    modified files.
    """
    try:
        logger.info(f"Backing up student data from {SOURCE_DATA_DIR} to {BACKUP_DATA_PATH}...")
        BACKUP_DATA_PATH.mkdir(parents=True, exist_ok=True)

        # Use copytree with a custom copy function to be more efficient
        shutil.copytree(
            SOURCE_DATA_DIR,
            BACKUP_DATA_PATH,
            dirs_exist_ok=True,
            copy_function=lambda src, dst: shutil.copy2(src, dst) if should_overwrite(src, dst) else None
        )
        logger.info("Student data backup sync completed successfully.")
        
    except FileNotFoundError:
        logger.error(f"Student data directory not found at {SOURCE_DATA_DIR}. Backup failed.")
    except Exception as e:
        logger.error(f"An error occurred during student data backup: {e}", exc_info=True)

def run_backup():
    """
    Runs all backup tasks.
    """
    logger.info("Starting scheduled backup process...")
    backup_database()
    backup_student_data()
    logger.info("Scheduled backup process finished.")

if __name__ == '__main__':
    # This allows the script to be run manually for testing
    run_backup()