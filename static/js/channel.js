// channel.js - Only for channel detail page
// Contains: category tabs, sorting, pagination enhancements

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        console.log('📺 Channel JS initialized');

        // Smooth scroll to top when paginating
        document.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                if (this.getAttribute('href') !== '#') {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });
        });

        // Optional: Add loading indicator for category switches
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                // Visual feedback for category change
                this.style.opacity = '0.7';
            });
        });
    });
})();