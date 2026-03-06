// utils.js - Core utilities

window.formatNumber = function(num) {
    if (!num && num !== 0) return '0';
    num = parseInt(num, 10);
    if (num >= 1e9) return (num / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return num.toString();
};

window.escapeHtml = function(text) {
    if (!text) return '';
    return String(text).replace(/[&<>"']/g, function(c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
};

// Global function to reinitialize tooltips (can be called from anywhere)
window.reinitializeTooltips = function(container = document) {
    if (typeof bootstrap === 'undefined') {
        console.warn('Bootstrap not available');
        return;
    }
    
    const tooltipEls = container.querySelectorAll('[data-bs-toggle="tooltip"]');
    let count = 0;
    
    tooltipEls.forEach(el => {
        // Dispose existing tooltip if any
        const existingTooltip = bootstrap.Tooltip.getInstance(el);
        if (existingTooltip) {
            existingTooltip.dispose();
        }
        
        // Create new tooltip
        try {
            new bootstrap.Tooltip(el, { 
                trigger: 'hover focus',
                html: true,
                delay: { show: 100, hide: 50 }
            });
            count++;
        } catch (e) {
            console.warn('Tooltip error on element:', el, e);
        }
    });
    
    if (count > 0) {
        console.log(`✅ Reinitialized ${count} tooltips`);
    }
    return count;
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Utils JS initialized');
    
    // Format numbers
    document.querySelectorAll('.num-display').forEach(el => {
        if (el.dataset.value) {
            el.textContent = window.formatNumber(el.dataset.value);
        }
    });

    // Initial tooltip initialization
    setTimeout(() => {
        window.reinitializeTooltips();
    }, 100); // Small delay to ensure DOM is fully ready
});