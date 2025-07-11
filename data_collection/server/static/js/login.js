// login.js - Handles student login for face collection app

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('login-form');
    const errorDiv = document.getElementById('login-error');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        errorDiv.classList.add('d-none');
        const regno = document.getElementById('regno').value.trim();
        const dob = document.getElementById('dob').value;
        if (!regno || !dob) {
            errorDiv.textContent = 'Please enter both Register Number and Date of Birth.';
            errorDiv.classList.remove('d-none');
            return;
        }
        try {
            const res = await fetch('/api/student-login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ regno, dob })
            });
            const data = await res.json();
            if (data.success) {
                // Store session info and redirect to main app
                localStorage.setItem('studentRegNo', regno);
                window.location.href = '/static/index.html';
            } else {
                errorDiv.textContent = data.message || 'Invalid credentials.';
                errorDiv.classList.remove('d-none');
            }
        } catch (err) {
            errorDiv.textContent = 'Network error. Please try again.';
            errorDiv.classList.remove('d-none');
        }
    });
});
