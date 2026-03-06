// navbar.js - Shared between channel and player pages
// Contains: search modal functionality

(function() {
    'use strict';

    // ============================================================================
    // SEARCH MODAL FUNCTIONALITY
    // ============================================================================
    let searchModal, searchInput, searchResults, searchTimeout;
    let searchInitialized = false;

    function initSearch() {
        if (searchInitialized) return;
        
        searchModal = document.getElementById('searchModal');
        searchInput = document.getElementById('globalSearchInput');
        searchResults = document.getElementById('searchResults');
        const closeBtn = document.getElementById('closeSearchModal');
        const searchTriggers = document.querySelectorAll('.search-trigger, #desktopSearchTrigger');

        if (!searchModal || !searchInput || !searchResults || !closeBtn) {
            console.warn('Search elements not found');
            return;
        }

        searchInitialized = true;
        console.log('🔍 Search initialized');

        function openSearch() {
            searchModal.classList.add('active');
            setTimeout(() => searchInput.focus(), 100);
            document.body.style.overflow = 'hidden';
            if (!searchInput.value.trim()) loadRecentContent();
        }

        function closeSearch() {
            searchModal.classList.remove('active');
            searchInput.value = '';
            document.body.style.overflow = '';
            searchResults.innerHTML = getEmptyState();
        }

        function loadRecentContent() {
            fetch('/api/search/videos/')
                .then(res => res.json())
                .then(data => displayRecentResults(data))
                .catch(() => searchResults.innerHTML = getErrorState());
        }

        function performSearch(query) {
            fetch(`/api/search/videos/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => displaySearchResults(data, query))
                .catch(() => searchResults.innerHTML = getErrorState());
        }

        function displayRecentResults(data) {
            let html = '<div class="search-header-info">Recent Content</div>';
            if (data.recent_videos?.length) {
                html += createSection('Videos', 'bi-play-btn-fill', data.recent_videos, false);
            }
            if (data.recent_shorts?.length) {
                html += createSection('Shorts', 'bi-badge-vr-fill', data.recent_shorts, true);
            }
            searchResults.innerHTML = html || getEmptyState('No recent content');
        }

        function displaySearchResults(data, query) {
            const videos = data.videos || [];
            const shorts = data.shorts || [];
            const channels = data.channels || [];
            const total = videos.length + shorts.length + channels.length;

            let html = `
                <div class="search-header-info">
                    <span class="search-query">"${escapeHtml(query)}"</span>
                    <span class="search-count">${total} result${total !== 1 ? 's' : ''}</span>
                </div>
            `;

            if (channels.length) html += createChannelSection(channels, query);
            if (videos.length) html += createSection('Videos', 'bi-play-btn-fill', videos, false, query);
            if (shorts.length) html += createSection('Shorts', 'bi-badge-vr-fill', shorts, true, query);

            searchResults.innerHTML = html || getEmptyState(`No results found`);
        }

        function createChannelSection(channels, query) {
            let html = '<div class="search-section"><div class="search-section-title"><i class="bi bi-collection-play"></i> Channels</div>';
            channels.forEach(c => {
                html += `
                    <div class="search-item channel-item" onclick="window.location.href='/channel/${c.channel_id}/'">
                        <div class="search-item-image channel-avatar" ${!c.thumbnail ? 'style="background:linear-gradient(135deg,#ff1744,#d50000)"' : ''}>
                            ${c.thumbnail ? `<img src="${c.thumbnail}" alt="${escapeHtml(c.name)}">` : '<i class="bi bi-music-note-beamed" style="font-size:2.5rem;color:#fff"></i>'}
                        </div>
                        <div class="search-item-content">
                            <div class="search-item-title">${query ? highlightMatch(c.name, query) : escapeHtml(c.name)}<span class="verified-badge"><i class="bi bi-patch-check-fill"></i></span></div>
                        </div>
                        <i class="bi bi-chevron-right" style="color:rgba(255,255,255,0.3);font-size:1.5rem"></i>
                    </div>
                `;
            });
            return html + '</div>';
        }

        function createSection(title, icon, items, isShort, query) {
            let html = `<div class="search-section"><div class="search-section-title"><i class="bi ${icon}"></i> ${title}</div>`;
            items.forEach(item => { html += createVideoItem(item, isShort, query); });
            return html + '</div>';
        }

        function createVideoItem(video, isShort, query) {
            return `
                <div class="search-item video-item py-0 ${isShort ? 'short-item' : ''}" onclick="window.location.href='/channel/${video.channel_id}/video/${video.youtube_video_id}/'">
                    <div class="search-item-image ${isShort ? 'short-thumbnail' : ''}">
                        <img src="${video.thumbnail}" alt="${escapeHtml(video.title)}" loading="lazy">
                        <div class="duration-badge ${isShort ? 'short-badge' : ''}">${video.duration}</div>
                        <div class="play-overlay"><i class="bi bi-play-circle-fill"></i></div>
                    </div>
                    <div class="search-item-content">
                        <div class="search-item-title">${query ? highlightMatch(video.title, query) : escapeHtml(video.title)}</div>
                        <div class="search-item-channel">${query ? highlightMatch(video.channel_name, query) : escapeHtml(video.channel_name)}</div>
                        <div class="search-item-date small text-secondary"><i class="bi bi-calendar3 small"></i> ${video.published}</div>
                    </div>
                    <div class="search-item-action">${isShort ? '<span class="short-indicator px-2 py-1">Short</span>' : '<i class="bi bi-play-circle" style="color:#ff1744;font-size:1.5rem"></i>'}</div>
                </div>
            `;
        }

        function highlightMatch(text, query) {
            if (!text || !query) return escapeHtml(text);
            const words = query.toLowerCase().split(/\s+/).filter(w => w.length);
            if (!words.length) return escapeHtml(text);

            const escaped = escapeHtml(text);
            const parts = escaped.split(/(\s+|[.,!?;:-])/);

            for (let i = 0; i < parts.length; i++) {
                const word = parts[i].toLowerCase();
                for (const q of words) {
                    if (word.startsWith(q) && parts[i].length) {
                        parts[i] = `<mark class="search-highlight">${parts[i].slice(0, q.length)}</mark>${parts[i].slice(q.length)}`;
                        break;
                    }
                }
            }
            return parts.join('');
        }

        function getEmptyState(msg = 'Start typing to search...') {
            return `<div class="search-empty"><i class="bi bi-search" style="font-size:64px"></i><p>${msg}</p>${msg.includes('No results') ? '<p class="search-tip">Try different keywords</p>' : ''}</div>`;
        }

        function getLoadingState() {
            return `<div class="search-loading"><div class="loading-spinner"></div><p>Searching...</p></div>`;
        }

        function getErrorState() {
            return `<div class="search-empty"><i class="bi bi-exclamation-circle" style="font-size:64px"></i><p>Error loading results</p><p class="search-tip">Please try again</p></div>`;
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Event listeners
        searchTriggers.forEach(trigger => {
            if (trigger) {
                trigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    openSearch();
                });
            }
        });

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

        closeBtn.addEventListener('click', closeSearch);
        searchModal.addEventListener('click', (e) => { if (e.target === searchModal) closeSearch(); });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                openSearch();
            }
            if (e.key === 'Escape' && searchModal.classList.contains('active')) {
                closeSearch();
            }
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        console.log('🔧 Navbar JS initialized');
        initSearch();
    });

})();