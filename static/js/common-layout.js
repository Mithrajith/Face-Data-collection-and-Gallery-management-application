/**
 * Common Layout Components
 * This file contains the common header, navigation, and footer components
 * that are shared across all pages except about and login
 */

// Common Header Component
const CommonHeader = {
    html: `
    <header class="header">
        <div class="header-container d-flex justify-content-between align-items-center">
            <div class="nba">
                <img src="/static/images/image.png" class="nba-logo" alt="College Logo">
            </div>
            <div class="college-info flex-grow-1 text-center">
                <h1>SRI SHAKTHI INSTITUTE OF ENGINEERING AND TECHNOLOGY</h1>
            </div>
            <div class="logout-container ms-auto">
                <button id="logoutBtn" class="btn btn-outline-danger btn-lg" type="button">
                    <i class="fas fa-sign-out-alt me-2"></i>Logout
                </button>
            </div>
        </div>
    </header>
    `,
    
    init: function() {
        // Add logout functionality
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function() {
                localStorage.removeItem('userRole');
                window.location.href = '/login';
            });
        }
    }
};

// Common Navigation Component
const CommonNavigation = {
    html: `
    <nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom custom-navbar">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center" href="/">
                <i class="fas fa-user-circle me-2 text-primary fs-4"></i>
                <span class="fw-bold text-primary">Face Recognition Gallery</span>
            </a>

            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>

            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/" data-page="home">
                            <i class="fas fa-home me-1"></i> Home
                        </a>
                    </li>

                    <li class="nav-item">
                        <a class="nav-link" href="/process_video" data-page="process_video">
                            <i class="fas fa-video me-1"></i> Process Videos
                        </a>
                    </li>

                    <li class="nav-item">
                        <a class="nav-link" href="/create_gallery" data-page="create_gallery">
                            <i class="fas fa-database me-1"></i> Create Galleries
                        </a>
                    </li>

                    <li class="nav-item">
                        <a class="nav-link" href="/view_gallery" data-page="view_gallery">
                            <i class="fas fa-images me-1"></i> View Galleries
                        </a>
                    </li>

                    <li class="nav-item">
                        <a class="nav-link" href="/face_reg" data-page="face_reg">
                            <i class="fas fa-user-check me-1"></i> Face Recognition
                        </a>
                    </li>

                    <li class="nav-item">
                        <a class="nav-link" href="/report" data-page="report">
                            <i class="fas fa-chart-bar me-1"></i> Reports
                        </a>
                    </li>

                    <li class="nav-item">
                        <a class="nav-link" href="/admin" data-page="admin">
                            <i class="fas fa-cog me-1"></i> Admin
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    `,
    
    init: function() {
        // Set active navigation item based on current page
        this.setActiveNavItem();
    },
    
    setActiveNavItem: function() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link[data-page]');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            const linkPath = link.getAttribute('href');
            
            // Handle home page special case
            if (currentPath === '/' && linkPath === '/') {
                link.classList.add('active');
            } else if (currentPath !== '/' && currentPath.includes(linkPath) && linkPath !== '/') {
                link.classList.add('active');
            }
        });
    }
};

// Common Footer Component
const CommonFooter = {
    html: `
    <footer class="footer bg-gradient mt-5 py-4" style="background-color: #f8f9fa; border-top: 1px solid rgba(0,0,0,0.05);">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-4 mb-3 mb-md-0">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-user-circle text-primary fa-2x me-3"></i>
                        <div>
                            <h5 class="mb-0 fw-bold">Face Recognition</h5>
                            <p class="mb-0 text-muted small">Gallery Manager</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3 mb-md-0 text-center">
                </div>
                <div class="col-md-4 text-md-end">
                    <p class="mb-0">
                        <span class="text-muted">Designed & Developed by</span>
                        <span class="fw-medium ms-1"><a href="/about" style="text-decoration: none;">AI & ML Students</a></span>
                    </p>
                </div>
            </div>
        </div>
    </footer>
    `
};

// Common CSS that should be included on all pages
const CommonCSS = `
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<link rel="stylesheet" href="/static/css/style.css?v=1.1">
<link rel="stylesheet" href="/static/css/toast.css?v=1.1">
`;

// Common JS that should be included on all pages
const CommonJS = `
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
`;

// Main layout initialization function
function initCommonLayout() {
    // Check if this is a page that should have common layout
    const currentPath = window.location.pathname;
    const excludedPages = ['/about', '/login', '/about.html', '/login.html'];
    
    // Check if current page should be excluded
    const shouldExclude = excludedPages.some(page => 
        currentPath === page || currentPath.endsWith(page)
    );
    
    if (shouldExclude) {
        return; // Don't load common layout for excluded pages
    }
    
    // Inject header
    const headerContainer = document.getElementById('common-header');
    if (headerContainer) {
        headerContainer.innerHTML = CommonHeader.html;
        CommonHeader.init();
    }
    
    // Inject navigation
    const navContainer = document.getElementById('common-nav');
    if (navContainer) {
        navContainer.innerHTML = CommonNavigation.html;
        CommonNavigation.init();
    }
    
    // Inject footer
    const footerContainer = document.getElementById('common-footer');
    if (footerContainer) {
        footerContainer.innerHTML = CommonFooter.html;
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initCommonLayout();
});

// Export for manual initialization if needed
window.CommonLayout = {
    header: CommonHeader,
    navigation: CommonNavigation,
    footer: CommonFooter,
    init: initCommonLayout,
    css: CommonCSS,
    js: CommonJS
};
