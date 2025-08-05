import logging
from apscheduler.schedulers.background import BackgroundScheduler
from quality_checker import VideoQualityChecker
from config.settings import STUDENT_DATA_DIR, DEFAULT_YOLO_PATH
from services.student_data_service import get_student_data_folders
from database_backup import run_backup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_periodic_quality_checks():
    """
    Runs quality checks for all videos that haven't been processed yet.
    """
    logger.info("Starting periodic quality check...")
    
    try:
        quality_checker = VideoQualityChecker(DEFAULT_YOLO_PATH)
        
        # Get all department-year folders from the student data directory
        folders = get_student_data_folders()
        
        logger.info(f"Found {len(folders)} student data folders to check.")
        
        for folder in folders:
            # Assumes folder names are in 'dept_year' format
            parts = folder['folder'].split('_')
            if len(parts) == 2:
                dept, year = parts
                logger.info(f"Checking quality for {dept} - {year}")
                quality_checker.check_student_data_quality(dept, year, STUDENT_DATA_DIR)
            else:
                logger.warning(f"Skipping folder with unexpected name format: {folder}")
                
        logger.info("Periodic quality check finished.")
        
    except Exception as e:
        logger.error(f"An error occurred during the periodic quality check: {e}", exc_info=True)

# Initialize the scheduler
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_periodic_quality_checks, 'interval', hours=2)
scheduler.add_job(run_backup, 'cron', hour=16, minute=35)
