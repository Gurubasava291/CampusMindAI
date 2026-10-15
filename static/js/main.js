/**
 * CampusPulse DSU — Main Application UI Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // Mobile nav drawer toggle if present
    const mobileBtn = document.getElementById('mobile-nav-toggle');
    const mobileDrawer = document.getElementById('mobile-nav-drawer');
    if (mobileBtn && mobileDrawer) {
        mobileBtn.addEventListener('click', () => {
            mobileDrawer.classList.toggle('open');
        });
    }
});
