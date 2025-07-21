import os
import json
import shutil
import gc
from typing import List, Dict, Any
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from models.pydantic_models import StudentInfo, StudentDataSummary
from services.face_processing import extract_frames, detect_and_crop_faces
from config.settings import STUDENT_DATA_DIR, BASE_DATA_DIR

def get_student_data_folders():
    """Get all department-year folders from student data directory"""
    folders = []
    if os.path.exists(STUDENT_DATA_DIR):
        for folder in os.listdir(STUDENT_DATA_DIR):
            folder_path = os.path.join(STUDENT_DATA_DIR, folder)
            if os.path.isdir(folder_path) and "_" in folder:
                dept, year = folder.split("_", 1)
                folders.append({"folder": folder, "dept": dept, "year": year})
    return folders

def get_students_in_folder(dept: str, year: str) -> List[StudentInfo]:
    """Get all students in a specific department-year folder"""
    students = []
    folder_path = os.path.join(STUDENT_DATA_DIR, f"{dept}_{year}")
    
    if os.path.exists(folder_path):
        for student_folder in os.listdir(folder_path):
            student_path = os.path.join(folder_path, student_folder)
            if os.path.isdir(student_path):
                # Look for student JSON file
                json_file = os.path.join(student_path, f"{student_folder}.json")
                if os.path.exists(json_file):
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                            
                            # Handle missing required fields
                            if 'regNo' not in data:
                                data['regNo'] = student_folder
                                
                            if 'name' not in data:
                                data['name'] = f"Student {student_folder}"
                                
                            if 'sessionId' not in data:
                                data['sessionId'] = f"session_{student_folder}"
                                
                            if 'year' not in data:
                                data['year'] = year
                                
                            if 'dept' not in data:
                                # If dept is missing, we need to get the department name
                                # For now, use the dept parameter (which is dept_id) as fallback
                                data['dept'] = dept
                                
                            if 'dept_id' not in data:
                                # The dept parameter passed to this function is actually the dept_id from the URL
                                data['dept_id'] = dept
                                
                            if 'batch' not in data:
                                data['batch'] = f"{dept}_{year}"
                                
                            if 'startTime' not in data:
                                data['startTime'] = ""
                                
                            if 'videoUploaded' not in data:
                                data['videoUploaded'] = os.path.exists(os.path.join(student_path, f"{student_folder}.mp4"))
                                
                            if 'facesExtracted' not in data:
                                data['facesExtracted'] = False
                                
                            if 'facesOrganized' not in data:
                                data['facesOrganized'] = False
                                
                            if 'videoPath' not in data:
                                data['videoPath'] = os.path.join(student_path, f"{student_folder}.mp4")
                                
                            if 'facesCount' not in data:
                                data['facesCount'] = 0
                                
                            if 'qualityCheck' not in data:
                                data['qualityCheck'] = 'not_tested'
                            
                            # Try to create the StudentInfo object with the fixed data
                            students.append(StudentInfo(**data))
                            
                            # If we had to fix the JSON, save it back to the file
                            if any(k not in data for k in ['name', 'regNo', 'sessionId', 'year', 'dept', 'dept_id', 'batch', 'qualityCheck']):
                                with open(json_file, 'w') as f:
                                    json.dump(data, f, indent=2)
                                    
                    except Exception as e:
                        print(f"Error reading student data {json_file}: {e}")
    
    return students

def get_student_data_summary(dept: str, year: str) -> StudentDataSummary:
    """Get summary statistics for students in a department-year"""
    students = get_students_in_folder(dept, year)
    
    total = len(students)
    with_video = sum(1 for s in students if s.videoUploaded)
    without_video = total - with_video
    processed = sum(1 for s in students if s.facesExtracted)
    pending = with_video - processed
    
    return StudentDataSummary(
        total_students=total,
        students_with_video=with_video,
        students_without_video=without_video,
        students_processed=processed,
        students_pending=pending,
        department=dept,
        year=year
    )

def process_student_video(student: StudentInfo) -> Dict[str, Any]:
    try:
        print(f"Starting video processing for student: {student.regNo}")
        # Remove psutil for environments where it's not available
        # Source paths (where video is stored)
        # Use dept_id for folder structure since folders are named with department ID
        dept_folder = getattr(student, 'dept_id', student.dept)  # Fallback to dept if dept_id not available
        student_source_folder = os.path.join(STUDENT_DATA_DIR, f"{dept_folder}_{student.year}", student.regNo)
        video_path = os.path.join(student_source_folder, f"{student.regNo}.mp4")
        
        print(f"Student dept: {student.dept}, dept_id: {getattr(student, 'dept_id', 'Not set')}")
        print(f"Using department folder: {dept_folder}")
        print(f"Looking for video at: {video_path}")
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return {"success": False, "error": f"Video file not found: {video_path}"}
        
        # Destination paths (gallery data structure)
        gallery_data_dir = os.path.join(BASE_DATA_DIR, f"{dept_folder}_{student.year}")
        student_gallery_folder = os.path.join(gallery_data_dir, student.regNo)
        
        # Create gallery data directory structure
        os.makedirs(student_gallery_folder, exist_ok=True)
        
        # Create temporary frames directory for processing
        temp_frames_dir = os.path.join(student_source_folder, "temp_frames")
        os.makedirs(temp_frames_dir, exist_ok=True)
        
        # Extract frames from video
        print(f"Extracting frames from {video_path} to {temp_frames_dir}")
        frame_paths = extract_frames(video_path, temp_frames_dir)
        print(f"Extracted {len(frame_paths)} frames")
        
        if not frame_paths:
            print(f"No frames extracted from video: {video_path}")
            return {"success": False, "error": f"No frames could be extracted from video: {video_path}"}
        
        # Process each frame to extract faces and save them in gallery structure
        all_face_paths = []
        print(f"Processing {len(frame_paths)} frames for face detection")
        for i, frame_path in enumerate(frame_paths):
            print(f"Processing frame {i+1}/{len(frame_paths)}: {frame_path}")
            face_paths = detect_and_crop_faces(frame_path, student_gallery_folder)
            print(f"Found {len(face_paths)} faces in frame {i+1}")
            all_face_paths.extend(face_paths)
            # Memory cleanup after each frame
            del face_paths
            gc.collect()
        faces_count = len(all_face_paths)  # <-- define before deleting
        print(f"Total faces extracted for {student.regNo}: {faces_count}")
        
        # Clean up temporary frames directory
        try:
            for frame_path in frame_paths:
                if os.path.exists(frame_path):
                    os.remove(frame_path)
            if os.path.exists(temp_frames_dir):
                os.rmdir(temp_frames_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temporary frames: {e}")
        
        # Update student JSON file (only one JSON file per student)
        json_file = os.path.join(student_source_folder, f"{student.regNo}.json")
        try:
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    student_data = json.load(f)
            else:
                student_data = student.dict()

            # Ensure all required fields for StudentInfo are present
            required_fields = [
                "sessionId", "regNo", "name", "year", "dept", "batch", "startTime",
                "videoUploaded", "facesExtracted", "facesOrganized", "videoPath", "facesCount"
            ]
            for field in required_fields:
                if field not in student_data:
                    student_data[field] = getattr(student, field, None)

            # Update processing status
            student_data["facesExtracted"] = True
            student_data["facesOrganized"] = True
            student_data["facesCount"] = len(all_face_paths)

            # Save updated JSON file
            with open(json_file, 'w') as f:
                json.dump(student_data, f, indent=2)
        except Exception as e:
            print(f"Error updating student JSON file: {e}")
            return {"success": False, "error": f"Error updating student JSON file: {e}"}
        
        # Memory cleanup after each student
        del all_face_paths
        gc.collect()
        return {
            "success": True, 
            "faces_extracted": faces_count,
            "frames_processed": len(frame_paths),
            "gallery_path": student_gallery_folder
        }
    except MemoryError as e:
        print(f"MemoryError processing student {student.regNo}: {e}")
        return {"success": False, "error": f"MemoryError: {str(e)}"}
    except Exception as e:
        print(f"Exception processing student {getattr(student, 'regNo', 'unknown')}: {e}")
        return {"success": False, "error": str(e)}

def delete_students_by_quality(dept: str, year: str, quality_category: str) -> Dict[str, Any]:
    """Delete students based on quality category"""
    try:
        dept_year_dir = os.path.join(STUDENT_DATA_DIR, f"{dept}_{year}")
        
        if not os.path.exists(dept_year_dir):
            return {"success": False, "error": f"Directory not found: {dept_year_dir}"}
        
        deleted_students = []
        
        # Process each student directory
        for student_id in os.listdir(dept_year_dir):
            student_path = os.path.join(dept_year_dir, student_id)
            
            if not os.path.isdir(student_path):
                continue
            
            json_path = os.path.join(student_path, f"{student_id}.json")
            
            if not os.path.exists(json_path):
                continue
            
            try:
                with open(json_path, 'r') as f:
                    student_data = json.load(f)
                
                # Check if student matches the quality category
                if student_data.get('qualityCategory') == quality_category:
                    # Delete the entire student directory
                    shutil.rmtree(student_path)
                    deleted_students.append(student_id)
                    
            except Exception as e:
                print(f"Error processing student {student_id}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"Deleted {len(deleted_students)} students with {quality_category} quality",
            "deleted_students": deleted_students
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error deleting {quality_category} data: {str(e)}"}

def process_borderline_students(dept: str, year: str) -> Dict[str, Any]:
    """Process students who were marked as borderline quality"""
    try:
        dept_year_dir = os.path.join(STUDENT_DATA_DIR, f"{dept}_{year}")
        
        if not os.path.exists(dept_year_dir):
            return {"success": False, "error": f"Directory not found: {dept_year_dir}"}
        
        processed_students = []
        
        # Process each student directory
        for student_id in os.listdir(dept_year_dir):
            student_path = os.path.join(dept_year_dir, student_id)
            
            if not os.path.isdir(student_path):
                continue
            
            json_path = os.path.join(student_path, f"{student_id}.json")
            
            if not os.path.exists(json_path):
                continue
            
            try:
                with open(json_path, 'r') as f:
                    student_data = json.load(f)
                
                # Check if student is borderline and update to pass
                if student_data.get('qualityCategory') == 'borderline':
                    student_data['qualityCheck'] = 'pass'
                    student_data['qualityCategory'] = 'pass'
                    
                    # Save updated JSON
                    with open(json_path, 'w') as f:
                        json.dump(student_data, f, indent=2)
                    
                    processed_students.append(student_id)
                    
            except Exception as e:
                print(f"Error processing student {student_id}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"Processed {len(processed_students)} borderline students",
            "processed_students": processed_students
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error processing borderline students: {str(e)}"}

def process_students_videos(dept: str, year: str) -> Dict[str, Any]:
    """Process all pending students' videos in a department-year to extract faces"""
    try:
        # Remove psutil for environments where it's not available
        # ...existing code...
        students = get_students_in_folder(dept, year)
        print(f"Total students found: {len(students)}")
        
        pending_students = [s for s in students if s.videoUploaded and not s.facesExtracted]
        print(f"Students with video uploaded and not yet processed: {len(pending_students)}")
        
        # Allow processing of students who either passed quality check OR haven't been tested yet
        # This allows direct processing without requiring quality check first
        quality_passed_students = [s for s in pending_students if getattr(s, 'qualityCheck', 'not_tested') in ["pass", "not_tested"]]
        print(f"Students eligible for processing (passed quality or not tested): {len(quality_passed_students)}")
        
        if not quality_passed_students:
            return {
                "success": True,
                "message": "No students available for processing. All students may have failed quality check or already been processed.",
                "processed_count": 0
            }
        results = []
        processed_count = 0
        processed_students = []  # Define a list to track successfully processed students
        for student in quality_passed_students:
            print(f"Processing student: {student.regNo} - {student.name}")
            try:
                result = process_student_video(student)
                print(f"Processing result for {student.regNo}: {result}")
            except Exception as e:
                print(f"Exception in process_student_video for {student.regNo}: {e}")
                result = {"success": False, "error": str(e)}
            results.append({
                "student": student.regNo,
                "name": student.name,
                "result": result
            })
            if result["success"]:
                processed_count += 1
                processed_students.append(student)  # Add successfully processed students to the list
        return {
            "success": True,
            "message": f"Processed {processed_count} out of {len(quality_passed_students)} quality-passed students",
            "processed_count": processed_count,
            "total_pending": len(quality_passed_students),
            "processedCount": processed_count,  # Adding this property for frontend compatibility
            "totalPending": len(quality_passed_students),  # Adding this property for frontend compatibility
            "details": results,
            "students": [student.dict() for student in processed_students]  # Add student info for display
        }
    except MemoryError as e:
        print(f"MemoryError in batch: {e}")
        return {"success": False, "error": f"MemoryError: {str(e)}"}
    except Exception as e:
        print(f"Exception in batch: {e}")
        return {"success": False, "error": f"Error processing students: {str(e)}"}
