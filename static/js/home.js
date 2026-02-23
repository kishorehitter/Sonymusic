// ============================================================================
// SONY MUSIC INDIA - MAIN JAVASCRIPT FILE
// Version: 3.0.0
// Description: Core functionality including animations, search, carousel, forms
// ============================================================================

'use strict';

(function() {
    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    /**
     * DOM Ready Handler - Initializes all components
     */
    document.addEventListener('DOMContentLoaded', function() {
        console.log('🚀 Sony Music India - Initializing application');
        
        // Core functionality
        initSVGAnimation();
        initSubscriptionForms();
        initNavbar();
        initScrollReveal();
        
        // UI Components
        initReleasesCarousel();
        initSearchFunctionality();
        
        // Event handlers
        initSmoothScrolling();

        if (typeof initParallaxEffect === 'function') {
            initParallaxEffect();
        } else {
            console.log('📦 Skipping parallax effect (not defined)');
        }

        if (typeof initStatsCounter === 'function') {
            initStatsCounter();
        } else {
            console.log('📊 Skipping stats counter (not defined)');
        }

        // ✅ ADD THIS LINE - Initialize ticker
        initLatestTicker();
    });
    
    
    // ============================================================================
    // CORE ANIMATIONS
    // ============================================================================
    
    /**
     * Initializes the SVG dot animation for Sony Music logo pattern
     * @returns {void}
     */
    function initSVGAnimation() {
        const SVG_CONFIG = {
            centerX: 200,
            centerY: 200,
            dotSize: 5,
            spacing: 20
        };
        
        // Sony Music logo pattern - exact dot counts per row
        const DOT_PATTERN = [
            3,   // Row 1: 3 dots
            7,   // Row 2: 7 dots
            9,   // Row 3: 9 dots
            9,   // Row 4: 9 dots
            11,  // Row 5: 11 dots (widest)
            11,  // Row 6: 11 dots
            11,  // Row 7: 11 dots
            9,   // Row 8: 9 dots
            9,   // Row 9: 9 dots
            7,   // Row 10: 7 dots
            3    // Row 11: 3 dots
        ];
        
        let dots = [];
        
        /**
         * Creates SVG dots in grid pattern
         */
        function createDots() {
            const grid = document.getElementById('dotGrid');
            if (!grid) {
                console.warn('⚠️ SVG grid element not found');
                return;
            }
            
            grid.innerHTML = '';
            dots = [];
            
            const totalRows = DOT_PATTERN.length;
            const startY = SVG_CONFIG.centerY - ((totalRows - 1) * SVG_CONFIG.spacing) / 2;
            
            DOT_PATTERN.forEach((dotsInRow, rowIndex) => {
                const y = startY + rowIndex * SVG_CONFIG.spacing;
                const rowWidth = (dotsInRow - 1) * SVG_CONFIG.spacing;
                const startX = SVG_CONFIG.centerX - rowWidth / 2;
                
                for (let dotIndex = 0; dotIndex < dotsInRow; dotIndex++) {
                    const x = startX + dotIndex * SVG_CONFIG.spacing;
                    
                    const distance = Math.sqrt(
                        Math.pow(x - SVG_CONFIG.centerX, 2) + 
                        Math.pow(y - SVG_CONFIG.centerY, 2)
                    );
                    
                    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    circle.setAttribute('cx', x);
                    circle.setAttribute('cy', y);
                    circle.setAttribute('r', 0);
                    circle.setAttribute('fill', 'url(#dotGradient)');
                    circle.setAttribute('filter', 'url(#glow)');
                    circle.style.transition = 'r 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    
                    grid.appendChild(circle);
                    
                    dots.push({
                        element: circle,
                        distance: distance
                    });
                }
            });
            
            // Sort dots by distance from center for sequential animation
            dots.sort((a, b) => a.distance - b.distance);
        }
        
        /**
         * Animates dots sequentially from center outward
         */
        function startAnimation() {
            // Reset all dots
            dots.forEach(dot => {
                dot.element.setAttribute('r', 0);
            });
            
            // Animate with sequential delay
            const ANIMATION_DURATION = 2000; // 2 seconds
            const DELAY_PER_DOT = ANIMATION_DURATION / dots.length;
            
            dots.forEach((dot, index) => {
                setTimeout(() => {
                    dot.element.setAttribute('r', SVG_CONFIG.dotSize);
                }, index * DELAY_PER_DOT);
            });
        }
        
        // Initialize animation
        createDots();
        setTimeout(startAnimation, 500);
        setInterval(startAnimation, 10000); // Repeat every 10 seconds
    }
    

    // ============================================================================
    // TICKER - Smooth Infinite Scroll (DEBUG VERSION)
    // ============================================================================

    function initLatestTicker() {
        const track = document.querySelector('.ticker-track');
        if (!track) return;
        
        let position = 0;
        let animationFrame;
        let isPaused = false;
        let lastTimestamp = 0;
        
        // ✅ Speed in pixels per second (consistent across devices)
        const speeds = {
            mobile: 30,    // 30 pixels per second
            tablet: 40,    // 40 pixels per second
            desktop: 50    // 50 pixels per second
        };
        
        function getCurrentSpeed() {
            const width = window.innerWidth;
            if (width <= 480) return speeds.mobile;
            if (width <= 768) return speeds.tablet;
            return speeds.desktop;
        }
        
        let pixelsPerSecond = getCurrentSpeed();
        console.log(`🎬 Speed: ${pixelsPerSecond}px/sec`);
        
        function getItemWidth() {
            const firstItem = track.children[0];
            if (!firstItem) return 0;
            const style = window.getComputedStyle(track);
            const gap = parseInt(style.gap) || 50;
            return firstItem.offsetWidth + gap;
        }
        
        // ✅ Frame-rate independent animation
        function animate(timestamp) {
            if (isPaused) {
                lastTimestamp = timestamp;
                animationFrame = requestAnimationFrame(animate);
                return;
            }
            
            if (lastTimestamp) {
                const deltaTime = timestamp - lastTimestamp; // milliseconds
                const distance = (pixelsPerSecond * deltaTime) / 1000; // Convert to pixels
                
                position -= distance;
                
                const itemWidth = getItemWidth();
                const totalWidth = itemWidth * 3;
                
                if (Math.abs(position) >= totalWidth) {
                    position = 0;
                    for (let i = 0; i < 3; i++) {
                        track.appendChild(track.children[0]);
                    }
                }
                
                track.style.transform = `translateX(${position}px)`;
            }
            
            lastTimestamp = timestamp;
            animationFrame = requestAnimationFrame(animate);
        }
        
        animationFrame = requestAnimationFrame(animate);
        
        // Update speed on resize
        window.addEventListener('resize', () => {
            pixelsPerSecond = getCurrentSpeed();
            console.log(`📱 Speed updated: ${pixelsPerSecond}px/sec`);
        });
        
        // Pause on hover
        track.addEventListener('mouseenter', () => {
            isPaused = true;
        });
        
        track.addEventListener('mouseleave', () => {
            isPaused = false;
        });
        
        // Clean up
        window.addEventListener('beforeunload', () => {
            if (animationFrame) {
                cancelAnimationFrame(animationFrame);
            }
        });
    }
        
    // ============================================================================
    // FORM HANDLING
    // ============================================================================
    
    /**
     * Initializes subscription forms with loading states
     * @returns {void}
     */
    function initSubscriptionForms() {
        const subscribeForms = document.querySelectorAll('.subscribe-form');
        
        subscribeForms.forEach(form => {
            form.addEventListener('submit', function(event) {
                const submitButton = this.querySelector('.subscribe-btn');
                if (!submitButton) return;
                
                // Show loading state
                const originalHTML = submitButton.innerHTML;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Subscribing...';
                submitButton.disabled = true;
                
                // Store original state for timeout cleanup
                setTimeout(() => {
                    submitButton.innerHTML = originalHTML;
                    submitButton.disabled = false;
                }, 5000);
            });
        });
    }
    
    
    // ============================================================================
    // NAVIGATION & UI
    // ============================================================================
    
    /**
     * Adds scroll effect to navbar
     * @returns {void}
     */
    function initNavbar() {
        const navbar = document.querySelector('.custom-navbar');
        
        if (navbar) {
            window.addEventListener('scroll', () => {
                if (window.scrollY > 50) {
                    navbar.classList.add('scrolled');
                } else {
                    navbar.classList.remove('scrolled');
                }
            });
        }
    }
    
    /**
     * Initializes scroll reveal animations
     * @returns {void}
     */
    function initScrollReveal() {
        const OBSERVER_OPTIONS = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, OBSERVER_OPTIONS);
        
        const animateElements = document.querySelectorAll(
            '.channel-card, .genre-card, .stat-item'
        );
        
        animateElements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = `all 0.6s ease ${index * 0.1}s`;
            observer.observe(el);
        });
    }
    
    /**
     * Enables smooth scrolling for anchor links
     * @returns {void}
     */
    function initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(event) {
                event.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                
                if (target) {
                    const navbarHeight = document.querySelector('.custom-navbar')?.offsetHeight || 0;
                    const targetPosition = target.offsetTop - navbarHeight;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                    
                    // Close mobile navbar if open
                    const navbarCollapse = document.querySelector('.navbar-collapse');
                    if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                        const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                        bsCollapse.hide();
                    }
                }
            });
        });
    }
    
    /**
     * Creates parallax effect on scroll
    //  * @returns {void}
    // function initParallaxEffect() {
    //     window.addEventListener('scroll', () => {
    //         const scrolled = window.pageYOffset;
    //         const parallaxElements = document.querySelectorAll('.svg-animation-wrapper');
            
    //         parallaxElements.forEach(el => {
    //             const speed = 0.3;
    //             el.style.transform = `translateY(${scrolled * speed}px)`;
    //         });
    //     });
    // }
    
    // ============================================================================
    // RELEASES CAROUSEL - CONTINUOUS LOOP VERSION
    // ============================================================================

    /**
     * Initializes the releases carousel with continuous looping in one direction
     * @returns {void}
     */
    function initReleasesCarousel() {
        const track = document.getElementById('releasesSlider');
        const originalSlides = track?.querySelectorAll('.release-slide-item:not(.clone)');
        const indicatorsContainer = document.getElementById('carouselIndicators');
        const prevBtn = document.getElementById('prevSlide');
        const nextBtn = document.getElementById('nextSlide');
        
        if (!originalSlides || originalSlides.length === 0) return;
        
        const totalSlides = originalSlides.length;
        let currentIndex = 0;
        let autoplayInterval;
        let isTransitioning = false;
        
        // Remove any existing clones first
        track.querySelectorAll('.clone').forEach(clone => clone.remove());
        
        // Clone slides for infinite loop
        // Add clones at the end
        originalSlides.forEach(slide => {
            const clone = slide.cloneNode(true);
            clone.classList.add('clone');
            clone.removeAttribute('data-video-id'); // Remove to avoid duplicate IDs
            track.appendChild(clone);
        });
        
        // Add clones at the beginning
        for (let i = originalSlides.length - 1; i >= 0; i--) {
            const clone = originalSlides[i].cloneNode(true);
            clone.classList.add('clone');
            clone.removeAttribute('data-video-id'); // Remove to avoid duplicate IDs
            track.insertBefore(clone, track.firstChild);
        }
        
        // Get all slides including clones
        const allSlides = track.querySelectorAll('.release-slide-item');
        
        /**
         * Creates carousel indicators/dots
         */
        function createIndicators() {
            if (!indicatorsContainer) return;
            
            indicatorsContainer.innerHTML = '';
            for (let i = 0; i < totalSlides; i++) {
                const dot = document.createElement('div');
                dot.className = 'carousel-dot';
                dot.setAttribute('role', 'button');
                dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
                dot.addEventListener('click', () => goToSlide(i));
                indicatorsContainer.appendChild(dot);
            }
        }
        
        /**
         * Updates carousel position and active states
         * @param {boolean} smooth - Whether to use smooth transition
         */
        function updateCarousel(smooth = true) {
            const slideWidth = allSlides[0].offsetWidth + 30; // width + gap
            const containerWidth = track.parentElement.offsetWidth;
            const centerOffset = (containerWidth - slideWidth) / 2;
            
            // Account for the prepended clones (totalSlides + currentIndex)
            const actualIndex = totalSlides + currentIndex;
            const translateX = -actualIndex * slideWidth + centerOffset;
            
            if (!smooth) {
                track.style.transition = 'none';
            } else {
                track.style.transition = 'transform 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            }
            
            track.style.transform = `translateX(${translateX}px)`;
            
            // Update slide states
            allSlides.forEach((slide, index) => {
                slide.classList.remove('active', 'adjacent');
                
                if (index === actualIndex) {
                    slide.classList.add('active');
                    slide.setAttribute('aria-hidden', 'false');
                } else {
                    slide.setAttribute('aria-hidden', 'true');
                    
                    if (index === actualIndex - 1 || index === actualIndex + 1) {
                        slide.classList.add('adjacent');
                    }
                }
            });
            
            // Update indicators (only for actual slides, not clones)
            const dots = indicatorsContainer.querySelectorAll('.carousel-dot');
            const indicatorIndex = ((currentIndex % totalSlides) + totalSlides) % totalSlides;
            dots.forEach((dot, index) => {
                dot.classList.toggle('active', index === indicatorIndex);
                dot.setAttribute('aria-current', index === indicatorIndex ? 'true' : 'false');
            });
        }
        
        /**
         * Navigates to specific slide
         * @param {number} index - Slide index
         */
        function goToSlide(index) {
            if (isTransitioning) return;
            currentIndex = index;
            updateCarousel();
            resetAutoplay();
        }
        
        /**
         * Moves to next slide (continuous loop)
         */
        function nextSlide() {
            if (isTransitioning) return;
            isTransitioning = true;
            
            currentIndex++;
            updateCarousel(true);
            
            // After animation completes, check if we need to reset
            setTimeout(() => {
                if (currentIndex >= totalSlides) {
                    // Reset to beginning without animation
                    currentIndex = 0;
                    updateCarousel(false);
                }
                isTransitioning = false;
            }, 850); // Slightly longer than animation duration
        }
        
        /**
         * Moves to previous slide (for manual control)
         */
        function prevSlide() {
            if (isTransitioning) return;
            isTransitioning = true;
            
            currentIndex--;
            updateCarousel(true);
            
            // After animation completes, check if we need to reset
            setTimeout(() => {
                if (currentIndex < 0) {
                    // Reset to end without animation
                    currentIndex = totalSlides - 1;
                    updateCarousel(false);
                }
                isTransitioning = false;
            }, 850); // Slightly longer than animation duration
        }
        
        /**
         * Starts autoplay (continuous loop in one direction)
         */
        function startAutoplay() {
            stopAutoplay();
            autoplayInterval = setInterval(nextSlide, 3500); // Auto-advance every 3.5 seconds
        }
        
        /**
         * Stops autoplay
         */
        function stopAutoplay() {
            if (autoplayInterval) {
                clearInterval(autoplayInterval);
            }
        }
        
        /**
         * Resets autoplay timer
         */
        function resetAutoplay() {
            stopAutoplay();
            startAutoplay();
        }
        
        /**
         * Initializes touch/swipe support
         */
        function initTouchSupport() {
            let touchStartX = 0;
            
            track.addEventListener('touchstart', (event) => {
                touchStartX = event.changedTouches[0].screenX;
                stopAutoplay();
            }, { passive: true });
            
            track.addEventListener('touchend', (event) => {
                const touchEndX = event.changedTouches[0].screenX;
                const threshold = 50;
                
                if (touchStartX - touchEndX > threshold) {
                    nextSlide();
                } else if (touchEndX - touchStartX > threshold) {
                    prevSlide();
                }
                
                startAutoplay();
            }, { passive: true });
        }
        
        /**
         * Initializes keyboard navigation
         */
        function initKeyboardNavigation() {
            document.addEventListener('keydown', (event) => {
                if (event.key === 'ArrowLeft') {
                    event.preventDefault();
                    prevSlide();
                    resetAutoplay();
                } else if (event.key === 'ArrowRight') {
                    event.preventDefault();
                    nextSlide();
                    resetAutoplay();
                }
            });
        }
        
        /**
         * Handles window resize
         */
        function initResizeHandler() {
            window.addEventListener('resize', () => {
                clearTimeout(window.resizeTimer);
                window.resizeTimer = setTimeout(() => {
                    updateCarousel(false);
                }, 250);
            });
        }
        
        // Initialize carousel
        createIndicators();
        updateCarousel(false); // Initial position without animation
        
        // Start autoplay after a short delay
        setTimeout(() => {
            startAutoplay();
        }, 500);
        
        // Event listeners
        nextBtn?.addEventListener('click', () => {
            nextSlide();
            resetAutoplay();
        });
        
        prevBtn?.addEventListener('click', () => {
            prevSlide();
            resetAutoplay();
        });
        
        // Pause autoplay on hover
        track.parentElement.addEventListener('mouseenter', stopAutoplay);
        track.parentElement.addEventListener('mouseleave', startAutoplay);
        
        // Additional features
        initTouchSupport();
        initKeyboardNavigation();
        initResizeHandler();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initReleasesCarousel);
    } else {
        initReleasesCarousel();
    }
    // ============================================================================
    // SEARCH FUNCTIONALITY
    // ============================================================================
    
    /**
     * Initializes global search functionality
     * @returns {void}
     */
    // ============================================================================
// SEARCH FUNCTIONALITY - COMPLETE FIXED VERSION
// ===========================================================================

    function initSearchFunctionality() {
        if (!document.getElementById('searchModal')) return;
        console.log('🔍 Initializing search functionality...');
        
        const searchModal = document.getElementById('searchModal');
        const searchInput = document.getElementById('globalSearchInput');
        const searchResults = document.getElementById('searchResults');
        const closeSearchBtn = document.getElementById('closeSearchModal');
        const searchTriggers = document.querySelectorAll('.search-trigger');
        
        let searchTimeout;
        
        if (!searchModal || !searchInput || !searchResults || !closeSearchBtn) {
            console.warn('⚠️ Search elements not found');
            return;
        }
        
        console.log('✅ Search elements found');
        
        /**
         * Opens search modal
         */
        function openSearch() {
            console.log('🔍 Opening search modal');
            searchModal.classList.add('active');
            setTimeout(() => {
                searchInput.focus();
            }, 100);
            document.body.style.overflow = 'hidden';
            
            if (searchInput.value.trim() === '') {
                loadRecentContent();
            }
        }
        
        /**
         * Closes search modal
         */
        function closeSearch() {
            searchModal.classList.remove('active');
            searchInput.value = '';
            document.body.style.overflow = '';
            searchResults.innerHTML = getEmptyState();
        }
        
        /**
         * Loads recent content for empty search state
         */
        function loadRecentContent() {
            console.log('📥 Loading recent content...');
            
            fetch('/api/search/videos/')
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    console.log('✅ Recent content loaded:', data);
                    displayRecentResults(data);
                })
                .catch(error => {
                    console.error('❌ Error loading recent content:', error);
                    searchResults.innerHTML = getErrorState();
                });
        }
        
        /**
         * Performs search with given query
         */
        function performSearch(query) {
            console.log('🔍 Searching for:', query);
            
            fetch(`/api/search/videos/?q=${encodeURIComponent(query)}`)
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    console.log('✅ Search results:', data);
                    displaySearchResults(data, query);
                })
                .catch(error => {
                    console.error('❌ Search error:', error);
                    searchResults.innerHTML = getErrorState();
                });
        }
        
        /**
         * Displays recent content results
         */
        function displayRecentResults(data) {
            let html = '<div class="search-header-info">Recent Content</div>';
            
            if (data.recent_videos && data.recent_videos.length > 0) {
                html += createSection('Videos', 'bi-play-btn-fill', data.recent_videos, false);
            }
            
            if (data.recent_shorts && data.recent_shorts.length > 0) {
                html += createSection('Shorts', 'bi-badge-vr-fill', data.recent_shorts, true);
            }
            
            if (!data.recent_videos?.length && !data.recent_shorts?.length) {
                html = getEmptyState('No recent content available');
            }
            
            searchResults.innerHTML = html;
        }
        
        /**
         * Displays search results
         */
        function displaySearchResults(data, query) {
            const totalResults = (data.videos?.length || 0) + 
                                (data.shorts?.length || 0) + 
                                (data.channels?.length || 0);
            
            let html = `
                <div class="search-header-info">
                    <span class="search-query">"${escapeHtml(query)}"</span>
                    <span class="search-count">${totalResults} results</span>
                </div>
            `;
            
            if (data.channels && data.channels.length > 0) {
                html += createChannelSection(data.channels);
            }
            
            if (data.videos && data.videos.length > 0) {
                html += createSection('Videos', 'bi-play-btn-fill', data.videos, false);
            }
            
            if (data.shorts && data.shorts.length > 0) {
                html += createSection('Shorts', 'bi-badge-vr-fill', data.shorts, true);
            }
            
            if (totalResults === 0) {
                html = getEmptyState(`No results found for "${escapeHtml(query)}"`);
            }
            
            searchResults.innerHTML = html;
        }
        
        /**
         * Creates channel section HTML
         */
        function createChannelSection(channels) {
            let html = '<div class="search-section">';
            html += '<div class="search-section-title"><i class="bi bi-collection-play"></i> Channels</div>';
            
            channels.forEach(channel => {
                const thumbnail = channel.thumbnail || '';
                const subscribers = formatNumber(channel.subscriber_count);
                const videos = formatNumber(channel.video_count);
                
                html += `
                    <div class="search-item channel-item" onclick="window.location.href='/channel/${channel.channel_id}/'">
                        <div class="search-item-image channel-avatar" ${!thumbnail ? 'style="background: linear-gradient(135deg, #ff1744, #d50000);"' : ''}>
                            ${thumbnail ? 
                                `<img src="${thumbnail}" alt="${escapeHtml(channel.name)}" loading="lazy">` : 
                                '<i class="bi bi-music-note-beamed" style="font-size: 2.5rem; color: white;"></i>'}
                        </div>
                        <div class="search-item-content">
                            <div class="search-item-title">
                                ${escapeHtml(channel.name)}
                                <span class="verified-badge"><i class="bi bi-patch-check-fill"></i></span>
                            </div>
                        </div>
                        <i class="bi bi-chevron-right" style="color: rgba(255,255,255,0.3); font-size: 1.5rem;"></i>
                    </div>
                `;
            });
            
            html += '</div>';
            return html;
        }
        
        /**
         * Creates a search results section
         */
        function createSection(title, icon, items, isShort) {
            let html = '<div class="search-section">';
            html += `<div class="search-section-title"><i class="bi ${icon}"></i> ${title}</div>`;
            
            items.forEach(item => {
                html += createVideoItem(item, isShort);
            });
            
            html += '</div>';
            return html;
        }
        
        /**
         * Creates a video item HTML
         */
        function createVideoItem(video, isShort) {
            const views = formatNumber(video.views);
            const likes = video.likes ? formatNumber(video.likes) : null;
            
            return `
                <div class="search-item video-item py-0 ${isShort ? 'short-item' : ''}" 
                    onclick="window.location.href='/channel/${video.channel_id}/video/${video.youtube_video_id}/'">
                    <div class="search-item-image ${isShort ? 'short-thumbnail' : ''}">
                        <img src="${video.thumbnail}" 
                            alt="${escapeHtml(video.title)}"
                            loading="lazy"
                            onerror="this.style.background='#1a1a1a'">
                        
                        <div class="duration-badge ${isShort ? 'short-badge' : ''}">
                            ${video.duration}
                        </div>
                        
                        <div class="play-overlay">
                            <i class="bi bi-play-circle-fill"></i>
                        </div>
                    </div>
                    
                    <div class="search-item-content">
                        <div class="search-item-title">
                            ${escapeHtml(video.title)}
                        </div>
                        
                    </div>
                    
                    <div class="search-item-action">
                        ${isShort ? 
                            '<span class="short-indicator px-2 py-1">Short</span>' : 
                            '<i class="bi bi-play-circle" style="color: #ff1744; font-size: 1.5rem;"></i>'}
                    </div>
                </div>
            `;
        }
        
        /**
         * Creates empty state HTML
         */
        function getEmptyState(message = 'Start typing to search...') {
            return `
                <div class="search-empty">
                    <i class="bi bi-search" style="font-size: 64px;"></i>
                    <p>${message}</p>
                    ${message.includes('No results') ? '<p class="search-tip">Try different keywords or check spelling</p>' : ''}
                </div>
            `;
        }
        
        /**
         * Creates loading state HTML
         */
        function getLoadingState() {
            return `
                <div class="search-loading">
                    <div class="loading-spinner"></div>
                    <p>Searching...</p>
                </div>
            `;
        }
        
        /**
         * Creates error state HTML
         */
        function getErrorState() {
            return `
                <div class="search-empty">
                    <i class="bi bi-exclamation-circle" style="font-size: 64px;"></i>
                    <p>Error loading results</p>
                    <p class="search-tip">Please try again</p>
                </div>
            `;
        }
        
        // ============================================================================
        // HELPER FUNCTIONS
        // ============================================================================
        
        function formatNumber(num) {
            if (!num && num !== 0) return '0';
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // ============================================================================
        // EVENT LISTENERS
        // ============================================================================
        
        // Mobile search triggers
        searchTriggers.forEach(trigger => {
            trigger.addEventListener('click', function(event) {
                event.preventDefault();
                console.log('📱 Mobile search clicked');
                openSearch();
            });
        });

        // Desktop search trigger - Wait for element to exist
        function attachDesktopTrigger() {
            const desktopTrigger = document.getElementById('desktopSearchTrigger');
            
            if (desktopTrigger) {
                console.log('✅ Desktop search trigger found');
                
                // Prevent default behavior
                desktopTrigger.addEventListener('mousedown', function(event) {
                    event.preventDefault();
                });
                
                // Handle click
                desktopTrigger.addEventListener('click', function(event) {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('🖥️ Desktop search clicked');
                    openSearch();
                });
                
                // Handle focus (if it's an input)
                desktopTrigger.addEventListener('focus', function(event) {
                    event.preventDefault();
                    console.log('🖥️ Desktop search focused');
                    this.blur();
                    openSearch();
                });
                
                return true;
            }
            
            console.warn('⚠️ Desktop search trigger not found yet');
            return false;
        }
        
        // Try to attach immediately
        if (!attachDesktopTrigger()) {
            // If not found, try again after delays
            setTimeout(attachDesktopTrigger, 100);
            setTimeout(attachDesktopTrigger, 500);
            setTimeout(attachDesktopTrigger, 1000);
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(event) {
            // Ctrl+K or Cmd+K to open search
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                console.log('⌨️ Keyboard shortcut triggered');
                openSearch();
            }
            // Escape to close
            if (event.key === 'Escape' && searchModal.classList.contains('active')) {
                closeSearch();
            }
        });
        
        // Close search
        closeSearchBtn.addEventListener('click', closeSearch);
        
        searchModal.addEventListener('click', (event) => {
            if (event.target === searchModal) {
                closeSearch();
            }
        });
        
        // Search input handler
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            clearTimeout(searchTimeout);
            
            if (query.length < 2) {
                loadRecentContent();
                return;
            }
            
            searchResults.innerHTML = getLoadingState();
            searchTimeout = setTimeout(() => performSearch(query), 300);
        });
        
        console.log('✅ Search functionality fully initialized');
    }

    // ============================================================================
    // CRITICAL: Export for use in DOMContentLoaded
    // ============================================================================

    // Make sure this function is available
    // window.initSearchFunctionality = initSearchFunctionality;
    
    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================
    
    /**
     * Sets sort parameter and reloads page
     * @param {string} sortValue - Sort value
     * @returns {boolean} false to prevent default
     */
    window.setSort = function(sortValue) {
        console.log('🔄 Setting sort to:', sortValue);
        
        const url = new URL(window.location.href);
        const params = new URLSearchParams(url.search);
        
        // Get current category
        const category = params.get('category') || 'all';
        
        // Update parameters
        params.set('sort', sortValue);
        params.set('category', category);
        params.set('page', '1'); // Reset to page 1
        
        // Navigate
        window.location.href = `${url.pathname}?${params.toString()}`;
        
        return false; // Prevent default
    };
    
    /**
     * Initializes stats counter animation
     * @returns {void}
     */
    function initStatsCounter() {
        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const statNumbers = entry.target.querySelectorAll('.stat-number');
                    statNumbers.forEach(stat => {
                        const text = stat.textContent;
                        const numericValue = parseInt(text.replace(/\D/g, ''));
                        const suffix = text.replace(/[0-9]/g, '');
                        
                        let count = 0;
                        const increment = numericValue / 100;
                        
                        const timer = setInterval(() => {
                            count += increment;
                            if (count >= numericValue) {
                                stat.textContent = numericValue + suffix;
                                clearInterval(timer);
                            } else {
                                stat.textContent = Math.floor(count) + suffix;
                            }
                        }, 20);
                    });
                    
                    statsObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        const statsSection = document.querySelector('.stats-section');
        if (statsSection) {
            statsObserver.observe(statsSection);
        }
    }
    
})(); // End of IIFE

// ============================================================================
// END OF FILE
// ============================================================================