#!/usr/bin/env python3

"""
--------------------------------------------------------------

 THIS IS THE TEMP FILE TO FIX STUDENT JSON FILES
 This script scans the student data directory and fixes JSON files
 by adding missing fields like regNo, name, sessionId, year, dept,
 batch, startTime, videoUploaded, facesExtracted, facesOrganized,
 videoPath, and facesCount.

--------------------------------------------------------------
"""

import os
import json
import sys

# Add src directory to system path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import STUDENT_DATA_DIR

def fix_student_json_files():
    """Fix student JSON files missing required fields"""
    print(f"Scanning {STUDENT_DATA_DIR} for JSON files...")
    
    if not os.path.exists(STUDENT_DATA_DIR):
        print(f"Error: Directory not found: {STUDENT_DATA_DIR}")
        return
    
    # Get all department-year folders
    total_fixed = 0
    for dept_year_folder in os.listdir(STUDENT_DATA_DIR):
        dept_year_path = os.path.join(STUDENT_DATA_DIR, dept_year_folder)
        
        if not os.path.isdir(dept_year_path):
            continue
        
        # Try to extract dept and year from folder name
        try:
            dept, year = dept_year_folder.split('_', 1)
        except ValueError:
            print(f"Warning: Skipping folder with invalid format: {dept_year_folder}")
            continue
            
        print(f"Processing folder: {dept_year_folder}")
        
        # Process each student folder
        for student_id in os.listdir(dept_year_path):
            student_path = os.path.join(dept_year_path, student_id)
            
            if not os.path.isdir(student_path):
                continue
                
            json_file = os.path.join(student_path, f"{student_id}.json")
            
            if not os.path.exists(json_file):
                print(f"  Warning: No JSON file found for student {student_id}")
                continue
                
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Check for missing fields
                fields_fixed = []
                
                if 'regNo' not in data:
                    data['regNo'] = student_id
                    fields_fixed.append('regNo')
                    
                if 'name' not in data:
                    data['name'] = f"Student {student_id}"
                    fields_fixed.append('name')
                    
                if 'sessionId' not in data:
                    data['sessionId'] = f"session_{student_id}"
                    fields_fixed.append('sessionId')
                    
                if 'year' not in data:
                    data['year'] = year
                    fields_fixed.append('year')
                    
                if 'dept' not in data:
                    data['dept'] = dept
                    fields_fixed.append('dept')
                    
                if 'batch' not in data:
                    data['batch'] = f"{dept}_{year}"
                    fields_fixed.append('batch')
                    
                if 'startTime' not in data:
                    data['startTime'] = ""
                    fields_fixed.append('startTime')
                    
                if 'videoUploaded' not in data:
                    data['videoUploaded'] = os.path.exists(os.path.join(student_path, f"{student_id}.mp4"))
                    fields_fixed.append('videoUploaded')
                    
                if 'facesExtracted' not in data:
                    data['facesExtracted'] = False
                    fields_fixed.append('facesExtracted')
                    
                if 'facesOrganized' not in data:
                    data['facesOrganized'] = False
                    fields_fixed.append('facesOrganized')
                    
                if 'videoPath' not in data:
                    data['videoPath'] = os.path.join(student_path, f"{student_id}.mp4")
                    fields_fixed.append('videoPath')
                    
                if 'facesCount' not in data:
                    data['facesCount'] = 0
                    fields_fixed.append('facesCount')
                
                # If any fields were fixed, save the updated JSON
                if fields_fixed:
                    print(f"  Fixed {len(fields_fixed)} fields for student {student_id}: {', '.join(fields_fixed)}")
                    with open(json_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    total_fixed += 1
                    
            except Exception as e:
                print(f"  Error processing student {student_id}: {e}")
    
    print(f"\nFixed {total_fixed} JSON files.")

if __name__ == "__main__":
    fix_student_json_files()
