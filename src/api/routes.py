import os
import cv2
import numpy as np
import base64
import json
import shutil
from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from models.pydantic_models import BatchInfo, GalleryInfo, ProcessingResult, StudentInfo, StudentDataSummary
from services.gallery_service import get_gallery_info, recognize_faces
from services.student_data_service import (
    get_student_data_folders, get_students_in_folder, get_student_data_summary,
    process_student_video, delete_students_by_quality, process_borderline_students,
    process_students_videos
)
from services.collection_app_service import (
    start_collection_app, stop_collection_app, get_collection_app_status,
    get_collection_app_config
)
from services.face_processing import extract_frames, detect_and_crop_faces
from utils.path_utils import get_gallery_path, get_data_path
from config.settings import BASE_DIR, BASE_GALLERY_DIR, BASE_DATA_DIR, STUDENT_DATA_DIR, DEFAULT_MODEL_PATH, DEFAULT_YOLO_PATH
import database.models as database
from ml.gallery_operations import create_gallery, update_gallery, create_gallery_from_embeddings, update_gallery_from_embeddings
from ml.embeddings import load_model, extract_embedding
from quality_checker import VideoQualityChecker
from services.auth_service import authenticate_user, add_admin_user, delete_admin_user, list_admin_users
from database.models import get_students_by_dept_and_batch
# Global quality checker instance
DEFAULT_QUALITY_CHECKER = None

def get_quality_checker():
    """Get or create quality checker instance"""
    global DEFAULT_QUALITY_CHECKER
    if DEFAULT_QUALITY_CHECKER is None:
        DEFAULT_QUALITY_CHECKER = VideoQualityChecker(DEFAULT_YOLO_PATH)
    return DEFAULT_QUALITY_CHECKER

def create_app() -> FastAPI:
    app = FastAPI(title="Face Recognition Gallery Manager", 
                  description="API for managing face recognition galleries for students by batch and department")

    # Mount static files
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/login", response_class=FileResponse)
    async def serve_login():
        """Serve the login page"""
        return FileResponse(os.path.join("static", "login.html"))

    @app.get('/departments/name/{dept_id}', summary="Get department name by ID")
    async def get_department_name_by_id(dept_id: str):
        """Get department name by department_id (string or int)"""
        try:
            with database.get_db_connection() as conn:
                cursor = conn.cursor()
                # Try both possible column names for department ID
                cursor.execute("SELECT name FROM departments WHERE id = ? OR department_id = ?", (dept_id, dept_id))
                row = cursor.fetchone()
                if row:
                    return JSONResponse({"name": row["name"]})
                else:
                    raise HTTPException(status_code=404, detail="Department not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error looking up department: {str(e)}")


    @app.get("/", response_class=FileResponse)
    async def serve_spa():
        return FileResponse("static/index.html")

    @app.get("/about", response_class=FileResponse)
    async def about():
        return FileResponse(os.path.join("static", "about.html"))

    @app.get("/static/css/toast", response_class=FileResponse)
    async def serve_style_1():
        """Serve the process video page"""
        return FileResponse(os.path.join("static","css","toast.css"))


    @app.get("/static/css/style", response_class=FileResponse)
    async def serve_style_2():
        """Serve the process video page"""
        return FileResponse(os.path.join("static","css","style.css"))

    @app.get("/home", response_class=FileResponse)
    async def serve_home():
        """Serve the process video page"""
        return FileResponse(os.path.join("static", "index.html"))

    # Split page routes
    @app.get("/process_video", response_class=FileResponse)
    async def serve_process_video():
        """Serve the process video page"""
        return FileResponse(os.path.join("static", "process_video.html"))

    @app.get("/create_gallery", response_class=FileResponse)
    async def serve_create_gallery():
        """Serve the create gallery page"""
        return FileResponse(os.path.join("static", "create_gallery.html"))

    @app.get("/view_gallery", response_class=FileResponse)
    async def serve_view_gallery():
        """Serve the view gallery page"""
        return FileResponse(os.path.join("static", "view_gallery.html"))

    @app.get("/face_reg", response_class=FileResponse)
    async def serve_face_recognition():
        """Serve the face recognition page"""
        return FileResponse(os.path.join("static", "face_reg.html"))

    @app.get("/admin", response_class=FileResponse)
    async def serve_admin():
        """Serve the admin page"""
        return FileResponse(os.path.join("static", "admin.html"))

    @app.get("/report", response_class=FileResponse)
    async def report():
        return FileResponse(os.path.join("static", "report.html"))  

    @app.get("/batches", summary="Get available batch years and departments")
    async def get_batches():
        """Get available batch years and departments."""
        years = database.get_batch_years()
        departments = database.get_departments()
        print(f"DEBUG: Years: {years}")
        print(f"DEBUG: Departments: {departments}")
        return {
            "years": years,
            "departments": departments
        }

    @app.get("/galleries", summary="Get all available galleries")
    async def list_galleries():
        """List all available face recognition galleries"""
        
        if not os.path.exists(BASE_GALLERY_DIR):
            print(f"DEBUG: Gallery directory does not exist: {BASE_GALLERY_DIR}")
            return {"galleries": []}
        
        # Find all gallery files
        galleries = []
        all_files = os.listdir(BASE_GALLERY_DIR)
        print(f"DEBUG: All files in {BASE_GALLERY_DIR}: {all_files}")
        
        for file in all_files:
            if file.endswith(".pth"):
                galleries.append(file)
                print(f"DEBUG: Found gallery file: {file}")
        
        print(f"DEBUG: Returning galleries: {galleries}")
        return {"galleries": galleries}

    @app.get("/galleries/{year}/{department}", response_model=Optional[GalleryInfo], 
             summary="Get information about a specific gallery")
    async def get_gallery(year: str, department: str):
        gallery_path = get_gallery_path(year, department)
        gallery_info = get_gallery_info(gallery_path)
        
        if gallery_info is None:
            raise HTTPException(status_code=404, 
                               detail=f"No gallery found for {department} {year} batch")
        
        return gallery_info

    @app.post("/process", response_model=ProcessingResult, 
              summary="Process videos to extract frames and detect faces")
    async def process_videos(
        year: str = Form(...),
        department: str = Form(...),
        videos_dir: str = Form(...)
    ):
        """
        Process videos to extract faces and store them in the dataset
        
        Parameters:
        - year: Batch year (e.g., "1st", "2nd")
        - department: Department name (e.g., "CS", "IT")
        - videos_dir: Path to directory containing student videos
        """
        # Validation code remains the same
        if year not in database.get_batch_years():
            raise HTTPException(status_code=400, detail=f"Invalid batch year: {year}")
        if department not in database.get_department_ids():  # use department IDs instead of names
            raise HTTPException(status_code=400, detail=f"Invalid department: {department}")
        
        if not os.path.exists(videos_dir):
            raise HTTPException(status_code=400, detail=f"Directory not found: {videos_dir}")
        
        # Get data path
        data_path = get_data_path(year, department)
        os.makedirs(data_path, exist_ok=True)
        
        # Find video files
        video_files = []
        for file in os.listdir(videos_dir):
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_path = os.path.join(videos_dir, file)
                student_name = os.path.splitext(file)[0]
                video_files.append((video_path, student_name))
        
        if not video_files:
            raise HTTPException(status_code=400, detail="No video files found in the specified directory")
        
        # Process each video - ONLY extract frames and faces
        processed_videos = 0
        processed_frames = 0
        extracted_faces = 0
        failed_videos = []
        
        for video_path, student_name in video_files:
            try:
                print(f"Processing video: {video_path}")
                
                # Create student directory
                student_dir = os.path.join(data_path, student_name)
                os.makedirs(student_dir, exist_ok=True)
                
                # Extract frames temporarily for face detection
                temp_frames_dir = os.path.join(student_dir, "temp_frames")
                frame_paths = extract_frames(video_path, temp_frames_dir, max_frames=20, interval=5)
                print(f"Extracted {len(frame_paths)} frames")
                processed_frames += len(frame_paths)
                
                # Extract faces from frames
                video_faces = 0
                for frame_path in frame_paths:
                    face_paths = detect_and_crop_faces(frame_path, student_dir)
                    video_faces += len(face_paths)
                    
                # Clean up temp frames
                shutil.rmtree(temp_frames_dir, ignore_errors=True)
                
                extracted_faces += video_faces
                processed_videos += 1
                print(f"Extracted {video_faces} faces for {student_name}")
                
            except Exception as e:
                print(f"Error processing {video_path}: {e}")
                failed_videos.append(f"{student_name}: {str(e)}")
        
        # Determine gallery path and attempt creation
        gallery_path = get_gallery_path(year, department)
        gallery_updated = False
        
        try:
            # Create or update gallery using the extracted faces
            if os.path.exists(gallery_path):
                update_gallery(DEFAULT_MODEL_PATH, gallery_path, data_path, gallery_path)
            else:
                create_gallery(DEFAULT_MODEL_PATH, data_path, gallery_path)
            
            # Register gallery in database
            database.register_gallery(year, department, gallery_path)
            gallery_updated = True
            
        except Exception as e:
            print(f"Error creating/updating gallery: {e}")
        
        return ProcessingResult(
            processed_videos=processed_videos,
            processed_frames=processed_frames,
            extracted_faces=extracted_faces,
            failed_videos=failed_videos,
            gallery_updated=gallery_updated,
            gallery_path=gallery_path
        )

    @app.post("/galleries/create", 
              summary="Create a gallery from extracted face data")
    async def create_gallery_endpoint(
        year: str = Form(...),
        department: str = Form(...),
        augment_ratio: float = Form(0.0),
        augs_per_image: int = Form(3)
    ):
        """Create a gallery for face recognition from extracted face data"""
        # Use department name for folder search, not department_id
        dept_info = database.get_department_by_name_or_id(department)
        if dept_info:
            department_name = dept_info["name"]
            department_id = dept_info["department_id"]
            print(f"Found department: ID={department_id}, Name={department_name}")
        else:
            # Try directly as department name
            department_name = department
            dept_info = database.get_department_by_name_or_id(department_name)
            if not dept_info:
                raise HTTPException(status_code=400, detail=f"Invalid department: {department}")
            department_id = dept_info["department_id"]

        # Validate inputs
        if year not in database.get_batch_years():
            raise HTTPException(status_code=400, detail=f"Invalid batch year: {year}")

        # Use the standardized path functions
        data_path = get_data_path(year, department_id)
        gallery_path = get_gallery_path(year, department_id)

        print(f"Looking for data in: {data_path}")
        print(f"Gallery will be created at: {gallery_path}")

        if not os.path.exists(data_path):
            raise HTTPException(status_code=400, detail=f"No face data found for {department_name} (ID: {department_id}) {year}. Please process videos first. Expected path: {data_path}")

        try:
            # Create gallery
            gallery = create_gallery(DEFAULT_MODEL_PATH, data_path, gallery_path, augment_ratio, augs_per_image)
            # Register in database
            identity_count = len(gallery) if gallery else 0
            database.register_gallery(year, department_id, gallery_path, identity_count)
            return {
                "success": True,
                "message": f"Gallery created successfully for {department_name} {year}",
                "gallery_path": gallery_path,
                "identities": identity_count,
                "identities_count": identity_count  # For frontend compatibility
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating gallery: {str(e)}")

    @app.post("/batches/year", status_code=201, summary="Add a new batch year")
    async def add_batch_year(year_data: dict):
        year = year_data.get("year")
        if not year:
            raise HTTPException(status_code=400, detail="Year is required")
        
        success = database.add_batch_year(year)
        if not success:
            raise HTTPException(status_code=400, detail=f"Batch year '{year}' already exists")
        
        return {"message": f"Added batch year: {year}", "success": True}

    @app.delete("/batches/year/{year}", status_code=200, summary="Delete a batch year")
    async def delete_batch_year(year: str):
        # Check if any galleries are using this year in the database
        galleries = database.list_all_galleries()
        year_galleries = [g for g in galleries if g['year'] == year]
        
        if year_galleries:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete year '{year}' as it is used by {len(year_galleries)} galleries"
            )
        
        if year not in database.get_batch_years():
            raise HTTPException(status_code=404, detail=f"Batch year '{year}' not found")
        
        success = database.delete_batch_year(year)
        if not success:
            raise HTTPException(status_code=404, detail=f"Batch year '{year}' not found")
        
        return {"message": f"Deleted batch year: {year}", "success": True}

    @app.post("/batches/department", status_code=201, summary="Add a new department")
    async def add_department(dept_data: dict):
        print(f"DEBUG: Received department data: {dept_data}")
        department_id = dept_data.get("department_id")
        department_name = dept_data.get("department")
        
        print(f"DEBUG: Extracted department_id: {department_id}")
        print(f"DEBUG: Extracted department_name: {department_name}")
        
        if not department_id or not department_name:
            print(f"DEBUG: Validation failed - department_id: {department_id}, department_name: {department_name}")
            raise HTTPException(status_code=400, detail="Both department_id and department name are required")
        
        success = database.add_department(department_id, department_name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Department ID '{department_id}' or name '{department_name}' already exists")
        
        return {"message": f"Added department: {department_name} (ID: {department_id})", "success": True}

    @app.delete("/batches/department/{department_id}", status_code=200, summary="Delete a department")
    async def delete_department(department_id: str):
        # Check if any galleries are using this department in the database
        galleries = database.list_all_galleries()
        dept_galleries = [g for g in galleries if g['department_id'] == department_id]
        
        if dept_galleries:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete department '{department_id}' as it is used by {len(dept_galleries)} galleries"
            )
        
        # Check if department exists
        dept_info = database.get_department_by_id(department_id)
        if not dept_info:
            raise HTTPException(status_code=404, detail=f"Department with ID '{department_id}' not found")
        
        success = database.delete_department(department_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Department with ID '{department_id}' not found")
        
        return {"message": f"Deleted department: {dept_info['name']} (ID: {department_id})", "success": True}

    @app.get("/check-directories", summary="Check if directories exist and are accessible")
    async def check_directories():
        """Debug endpoint to check if directories exist and are accessible"""
        data_dir_exists = os.path.exists(BASE_DATA_DIR)
        gallery_dir_exists = os.path.exists(BASE_GALLERY_DIR)
        
        data_dir_files = []
        gallery_dir_files = []
        
        try:
            if data_dir_exists:
                data_dir_files = os.listdir(BASE_DATA_DIR)
        except Exception as e:
            data_dir_files = [f"Error: {str(e)}"]
        
        try:
            if gallery_dir_exists:
                gallery_dir_files = os.listdir(BASE_GALLERY_DIR)
        except Exception as e:
            gallery_dir_files = [f"Error: {str(e)}"]
        
        return {
            "data_dir_exists": data_dir_exists,
            "gallery_dir_exists": gallery_dir_exists,
            "data_dir_path": BASE_DATA_DIR,
            "gallery_dir_path": BASE_GALLERY_DIR,
            "data_dir_files": data_dir_files,
            "gallery_dir_files": gallery_dir_files
        }

    @app.get("/galleries/registered", summary="Get all registered galleries from database")
    async def list_registered_galleries():
        """List all galleries registered in the database with their metadata"""
        galleries = database.list_all_galleries()
        return {
            "galleries": galleries,
            "count": len(galleries)
        }

    @app.get("/database/stats", summary="Get database statistics")
    async def get_database_stats():
        """Get comprehensive database statistics"""
        return database.get_database_stats()

    @app.delete("/galleries/{year}/{department}", status_code=200, summary="Delete a gallery")
    async def delete_gallery(year: str, department: str):
        """Delete a gallery file and remove it from the database"""
        # Validate batch year and department
        if year not in database.get_batch_years():
            raise HTTPException(status_code=400, detail=f"Invalid batch year: {year}")
        if department not in database.get_department_ids():  # use department IDs instead of names
            raise HTTPException(status_code=400, detail=f"Invalid department: {department}")
        
        # Get gallery path
        gallery_path = get_gallery_path(year, department)
        
        # Check if gallery exists
        if not os.path.exists(gallery_path):
            raise HTTPException(status_code=404, detail=f"No gallery found for {department} {year}")
        
        try:
            # Remove gallery file
            os.remove(gallery_path)
            
            # Remove from database
            database.remove_gallery(year, department)
            
            return {
                "message": f"Deleted gallery for {department} {year}",
                "success": True
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete gallery: {str(e)}")

    @app.post("/galleries/{year}/{department}/sync", summary="Sync gallery file with database")
    async def sync_gallery_with_database(year: str, department: str):
        """Sync an existing gallery file with the database"""
        # Validate batch year and department
        if year not in database.get_batch_years():
            raise HTTPException(status_code=400, detail=f"Invalid batch year: {year}")
        if department not in database.get_department_ids():  # use department IDs instead of names
            raise HTTPException(status_code=400, detail=f"Invalid department: {department}")
        
        # Get gallery path
        gallery_path = get_gallery_path(year, department)
        
        # Check if gallery exists
        if not os.path.exists(gallery_path):
            raise HTTPException(status_code=404, detail=f"No gallery found for {department} {year}")
        
        try:
            # Get gallery info
            gallery_info = get_gallery_info(gallery_path)
            if not gallery_info:
                raise HTTPException(status_code=500, detail="Failed to read gallery file")
            
            # Register/update in database
            success = database.register_gallery(year, department, gallery_path, gallery_info.count)
            
            if success:
                return {
                    "message": f"Successfully synced gallery for {department} {year}",
                    "identities_count": gallery_info.count,
                    "success": True
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to register gallery in database")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to sync gallery: {str(e)}")

    @app.post("/recognize", summary="Recognize faces in an uploaded image")
    async def recognize_image(
        image: UploadFile = File(...),
        galleries: List[str] = Form(...),
        threshold: float = Form(0.45)
    ):
        """Recognize faces in an uploaded image using selected galleries"""
        try:
            # Read the image
            contents = await image.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise HTTPException(status_code=400, detail="Invalid image file")
            
            # Process galleries
            gallery_paths = []
            for gallery_name in galleries:
                gallery_path = os.path.join(BASE_GALLERY_DIR, gallery_name)
                if os.path.exists(gallery_path):
                    gallery_paths.append(gallery_path)
            
            if not gallery_paths:
                raise HTTPException(status_code=400, detail="No valid galleries found")
            
            # Recognize faces
            try:
                result_img, detected_faces = recognize_faces(
                    img, gallery_paths, DEFAULT_MODEL_PATH, DEFAULT_YOLO_PATH, threshold
                )
                
                # Ensure detected_faces is a list
                if detected_faces is None:
                    detected_faces = []
                    
                # Convert result image to base64
                _, buffer = cv2.imencode('.jpg', result_img)
                result_base64 = base64.b64encode(buffer).decode('utf-8')
            except Exception as face_error:
                print(f"Error in face recognition: {face_error}")
                # Return the original image if face recognition fails
                _, buffer = cv2.imencode('.jpg', img)
                result_base64 = base64.b64encode(buffer).decode('utf-8')
                detected_faces = []
            
            return {
                "success": True,
                "result_image": f"data:image/jpeg;base64,{result_base64}",
                "detected_faces": detected_faces,
                "total_faces": len(detected_faces),
                "galleries_used": galleries,
                "threshold": threshold
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Recognition failed: {str(e)}")

    # Collection app routes
    @app.post("/api/start-collection-app", summary="Start the face collection application")
    async def start_collection_app_route():
        """Start the face collection application server using the launch script"""
        return start_collection_app()

    @app.post("/api/stop-collection-app", summary="Stop the face collection application")
    async def stop_collection_app_route():
        """Stop the face collection application server using PM2"""
        return stop_collection_app()

    @app.get("/api/collection-app-status", summary="Check face collection app status")
    async def get_collection_app_status_route():
        """Check if the face collection application is running using PM2"""
        return get_collection_app_status()

    @app.get("/api/collection-app-config", summary="Get face collection app configuration")
    async def get_collection_app_config_route():
        return get_collection_app_config()

    # Student data routes
    @app.get("/student-data/folders", summary="Get available student data folders (dept_year)")
    async def get_available_folders():
        """Get all available department-year folders from student data"""
        folders = get_student_data_folders()
        return {"folders": folders}

    @app.get("/student-data/total-stats", summary="Get total statistics across all student data")
    async def get_total_student_stats():
        """Get aggregated statistics for all students across all departments and years"""
        try:
            folders = get_student_data_folders()
            total_stats = {
                "total_students": 0,
                "total_videos_uploaded": 0,
                "total_processed": 0,
                "total_pending": 0,
                "folders_count": len(folders),
                "departments": set(),
                "years": set()
            }
            
            for folder_info in folders:
                try:
                    dept = folder_info["dept"]
                    year = folder_info["year"]
                    
                    # Add to unique sets
                    total_stats["departments"].add(dept)
                    total_stats["years"].add(year)
                    
                    # Get summary for this folder
                    summary = get_student_data_summary(dept, year)
                    total_stats["total_students"] += summary.total_students
                    total_stats["total_videos_uploaded"] += summary.students_with_video
                    total_stats["total_processed"] += summary.students_processed
                    total_stats["total_pending"] += summary.students_pending
                    
                except Exception as e:
                    print(f"Error getting stats for {folder_info}: {e}")
                    continue
            
            # Convert sets to lists for JSON serialization
            total_stats["departments"] = list(total_stats["departments"])
            total_stats["years"] = list(total_stats["years"])
            
            return {
                "success": True,
                "data": total_stats
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calculating total stats: {str(e)}")

    @app.get("/student-data/department-stats", summary="Get department-wise student statistics")
    async def get_department_wise_stats(batch: Optional[str] = Query(None, description="Filter by specific batch year")):
        """Get aggregated statistics for each department across all years or filtered by batch"""
        try:
            # Get all departments from database
            departments = database.get_departments()
            
            # Get all student data folders
            folders = get_student_data_folders()
            
            # Filter folders by batch if specified
            if batch:
                folders = [f for f in folders if str(f["year"]) == str(batch)]
            
            # Create department statistics dict - Initialize ALL departments from database
            dept_stats = {}
            
            # Initialize ALL departments from database with zero counts
            for dept in departments:
                dept_id = dept["id"]
                dept_name = dept["name"]
                dept_stats[dept_id] = {
                    "department_id": dept_id,
                    "department_name": dept_name,
                    "total_students": 0,
                    "total_videos_uploaded": 0,
                    "total_processed": 0,
                    "years": []
                }
            
            # Aggregate data from student folders for departments that have data
            for folder_info in folders:
                try:
                    dept_id = folder_info["dept"]
                    year = folder_info["year"]
                    
                    # Get summary for this folder
                    summary = get_student_data_summary(dept_id, year)
                    
                    # Add to department stats if department exists in our initialized list
                    if dept_id in dept_stats:
                        dept_stats[dept_id]["total_students"] += summary.total_students
                        dept_stats[dept_id]["total_videos_uploaded"] += summary.students_with_video
                        dept_stats[dept_id]["total_processed"] += summary.students_processed
                        if year not in dept_stats[dept_id]["years"]:
                            dept_stats[dept_id]["years"].append(year)
                    else:
                        # Handle departments not in database but have data folders (fallback)
                        dept_stats[dept_id] = {
                            "department_id": dept_id,
                            "department_name": f"Department {dept_id}",
                            "total_students": summary.total_students,
                            "total_videos_uploaded": summary.students_with_video,
                            "total_processed": summary.students_processed,
                            "years": [year]
                        }
                        
                except Exception as e:
                    print(f"Error getting stats for {folder_info}: {e}")
                    continue
            
            # Convert to list and sort by department name
            # Always show ALL departments from database, regardless of having data or not
            department_list = list(dept_stats.values())
            department_list.sort(key=lambda x: x["department_name"])
            
            filter_info = f" for batch {batch}" if batch else " (all batches)"
            
            return {
                "success": True,
                "data": {
                    "departments": department_list,
                    "total_departments": len(department_list),
                    "filter_applied": batch,
                    "filter_description": f"Department statistics{filter_info}",
                    "note": "Showing all departments from database, including those with no student data"
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calculating department stats: {str(e)}")

    @app.get("/student-data/{dept}/{year}/summary", 
             response_model=StudentDataSummary,
             summary="Get summary of students in a department-year")
    async def get_student_summary(dept: str, year: str):
        """Get summary statistics for students in a specific department and year"""
        return get_student_data_summary(dept, year)

    @app.get("/student-data/{dept}/{year}/students", 
             summary="Get list of students in a department-year")
    async def get_students_list(dept: str, year: str):
        """Get detailed list of all students in a specific department and year"""
        students = get_students_in_folder(dept, year)
        return {"students": [student.dict() for student in students]}

    @app.get("/student-data/{dept}/{year}/pending", 
             summary="Get students pending processing")
    async def get_pending_students(dept: str, year: str):
        """Get list of students who have uploaded videos but haven't been processed yet"""
        students = get_students_in_folder(dept, year)
        pending = [s for s in students if s.videoUploaded and not s.facesExtracted]
        return {"pending_students": [student.dict() for student in pending]}

    @app.post("/student-data/{dept}/{year}/quality-check", 
              summary="Check quality of student videos")
    async def check_student_data_quality(dept: str, year: str):
        """Check quality of all student videos in a department-year before processing"""
        try:
            quality_checker = get_quality_checker()
            result = quality_checker.check_student_data_quality(dept, year, STUDENT_DATA_DIR)
            
            if 'error' in result:
                raise HTTPException(status_code=404, detail=result['error'])
            
            return {
                "success": True,
                "message": f"Quality check completed for {dept} {year}",
                "passed_students": result['passed_students'],
                "failed_students": result['failed_students'],
                "borderline_students": result['borderline_students'],
                "total_checked": result['total_checked'],
                "pass_rate": len(result['passed_students']) / result['total_checked'] * 100 if result['total_checked'] > 0 else 0
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error checking quality: {str(e)}")

    @app.delete("/student-data/{dept}/{year}/failed-quality", 
               summary="Delete student data that failed quality check")
    async def delete_failed_quality_data(dept: str, year: str):
        """Delete student data that failed quality check"""
        try:
            result = delete_students_by_quality(dept, year, "fail")
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=404, detail=result["error"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting failed data: {str(e)}")

    @app.post("/student-data/{dept}/{year}/process-borderline", 
              summary="Process borderline quality students")
    async def process_borderline_students_route(dept: str, year: str):
        """Process students who were marked as borderline quality"""
        try:
            result = process_borderline_students(dept, year)
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=404, detail=result["error"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing borderline students: {str(e)}")

    @app.delete("/student-data/{dept}/{year}/delete-borderline", 
               summary="Delete borderline quality students")
    async def delete_borderline_students(dept: str, year: str):
        """Delete students who were marked as borderline quality"""
        try:
            result = delete_students_by_quality(dept, year, "borderline")
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=404, detail=result["error"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting borderline students: {str(e)}")

    @app.post("/student-data/{dept}/{year}/process", 
              summary="Process students' videos to extract faces")
    async def process_students_videos_route(dept: str, year: str):
        """Process all pending students' videos in a department-year to extract faces"""
        try:
            result = process_students_videos(dept, year)
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing students: {str(e)}")

    @app.get("/student-list/{dept}/{year}")
    async def get_students_by_department_year(dept: str, year: str):
        """Get list of students in a specific department and year"""
        students = get_students_by_dept_and_batch(dept, year)
        return students
    
    # Admin authentication routes
    @app.post('/api/login')
    async def login(data: dict):
        """User login endpoint"""
        username = data.get('username')
        password = data.get('password')
        return authenticate_user(username, password)

    @app.post('/api/add-admin')
    async def add_admin(data: dict):
        """Add a new admin user"""
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'admin')
        return add_admin_user(username, password, role)

    @app.delete('/api/admins/{username}')
    async def delete_admin(username: str):
        """Delete an admin user"""
        return delete_admin_user(username)

    @app.get('/api/admins')
    async def list_admins():
        """List all admin and superadmin users"""
        return list_admin_users()

    # Quality check report routes
    @app.get("/api/quality-reports", summary="Get all quality check reports")
    async def get_reports(
        department: Optional[str] = Query(None),
        year: Optional[str] = Query(None)
    ):
        """Get all quality check reports, optionally filtered by department and year."""
        reports = database.get_quality_check_reports(department, year)
        return {"reports": reports}

    @app.get("/api/quality-reports/{report_id}", summary="Get a specific quality check report")
    async def get_report_details(report_id: int):
        """Get detailed information for a single quality check report."""
        report_details = database.get_quality_check_report_details(report_id)
        if not report_details:
            raise HTTPException(status_code=404, detail="Report not found")
        return report_details

    @app.get("/student-data/{dept}/{year}/quality-results", 
             summary="Get existing quality check results")
    async def get_existing_quality_results(dept: str, year: str):
        """Get existing quality check results for students in a department-year"""
        try:
            students = get_students_in_folder(dept, year)
            
            passed_students = []
            failed_students = []
            borderline_students = []
            total_with_quality = 0
            
            for student in students:
                if hasattr(student, 'qualityCheck') and student.qualityCheck:
                    total_with_quality += 1
                    
                    if hasattr(student, 'qualityCategory'):
                        category = student.qualityCategory
                    elif student.qualityCheck == 'pass':
                        category = 'pass'
                    else:
                        category = 'fail'
                    
                    if category == 'pass':
                        passed_students.append(student.regNo)
                    elif category == 'borderline':
                        issues = getattr(student, 'qualityIssues', [])
                        borderline_students.append({
                            'regNo': student.regNo,
                            'issues': issues
                        })
                    else:  # fail
                        failed_students.append(student.regNo)
            
            if total_with_quality == 0:
                return {
                    "success": False,
                    "message": "No quality check results found",
                    "has_results": False
                }
            
            return {
                "success": True,
                "message": f"Found quality results for {total_with_quality} students",
                "has_results": True,
                "passed_students": passed_students,
                "failed_students": failed_students,
                "borderline_students": borderline_students,
                "total_checked": total_with_quality,
                "pass_rate": len(passed_students) / total_with_quality * 100 if total_with_quality > 0 else 0
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting quality results: {str(e)}")

    return app
