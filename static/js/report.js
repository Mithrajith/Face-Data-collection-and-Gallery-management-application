
class StudentDataReport {
    constructor() {
        this.departments = [];
        this.years = [];
        this.studentDatabase = {};
        this.init();
    }

    async init() {
        await this.loadFiltersFromAPI();
        this.setupEventListeners();
        this.showInitialMessage();
    }

    // Load departments and years from the API
    async loadFiltersFromAPI() {
        try {
            const response = await fetch('/batches');
            const data = await response.json();
            
            this.departments = data.departments || [];
            this.years = data.years || [];
            
            this.populateDropdowns();
            await this.loadStudentData();
        } catch (error) {
            this.loadFallbackData();
        }
    }

    // Populate dropdown options from API data
    populateDropdowns() {
        const departmentSelect = document.getElementById('departmentSelect');
        const batchSelect = document.getElementById('batchSelect');

        // Clear existing options except the first one
        departmentSelect.innerHTML = '<option value="">Select Department</option>';
        batchSelect.innerHTML = '<option value="">Select Batch</option>';

        // Populate departments
        this.departments.forEach(dept => {
            const option = document.createElement('option');
            // Handle both string and object formats
            if (typeof dept === 'object') {
                option.value = dept.department_id || dept.id;
                option.textContent = dept.name || dept.department_id;
            } else {
                option.value = dept;
                option.textContent = dept;
            }
            departmentSelect.appendChild(option);
        });

        // Populate years/batches
        this.years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `${year-4} - ${year}`;4
            batchSelect.appendChild(option);
        });
    }

    // Initialize empty student database - data will be loaded on demand
    async loadStudentData() {
        // Initialize empty database - data will be fetched dynamically when needed
        this.studentDatabase = {};
    }

    // Fetch student data from APIs and merge results
    async fetchStudentDataFromAPI(department, year) {
        try {
            // Fetch students who have logged in (from collection app data)
            const loggedInResponse = await fetch(`/student-data/${department}/${year}/students`);
            
            if (!loggedInResponse.ok) {
                throw new Error(`HTTP error! status: ${loggedInResponse.status}`);
            }
            
            const loggedInData = await loggedInResponse.json();
            const loggedInStudents = loggedInData.students || [];
            
            // Try to fetch all students from database (registered students)
            let allStudentsFromDB = [];
            try {
                const endpoint = `/student-list/${department}/${year}`;
                const allStudentsResponse = await fetch(endpoint);
                
                if (allStudentsResponse.ok) {
                    const allStudentsData = await allStudentsResponse.json();
                    const studentsArray = allStudentsData.students || 
                                         allStudentsData.data || 
                                         allStudentsData.results || 
                                         (Array.isArray(allStudentsData) ? allStudentsData : []);
                    
                    allStudentsFromDB = studentsArray.map(student => ({
                        regNo: student.register_no,
                        name: student.name || 'Unknown',
                        departmentId: student.department_id || department,
                        batch: student.batch || year,
                        id: student.id,
                        department: student.department || department,
                        dob: student.dob,
                        regulation: student.regulation,
                        semester: student.semester
                    }));
                }
            } catch (dbError) {
                // Continue with only logged-in students if database fetch fails
            }
            
            // Create a map of logged in students by reg number for quick lookup
            const loggedInMap = new Map();
            loggedInStudents.forEach(student => {
                const regNo = student.regNo || student.studentId || student.id;
                loggedInMap.set(regNo, student);
            });
            
            // Combine the data to create comprehensive student list
            const combinedStudents = [];
            const processedRegNos = new Set(); // Track processed registration numbers
            
            // First, process all logged-in students (they have priority)
            loggedInStudents.forEach(student => {
                const regNo = student.regNo || student.studentId || student.id;
                if (!processedRegNos.has(regNo)) {
                    // Find corresponding database student for additional info
                    const dbStudent = allStudentsFromDB.find(db => 
                        (db.regNo || db.studentId || db.id) === regNo
                    );
                    
                    combinedStudents.push({
                        regNo: regNo,
                        name: student.name || student.studentName || (dbStudent?.name) || 'Unknown',
                        status: student.videoUploaded ? 'uploaded' : 'logged_in',
                        uploaded: student.videoUploaded || false,
                        facesExtracted: student.facesExtracted || false,
                        department: (dbStudent?.department) || department,
                        batch: year
                    });
                    processedRegNos.add(regNo);
                }
            });
            
            // Then, process remaining database students who are not logged in
            if (allStudentsFromDB.length > 0) {
                allStudentsFromDB.forEach(dbStudent => {
                    const regNo = dbStudent.regNo || dbStudent.studentId || dbStudent.id;
                    if (!processedRegNos.has(regNo)) {
                        // Student is not logged in
                        combinedStudents.push({
                            regNo: regNo,
                            name: dbStudent.name || dbStudent.studentName || 'Unknown',
                            status: 'not_logged_in',
                            uploaded: false,
                            facesExtracted: false,
                            department: dbStudent.department || department,
                            batch: year
                        });
                        processedRegNos.add(regNo);
                    }
                });
            }
            
            // Sort by registration number
            combinedStudents.sort((a, b) => {
                const regA = String(a.regNo || '');
                const regB = String(b.regNo || '');
                return regA.localeCompare(regB);
            });
            
            // Cache the data
            if (!this.studentDatabase[department]) {
                this.studentDatabase[department] = {};
            }
            this.studentDatabase[department][year] = combinedStudents;
            
            return combinedStudents;
            
        } catch (error) {
            throw error;
        }
    }

    // Fallback data if API fails
    loadFallbackData() {
        this.departments = [
            { id: 'CSE', name: 'Computer Science Engineering' },
            { id: 'ECE', name: 'Electronics & Communication' },
            { id: 'MECH', name: 'Mechanical Engineering' },
            { id: 'CIVIL', name: 'Civil Engineering' },
            { id: 'EEE', name: 'Electrical Engineering' },
            { id: 'IT', name: 'Information Technology' },
            { id: 'AIML', name: 'AI & Machine Learning' },
            { id: 'BME', name: 'Biomedical Engineering' }
        ];
        this.years = ['2023', '2024', '2025', '2026', '2027'];
        this.populateDropdowns();
    }

    setupEventListeners() {
        document.getElementById('departmentSelect').addEventListener('change', () => this.validateAndLoadData());
        document.getElementById('batchSelect').addEventListener('change', () => this.validateAndLoadData());
    }





    validateAndLoadData() {
        const department = document.getElementById('departmentSelect').value;
        const batch = document.getElementById('batchSelect').value;
        const loadBtn = document.getElementById('loadDataBtn');
        
        if (department && batch) {
            loadBtn.disabled = false;
            this.loadStudentDataForTable();
        } else {
            loadBtn.disabled = true;
            this.hideDataSections();
            
            if (!department && !batch) {
                return;
            } else if (!department) {
                return;
            } else if (!batch) {
                return;
            }
        }
    }

    hideDataSections() {
        document.getElementById('statsSection').style.display = 'none';
        document.getElementById('dataTableSection').style.display = 'none';
        document.getElementById('noDataSection').style.display = 'none';
        document.getElementById('alertContainer').innerHTML = '';
    }

    showNoDataFound(department_id, year) {

        // Fetch department name from API
        fetch(`/departments/name/${department_id}`)
            .then(response => response.json())
            .then(department => {
                // Hide other sections
                document.getElementById('statsSection').style.display = 'none';
                document.getElementById('dataTableSection').style.display = 'none';
                document.getElementById('alertContainer').innerHTML = '';
                
                // Update no data section content
                const noDataMessage = document.querySelector('.no-data-message');
                if (noDataMessage) {
                    noDataMessage.innerHTML = `
                        No student data available for <strong>${department.name || department_id}  ${year - 4} - ${year}</strong>.
                    `;
                }
                
                // Show no data section
                document.getElementById('noDataSection').style.display = 'flex';
            })
            .catch(error => {
                // Fallback to department_id if API fails
                const noDataMessage = document.querySelector('.no-data-message');
                if (noDataMessage) {
                    noDataMessage.innerHTML = `
                        No student data available for <strong>${department_id}  ${year - 4} - ${year}</strong>.
                    `;
                }
                document.getElementById('noDataSection').style.display = 'flex';
            });
        
        // Show no data section
        document.getElementById('noDataSection').style.display = 'flex';
    }

    async loadStudentDataForTable() {
        const department = document.getElementById('departmentSelect').value;
        const year = document.getElementById('batchSelect').value;
        
        if (!department || !year) {
            return;
        }
        
        try {
            let students;
            
            // Check if data is already cached
            if (this.studentDatabase[department] && this.studentDatabase[department][year]) {
                students = this.studentDatabase[department][year];
            } else {
                // Fetch data from API
                students = await this.fetchStudentDataFromAPI(department, year);
            }
            
            // Check if any students were found
            if (!students || students.length === 0) {
                this.showNoDataFound(department, year);
                return;
            }
            
            const uploadedCount = students.filter(student => student.status === 'uploaded').length;
            const loggedInCount = students.filter(student => student.status === 'logged_in').length;
            const notLoggedInCount = students.filter(student => student.status === 'not_logged_in').length;
            const totalCount = students.length;
            
            // Update statistics
            document.getElementById('uploadedCount').textContent = uploadedCount;
            document.getElementById('loggedInCount').textContent = loggedInCount;
            document.getElementById('notLoggedInCount').textContent = notLoggedInCount;
            document.getElementById('totalStudents').textContent = totalCount;
            
            // Update filter info
            document.getElementById('filterInfo').textContent = `${department} - Batch ${year}`;
            
            // Populate table
            this.populateStudentTable(students, year);

            // Show sections
            document.getElementById('statsSection').style.display = 'block';
            document.getElementById('dataTableSection').style.display = 'block';
            document.getElementById('noDataSection').style.display = 'none';
            
            // Clear alerts
            document.getElementById('alertContainer').innerHTML = '';
            
        } catch (error) {
            this.hideDataSections();
        }
    }

    populateStudentTable(students, year) {
        const tableBody = document.getElementById('studentTableBody');
        tableBody.innerHTML = '';
        
        students.forEach((student, index) => {
            const row = document.createElement('tr');
            
            // Determine status badge
            let statusBadge = '';
            switch(student.status) {
                case 'uploaded':
                    statusBadge = '<span class="badge bg-success">Uploaded Successfully</span>';
                    break;
                case 'logged_in':
                    statusBadge = '<span class="badge bg-warning text-dark">Logged in but not uploaded</span>';
                    break;
                case 'not_logged_in':
                    statusBadge = '<span class="badge bg-danger">Not logged in</span>';
                    break;
                default:
                    statusBadge = '<span class="badge bg-secondary">Unknown</span>';
            }
            
            row.innerHTML = `
                <td><strong>${index + 1}</strong></td>
                <td><strong>${student.regNo}</strong></td>
                <td>${student.name}</td>
                <td>${student.department}</td>
                <td>${year}</td>
                <td>${statusBadge}</td>
            `;
            tableBody.appendChild(row);
        });
        
        // Update displayed rows count
        document.getElementById('displayedRows').textContent = students.length;
    }

    // Export functions
    async exportToCSV() {
        const department = document.getElementById('departmentSelect').value;
        const batch = document.getElementById('batchSelect').value;
        
        if (!department || !batch) {
            return;
        }
        
        try {
            // Get students data (from cache or API)
            if (this.studentDatabase[department] && this.studentDatabase[department][batch]) {
                students = this.studentDatabase[department][batch];
            } else {
                students = await this.fetchStudentDataFromAPI(department, batch);
            }
            
            if (!students || students.length === 0) {
                return;
            }
            
            // Create CSV content
            let csvContent = "S.No,Reg No,Student Name,Department,Batch,Status,Video Uploaded,Faces Extracted\n";
            students.forEach((student, index) => {
                const statusText = student.status === 'uploaded' ? 'Uploaded Successfully' :
                                 student.status === 'logged_in' ? 'Logged in but not uploaded' : 'Not logged in';
                csvContent += `${index + 1},"${student.regNo}","${student.name}","${student.department}","${batch}","${statusText}","${student.uploaded ? 'Yes' : 'No'}","${student.facesExtracted ? 'Yes' : 'No'}"\n`;
            });
            
            // Download CSV
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `student_data_${department}_${batch}_${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
        } catch (error) {
        }
    }

    async exportToExcel() {
        const department = document.getElementById('departmentSelect').value;
        const batch = document.getElementById('batchSelect').value;
        
        if (!department || !batch) {
            return;
        }
        
        try {
            // Ensure we have data
            let students;
            if (this.studentDatabase[department] && this.studentDatabase[department][batch]) {
                students = this.studentDatabase[department][batch];
            } else {
                students = await this.fetchStudentDataFromAPI(department, batch);
            }
            
            if (!students || students.length === 0) {
                return;
            }
            
        } catch (error) {
        }
    }

    async exportToPDF() {
        const department = document.getElementById('departmentSelect').value;
        const batch = document.getElementById('batchSelect').value;
        
        if (!department || !batch) {
            return;
        }
        
        try {
            // Ensure we have data
            let students;
            if (this.studentDatabase[department] && this.studentDatabase[department][batch]) {
                students = this.studentDatabase[department][batch];
            } else {
                students = await this.fetchStudentDataFromAPI(department, batch);
            }
            
            if (!students || students.length === 0) {
                return;
            }
            
        } catch (error) {
        }
    }

    async printTable() {
        const department = document.getElementById('departmentSelect').value;
        const batch = document.getElementById('batchSelect').value;
        
        if (!department || !batch) {
            return;
        }
        
        try {
            // Ensure we have data to print
            let students;
            if (this.studentDatabase[department] && this.studentDatabase[department][batch]) {
                students = this.studentDatabase[department][batch];
            } else {
                students = await this.fetchStudentDataFromAPI(department, batch);
            }
            
            if (!students || students.length === 0) {
                return;
            }
            
            // Create printable content
            const printWindow = window.open('', '_blank');
            const table = document.querySelector('#dataTableSection .table').outerHTML;
            const uploadedCount = students.filter(s => s.status === 'uploaded').length;
            const loggedInCount = students.filter(s => s.status === 'logged_in').length;
            const notLoggedInCount = students.filter(s => s.status === 'not_logged_in').length;
            const totalStudents = students.length;
            
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Student Data Report - ${department} Batch ${batch}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .header { text-align: center; margin-bottom: 30px; }
                        .stats { margin-bottom: 20px; }
                        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
                        th { background-color: #007bff; color: white; }
                        .badge { padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }
                        .bg-success { background-color: #28a745; }
                        .bg-danger { background-color: #dc3545; }
                        @media print { body { margin: 0; } }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>SIET - Student Data Report</h1>
                        <h2>${department} - Batch ${batch}</h2>
                        <div class="stats">
                            <p><strong>Total Students:</strong> ${totalStudents}</p>
                            <p><strong>Uploaded Successfully:</strong> ${uploadedCount} | <strong>Logged in but not uploaded:</strong> ${loggedInCount} | <strong>Not logged in:</strong> ${notLoggedInCount}</p>
                            <p><strong>Generated on:</strong> ${new Date().toLocaleString()}</p>
                        </div>
                    </div>
                    ${table}
                </body>
                </html>
            `);
            
            printWindow.document.close();
            printWindow.focus();
            
            // Wait for content to load then print
            setTimeout(() => {
                printWindow.print();
                printWindow.close();
            }, 500);
            
        } catch (error) {
        }
    }

    exportData() {
        // Silent operation - user can use export dropdown
    }

    showInitialMessage() {
        this.hideDataSections();
    }
}

// Global functions for onclick handlers
let reportInstance;

function validateAndLoadData() {
    reportInstance.validateAndLoadData();
}

function loadStudentData() {
    reportInstance.loadStudentDataForTable();
}

function exportToPDF() {
    reportInstance.exportToPDF();
}

function printTable() {
    reportInstance.printTable();
}

function exportData() {
    reportInstance.exportData();
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    reportInstance = new StudentDataReport();
});