import os
import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, List, Tuple, Any
import json
from pathlib import Path
from database.models import save_quality_check_report

class VideoQualityChecker:
    def __init__(self, yolo_model_path: str):
        """Initialize the quality checker with YOLO model for face detection"""
        self.yolo_model = YOLO(yolo_model_path)
        self.quality_thresholds = {
            'min_faces_detected': 5,  # Minimum faces across all sampled frames
            'max_faces_per_frame': 1,  # Maximum faces per frame (to avoid multiple people)
            'min_blur_score': 50,  # Minimum blur score (generous threshold)
            'min_contrast': 20,  # Minimum contrast (generous threshold)
            'min_face_angles': 1,  # Minimum different face angles/poses
            'min_face_size': 60,  # Minimum face size (pixels)
            'max_motion_blur': 80,  # Maximum motion blur threshold (generous)
        }
    
    def sample_frames(self, video_path: str, num_samples: int = 15) -> List[np.ndarray]:
        """Sample 15 frames from different points in the video"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < num_samples:
            num_samples = total_frames
        
        # Sample frames at regular intervals across the timeline
        frame_indices = np.linspace(0, total_frames - 1, num_samples, dtype=int)
        frames = []
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        
        cap.release()
        return frames
    
    def detect_blur(self, image: np.ndarray) -> float:
        """Detect blur using Laplacian variance (generous threshold)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian_var
    
    def detect_motion_blur(self, image: np.ndarray) -> float:
        """Detect motion blur using edge detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return np.mean(edges)
    
    def check_contrast(self, image: np.ndarray) -> float:
        """Check image contrast using standard deviation (generous threshold)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return np.std(gray)
    
    def detect_face_angles(self, faces_data: List[Dict]) -> int:
        """Estimate number of different face angles based on bounding box variations"""
        if len(faces_data) < 2:
            return len(faces_data)
        
        # Calculate face aspect ratios and positions to estimate angles
        angles = []
        for face in faces_data:
            bbox = face['bbox']
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            aspect_ratio = width / height if height > 0 else 1.0
            center_x = (bbox[0] + bbox[2]) / 2
            angles.append((aspect_ratio, center_x))
        
        # Group similar angles (simple clustering)
        unique_angles = []
        for angle in angles:
            is_unique = True
            for existing in unique_angles:
                if (abs(angle[0] - existing[0]) < 0.2 and 
                    abs(angle[1] - existing[1]) < 80):  # Generous angle grouping
                    is_unique = False
                    break
            if is_unique:
                unique_angles.append(angle)
        
        return len(unique_angles)
    
    def check_single_video_quality(self, video_path: str) -> Dict[str, Any]:
        """Check quality of a single video file"""
        if not os.path.exists(video_path):
            return {
                'overall_quality': 'fail',
                'category': 'fail',
                'error': 'Video file not found',
                'details': {}
            }
        
        # Sample 15 frames from the video
        frames = self.sample_frames(video_path, 15)
        if not frames:
            return {
                'overall_quality': 'fail',
                'category': 'fail',
                'error': 'Could not extract frames from video',
                'details': {}
            }
        
        # Initialize quality metrics
        total_faces = 0
        multiple_faces_count = 0
        blur_scores = []
        contrast_scores = []
        motion_blur_scores = []
        faces_data = []
        
        # Process each sampled frame
        for frame in frames:
            # Detect faces
            results = self.yolo_model(frame, conf=0.7)
            frame_faces = 0
            
            if len(results) > 0 and hasattr(results[0], 'boxes') and len(results[0].boxes) > 0:
                frame_faces = len(results[0].boxes)
                total_faces += frame_faces
                
                if frame_faces > 1:
                    multiple_faces_count += 1
                
                # Store face data for angle detection
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    face_width = x2 - x1
                    face_height = y2 - y1
                    faces_data.append({
                        'bbox': (x1, y1, x2, y2),
                        'size': max(face_width, face_height)
                    })
            
            # Check blur
            blur_score = self.detect_blur(frame)
            blur_scores.append(blur_score)
            
            # Check contrast
            contrast_score = self.check_contrast(frame)
            contrast_scores.append(contrast_score)
            
            # Check motion blur
            motion_blur_score = self.detect_motion_blur(frame)
            motion_blur_scores.append(motion_blur_score)
        
        # Calculate metrics
        avg_blur = np.mean(blur_scores) if blur_scores else 0
        avg_contrast = np.mean(contrast_scores) if contrast_scores else 0
        avg_motion_blur = np.mean(motion_blur_scores) if motion_blur_scores else 0
        face_angles = self.detect_face_angles(faces_data)
        avg_face_size = np.mean([f['size'] for f in faces_data]) if faces_data else 0
        
        # Quality checks - categorize issues
        critical_issues = []
        major_issues = []
        minor_issues = []
        
        # Critical issues (auto-fail)
        if total_faces < 3:
            critical_issues.append("No face detected or very few faces")
        
        if multiple_faces_count >= 8:  # More than half the frames have multiple people
            critical_issues.append("Multiple people detected in most frames")
        
        # Major issues
        if avg_blur < self.quality_thresholds['min_blur_score']:
            major_issues.append(f"Video too blurry")
        
        if avg_contrast < self.quality_thresholds['min_contrast']:
            major_issues.append(f"Poor lighting/contrast")
        
        if avg_face_size < self.quality_thresholds['min_face_size']:
            major_issues.append(f"Face too small in frame")
        
        # Minor issues
        if face_angles < self.quality_thresholds['min_face_angles']:
            minor_issues.append(f"Limited face angles")
        
        if multiple_faces_count > 0 and multiple_faces_count < 8:
            minor_issues.append(f"Multiple people in some frames")
        
        if avg_motion_blur > self.quality_thresholds['max_motion_blur']:
            minor_issues.append(f"Some motion blur detected")
        
        # Determine category
        if critical_issues:
            category = 'fail'
        elif major_issues:
            category = 'borderline'
        elif minor_issues:
            category = 'borderline'
        else:
            category = 'pass'
        
        all_issues = critical_issues + major_issues + minor_issues
        
        return {
            'overall_quality': 'pass' if category == 'pass' else 'fail',
            'category': category,
            'quality_issues': all_issues,
            'critical_issues': critical_issues,
            'major_issues': major_issues,
            'minor_issues': minor_issues,
            'details': {
                'total_faces': total_faces,
                'multiple_faces_frames': multiple_faces_count,
                'avg_blur_score': avg_blur,
                'avg_contrast': avg_contrast,
                'avg_motion_blur': avg_motion_blur,
                'face_angles': face_angles,
                'avg_face_size': avg_face_size,
                'frames_analyzed': len(frames)
            }
        }
    
    def check_student_data_quality(self, dept: str, year: str, student_data_dir: str) -> Dict[str, Any]:
        """Check quality for all students in a department-year folder"""
        dept_year_dir = os.path.join(student_data_dir, f"{dept}_{year}")
        
        print(f"Checking quality for directory: {dept_year_dir}")
        
        if not os.path.exists(dept_year_dir):
            print(f"Directory not found: {dept_year_dir}")
            return {
                'error': f"Directory not found: {dept_year_dir}",
                'passed_students': [],
                'failed_students': [],
                'borderline_students': [],
                'total_checked': 0
            }
        
        passed_students = []
        failed_students = []
        borderline_students = []
        total_processed = 0
        
        # Get all subdirectories in the dept_year directory
        try:
            student_dirs = [d for d in os.listdir(dept_year_dir) 
                          if os.path.isdir(os.path.join(dept_year_dir, d))]
            print(f"Found {len(student_dirs)} student directories: {student_dirs}")
        except Exception as e:
            print(f"Error listing directory {dept_year_dir}: {e}")
            return {
                'error': f"Error accessing directory: {str(e)}",
                'passed_students': [],
                'failed_students': [],
                'borderline_students': [],
                'total_checked': 0
            }
        
        # Process each student directory
        for student_id in student_dirs:
            student_path = os.path.join(dept_year_dir, student_id)
            
            # Check if student has a video file
            video_path = os.path.join(student_path, f"{student_id}.mp4")
            json_path = os.path.join(student_path, f"{student_id}.json")
            
            print(f"Checking student {student_id}:")
            print(f"  Video path: {video_path} (exists: {os.path.exists(video_path)})")
            print(f"  JSON path: {json_path} (exists: {os.path.exists(json_path)})")
            
            if not os.path.exists(video_path) or not os.path.exists(json_path):
                print(f"  Skipping - missing files")
                continue
            
            # Load student data
            try:
                with open(json_path, 'r') as f:
                    student_data = json.load(f)
                
                # Allow re-checking quality even if already done
                if 'qualityCheck' in student_data:
                    print(f"  Re-checking quality (was: {student_data['qualityCheck']})")
                else:
                    print(f"  First time quality check")
                
                # Allow quality check even on processed students
                if student_data.get('facesExtracted', False):
                    print(f"  Quality checking already processed student")
                
                print(f"  Processing quality check for {student_id}")
                
                # Check video quality
                quality_result = self.check_single_video_quality(video_path)
                
                # Update student JSON with quality check result
                student_data['qualityCheck'] = quality_result['overall_quality']
                student_data['qualityCategory'] = quality_result['category']
                student_data['qualityDetails'] = quality_result.get('details', {})
                student_data['qualityIssues'] = quality_result.get('quality_issues', [])
                student_data['criticalIssues'] = quality_result.get('critical_issues', [])
                student_data['majorIssues'] = quality_result.get('major_issues', [])
                student_data['minorIssues'] = quality_result.get('minor_issues', [])
                
                # Save updated JSON
                with open(json_path, 'w') as f:
                    json.dump(student_data, f, indent=2)
                
                print(f"  Quality category: {quality_result['category']}")
                print(f"  Quality issues: {quality_result.get('quality_issues', [])}")
                
                # Categorize student based on quality category
                if quality_result['category'] == 'pass':
                    passed_students.append(student_id)
                elif quality_result['category'] == 'borderline':
                    borderline_students.append({
                        'regNo': student_id,
                        'issues': quality_result.get('quality_issues', [])
                    })
                else:  # fail
                    failed_students.append(student_id)
                
                total_processed += 1
                    
            except Exception as e:
                print(f"Error processing student {student_id}: {e}")
                continue
        
        print(f"Quality check completed:")
        print(f"  Total processed: {total_processed}")
        print(f"  Passed: {len(passed_students)}")
        print(f"  Borderline: {len(borderline_students)}")
        print(f"  Failed: {len(failed_students)}")
        
        report = {
            'department': dept,
            'year': year,
            'passed_students': passed_students,
            'failed_students': failed_students,
            'borderline_students': borderline_students,
            'total_checked': total_processed
        }
        
        # Save the report to the database
        try:
            report_id = save_quality_check_report(report)
            print(f"Successfully saved quality check report with ID: {report_id}")
        except Exception as e:
            print(f"Failed to save quality check report to database: {e}")
            
        return report
