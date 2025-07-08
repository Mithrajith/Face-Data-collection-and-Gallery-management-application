from typing import List, Dict, Any
from pydantic import BaseModel

class BatchInfo(BaseModel):
    year: str
    department: str

class GalleryInfo(BaseModel):
    gallery_path: str
    identities: List[str]
    count: int

class ProcessingResult(BaseModel):
    processed_videos: int
    processed_frames: int
    extracted_faces: int
    failed_videos: List[str]
    gallery_updated: bool
    gallery_path: str

class StudentInfo(BaseModel):
    sessionId: str
    regNo: str
    name: str
    year: str
    dept: str
    batch: str
    startTime: str
    videoUploaded: bool
    facesExtracted: bool
    facesOrganized: bool
    videoPath: str
    facesCount: int
    qualityCheck: str = "not_tested"  # "not_tested", "pass", "fail"
    qualityCategory: str = "not_tested"  # "not_tested", "pass", "borderline", "fail"
    qualityDetails: Dict[str, Any] = {}
    qualityIssues: List[str] = []
    criticalIssues: List[str] = []
    majorIssues: List[str] = []
    minorIssues: List[str] = []

class StudentDataSummary(BaseModel):
    total_students: int
    students_with_video: int
    students_without_video: int
    students_processed: int
    students_pending: int
    department: str
    year: str
