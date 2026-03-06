// player.js
// Depends on utils.js (window.escapeHtml, window.formatNumber,
//                      window.formatNumDisplays, window.reinitializeTooltips)

(function () {
    'use strict';

    /* ============================================
       GET DATA FROM PAGE
    =========================================== */
    let currentChannelId = '';
    let currentVideoId   = '';

    const dataEl = document.querySelector('[data-channel-id]');
    if (dataEl) {
        currentChannelId = dataEl.getAttribute('data-channel-id') || '';
        currentVideoId   = dataEl.getAttribute('data-video-id')   || '';
    }
    if (!currentVideoId) {
        const playerEl = document.getElementById('player');
        if (playerEl) currentVideoId = playerEl.getAttribute('data-video-id') || '';
    }
    if (!currentChannelId || !currentVideoId) {
        const parts = window.location.pathname.split('/');
        const ci    = parts.indexOf('channel');
        if (ci !== -1 && parts.length > ci + 3) {
            currentChannelId = currentChannelId || parts[ci + 1];
            currentVideoId   = currentVideoId   || parts[ci + 3];
        }
    }

    console.log('🎬 Player initialized:', { channelId: currentChannelId, videoId: currentVideoId });

    /* ============================================
       STATE
    =========================================== */
    let player             = null;
    let ready              = false;
    let muted              = false;
    let vol                = 1;
    let progDrag           = false;
    let activityTimer      = null;
    let progressTimer      = null;
    let streamingVideos    = [];
    let unembeddableVideos = [];
    let isEmbedError       = false;
    let controlsVisible    = false;
    let isMobile           = window.innerWidth <= 767;
    let userInteracted     = false;

    /* ============================================
       DOM REFS
    =========================================== */
    const wrapper    = document.getElementById('vp-wrapper');
    const cover      = document.getElementById('vp-cover');
    const shield     = document.getElementById('vp-shield');
    const bigPlay    = document.getElementById('vp-big-play');
    const spinner    = document.getElementById('vp-spinner');
    const errorEl    = document.getElementById('vp-error');
    const controls   = document.getElementById('vp-controls');
    const progFill   = document.getElementById('vp-prog-fill');
    const progThumb  = document.getElementById('vp-prog-thumb');
    const progWrap   = document.getElementById('vp-prog-wrap');
    const timeEl     = document.getElementById('vp-time');
    const volFill    = document.getElementById('vp-vol-fill');
    const volThumb   = document.getElementById('vp-vol-thumb');
    const volTrack   = document.getElementById('vp-vol-track');
    const ppBtn      = document.getElementById('vp-playpause');
    const muteBtn    = document.getElementById('vp-mute');
    const fsBtn      = document.getElementById('vp-fs');
    const endScreen  = document.getElementById('vp-end-screen');
    const endGrid    = document.getElementById('vp-end-grid');
    const tapLeft    = document.getElementById('vp-tap-left');
    const tapRight   = document.getElementById('vp-tap-right');
    const shortsPrev = document.getElementById('shorts-nav-prev');
    const shortsNext = document.getElementById('shorts-nav-next');

    let mobileNavPrev = null;
    let mobileNavNext = null;

    const isShort = wrapper?.classList.contains('is-short') || false;

    /* ============================================
       HELPERS
    =========================================== */
    // FIX 1: On init, show spinner (not big play button) — hide bigPlay by default
    function showBigPlay() { if (bigPlay) bigPlay.classList.remove('hidden'); }
    function hideBigPlay() { if (bigPlay) bigPlay.classList.add('hidden'); }
    function showSpinner() { if (spinner) spinner.classList.add('show'); }
    function hideSpinner() { if (spinner) spinner.classList.remove('show'); }

    // Hide big play on page load so spinner shows during YT API init
    hideBigPlay();
    showSpinner();

    function setPP(playing) {
        if (!ppBtn) return;
        const pi = ppBtn.querySelector('.icon-play');
        const pa = ppBtn.querySelector('.icon-pause');
        if (pi) pi.style.display = playing ? 'none'  : 'block';
        if (pa) pa.style.display = playing ? 'block' : 'none';
    }

    function fmt(s) {
        s = Math.floor(s || 0);
        const m = Math.floor(s / 60), sec = s % 60;
        return m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    function togglePlay() {
        if (!ready || !player || isEmbedError) return;
        if (player.getPlayerState() === YT.PlayerState.PLAYING) {
            player.pauseVideo();
        } else {
            hideBigPlay(); showSpinner(); player.playVideo();
        }
    }

    function seekRelative(seconds) {
        if (!ready || !player) return;
        const cur = player.getCurrentTime(), dur = player.getDuration();
        player.seekTo(Math.max(0, Math.min(dur, cur + seconds)), true);
        const zone = seconds < 0 ? tapLeft : tapRight;
        if (zone) {
            zone.classList.add('active');
            setTimeout(() => zone.classList.remove('active'), 300);
        }
    }

    /* ============================================
       CONTROLS VISIBILITY
    =========================================== */
    function showControls(sticky = false) {
        if (!controls || isEmbedError) return;
        controls.classList.add('force-show');
        controls.style.opacity       = '1';
        controls.style.pointerEvents = 'auto';
        controlsVisible = true;
        if (activityTimer) clearTimeout(activityTimer);
        if (!sticky) activityTimer = setTimeout(hideControls, isMobile ? 3000 : 2000);
    }

    function hideControls() {
        if (!controls) return;
        controls.classList.remove('force-show');
        controls.style.opacity       = '0';
        controls.style.pointerEvents = 'none';
        controlsVisible = false;
        if (activityTimer) clearTimeout(activityTimer);
    }

    function resetActivityTimer() {
        if (!controls || isEmbedError) return;
        showControls(false);
    }

    if (wrapper && !isMobile) {
        wrapper.addEventListener('mousemove', () => { if (ready && player) showControls(false); });
        wrapper.addEventListener('mouseleave', () => {
            if (player && player.getPlayerState() === YT.PlayerState.PLAYING) hideControls();
        });
    }

    if (controls) {
        controls.addEventListener('mouseenter', () => { if (activityTimer) clearTimeout(activityTimer); });
        controls.addEventListener('mouseleave', () => {
            if (player && player.getPlayerState() === YT.PlayerState.PLAYING) resetActivityTimer();
        });
        controls.addEventListener('touchstart', (e) => {
            e.stopPropagation();
            if (activityTimer) clearTimeout(activityTimer);
        }, { passive: true });
    }

    /* ============================================
       CLICK / TAP HANDLING
    =========================================== */
    if (!isMobile && wrapper) {
        if (tapLeft)  tapLeft.addEventListener('click',  (e) => { e.preventDefault(); e.stopPropagation(); seekRelative(-10); resetActivityTimer(); });
        if (tapRight) tapRight.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); seekRelative(10);  resetActivityTimer(); });
        if (shield)   shield.addEventListener('click',   (e) => { e.preventDefault(); e.stopPropagation(); togglePlay();      resetActivityTimer(); });
    }

    if (isMobile && wrapper) {
        let touchStartX = 0, touchStartY = 0, touchStartTime = 0, touchMoved = false;

        wrapper.addEventListener('touchstart', (e) => {
            if (controls && controls.contains(e.target)) return;
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            touchMoved = false;
        }, { passive: true });

        wrapper.addEventListener('touchmove', (e) => {
            if (controls && controls.contains(e.target)) return;
            if (Math.abs(e.touches[0].clientX - touchStartX) > 8 ||
                Math.abs(e.touches[0].clientY - touchStartY) > 8) touchMoved = true;
        }, { passive: true });

        wrapper.addEventListener('touchend', (e) => {
            if (controls && controls.contains(e.target)) return;
            if (touchMoved || Date.now() - touchStartTime > 500) return;
            e.preventDefault();
            if (!controlsVisible) {
                showControls(false);
            } else {
                const endX  = e.changedTouches[0].clientX;
                const rect  = wrapper.getBoundingClientRect();
                const relX  = endX - rect.left;
                const third = rect.width / 3;
                if (relX < third)                   { seekRelative(-10); resetActivityTimer(); }
                else if (relX > rect.width - third)  { seekRelative(10);  resetActivityTimer(); }
                else                                 { togglePlay();       resetActivityTimer(); }
            }
        }, { passive: false });

        if (tapLeft)  tapLeft.style.pointerEvents  = 'none';
        if (tapRight) tapRight.style.pointerEvents = 'none';
        if (shield)   shield.style.pointerEvents   = 'none';
    }

    /* ============================================
       SHORTS NAVIGATION (mobile fix)
       FIX: Wire shorts prev/next with both click AND touchend
    =========================================== */
    function handleShortsNav(direction, e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        navigateShort(direction);
    }

    if (shortsPrev) {
        shortsPrev.addEventListener('click',    (e) => handleShortsNav('prev', e));
        shortsPrev.addEventListener('touchend', (e) => handleShortsNav('prev', e), { passive: false });
        shortsPrev.style.cssText += ';pointer-events:auto !important;touch-action:manipulation;cursor:pointer;';
    }
    if (shortsNext) {
        shortsNext.addEventListener('click',    (e) => handleShortsNav('next', e));
        shortsNext.addEventListener('touchend', (e) => handleShortsNav('next', e), { passive: false });
        shortsNext.style.cssText += ';pointer-events:auto !important;touch-action:manipulation;cursor:pointer;';
    }

    /* ============================================
       YOUTUBE API
    =========================================== */
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.getElementsByTagName('script')[0].parentNode.insertBefore(
            tag, document.getElementsByTagName('script')[0]);
    }

    window.onYouTubeIframeAPIReady = function () {
        console.log('🎬 YouTube API ready');
        const el  = document.getElementById('player');
        if (!el) return;
        const vid = el.getAttribute('data-video-id');
        if (!vid || vid.length !== 11) return;
        // FIX 1: Keep spinner visible, ensure big play stays hidden during init
        hideBigPlay();
        showSpinner();

        player = new YT.Player('player', {
            height: '100%', width: '100%', videoId: vid,
            playerVars: {
                autoplay: 1, controls: 0, modestbranding: 1, rel: 0,
                iv_load_policy: 3, enablejsapi: 1, disablekb: 1,
                fs: 0, playsinline: 1, cc_load_policy: 0
            },
            events: { onReady: onReady, onStateChange: onStateChange, onError: onError }
        });
    };

    function onReady() {
        ready = true;
        hideBigPlay(); hideSpinner();
        if (timeEl) timeEl.textContent = '0:00 / ' + fmt(player.getDuration());
        initVolSlider(); initProgressBar();
        try { if (player.getDuration() > 0) player.playVideo(); } catch (e) { console.error('Play error:', e); }
    }

    function onStateChange(e) {
        const S = YT.PlayerState;
        if (e.data === S.PLAYING) {
            if (cover) cover.classList.add('hidden');
            hideBigPlay(); hideSpinner(); setPP(true); startProgress(); hideEndScreen();
            isEmbedError = false;
            setTimeout(() => {
                if (player && player.getPlayerState() === S.PLAYING && !userInteracted) hideControls();
            }, 2000);
        } else if (e.data === S.PAUSED) {
            if (!isEmbedError) showBigPlay();
            hideSpinner(); setPP(false); stopProgress(); showControls(true);
        } else if (e.data === S.ENDED) {
            showBigPlay(); hideSpinner(); setPP(false); stopProgress();
            showControls(true); showEndScreen();
        } else if (e.data === S.BUFFERING) {
            if (!isEmbedError) { hideBigPlay(); showSpinner(); }
        } else if (e.data === S.CUED) {
            hideBigPlay(); showSpinner();
            setTimeout(() => {
                try { if (player && ready) player.playVideo(); } catch (err) {}
            }, 100);
        }
    }

    function onError(e) {
        hideSpinner(); hideBigPlay();
        console.error('YouTube error:', e.data);
        if (e.data === 101 || e.data === 150) { isEmbedError = true; autoSkipToNext(); }
        else {
            const m = document.getElementById('vp-error-msg');
            if (m) m.textContent = e.data === 100 ? 'Video unavailable' : 'Cannot play video';
            if (errorEl) errorEl.classList.add('show');
        }
    }

    /* ============================================
       PROGRESS BAR
    =========================================== */
    function initProgressBar() {
        if (!progWrap) return;
        progWrap.addEventListener('mousedown', startSeek);
        progWrap.addEventListener('touchstart', startSeek, { passive: false });
        progWrap.addEventListener('click', seek);
        document.addEventListener('mousemove', (e) => { if (progDrag) seek(e); });
        document.addEventListener('touchmove', (e) => {
            if (progDrag) { e.preventDefault(); seek(e.touches[0]); }
        }, { passive: false });
        document.addEventListener('mouseup', endSeek);
        document.addEventListener('touchend', endSeek);
    }

    function startSeek(e) { progDrag = true; seek(e); }
    function endSeek()    { progDrag = false; resetActivityTimer(); }

    function seek(e) {
        if (!ready || !player) return;
        e.preventDefault(); e.stopPropagation();
        const cx  = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
        const r   = progWrap.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (cx - r.left) / r.width));
        const t   = player.getDuration() * pct;
        player.seekTo(t, true);
        setProgUI(pct);
        if (timeEl) timeEl.textContent = fmt(t) + ' / ' + fmt(player.getDuration());
    }

    function startProgress() {
        stopProgress();
        progressTimer = setInterval(() => {
            if (!ready || !player || progDrag) return;
            try {
                const t = player.getCurrentTime(), dur = player.getDuration();
                setProgUI(dur ? t / dur : 0);
                if (timeEl) timeEl.textContent = fmt(t) + ' / ' + fmt(dur);
            } catch (e) {}
        }, 200);
    }

    function stopProgress() {
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
    }

    function setProgUI(pct) {
        const p = (pct * 100).toFixed(2) + '%';
        if (progFill)  progFill.style.width = p;
        if (progThumb) progThumb.style.left = p;
    }

    /* ============================================
       VOLUME
    =========================================== */
    function initVolSlider() {
        if (!volTrack) return;
        volTrack.addEventListener('click', applyVol);
        volTrack.addEventListener('touchstart', (e) => { e.preventDefault(); applyVol(e); }, { passive: false });
    }

    function applyVol(e) {
        if (!ready || !player) return;
        const cx = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
        const r  = volTrack.getBoundingClientRect();
        vol = Math.max(0, Math.min(1, (cx - r.left) / r.width));
        muted = (vol === 0);
        player.setVolume(vol * 100); updateVolUI(vol); resetActivityTimer();
    }

    function updateVolUI(v) {
        const p = (v * 100).toFixed(1) + '%';
        if (volFill)  volFill.style.width = p;
        if (volThumb) volThumb.style.left = p;
        if (!muteBtn) return;
        const u = muteBtn.querySelector('.icon-vol-up');
        const m = muteBtn.querySelector('.icon-vol-mute');
        if (u) u.style.display = v > 0 ? 'block' : 'none';
        if (m) m.style.display = v > 0 ? 'none'  : 'block';
    }

    if (muteBtn) {
        muteBtn.addEventListener('click', (e) => {
            e.preventDefault(); e.stopPropagation();
            if (!ready || !player) return;
            if (muted || vol === 0) { vol = 0.7; player.setVolume(70); muted = false; }
            else                    { muted = true; player.setVolume(0); }
            updateVolUI(muted ? 0 : vol); resetActivityTimer();
        });
    }

    if (ppBtn) {
        ppBtn.addEventListener('click', (e) => {
            e.preventDefault(); e.stopPropagation(); togglePlay(); resetActivityTimer();
        });
    }

    /* ============================================
       FULLSCREEN
    =========================================== */
    document.addEventListener('fullscreenchange', handleFSChange);
    document.addEventListener('webkitfullscreenchange', handleFSChange);

    function handleFSChange() {
        const inFS = !!(document.fullscreenElement || document.webkitFullscreenElement);
        if (inFS && screen.orientation?.lock)    screen.orientation.lock('landscape').catch(() => {});
        else if (!inFS && screen.orientation?.unlock) screen.orientation.unlock();
    }

    if (fsBtn) {
        fsBtn.addEventListener('click', (e) => {
            e.preventDefault(); e.stopPropagation();
            const w = document.getElementById('vp-wrapper'); if (!w) return;
            if (!document.fullscreenElement && !document.webkitFullscreenElement)
                (w.requestFullscreen || w.webkitRequestFullscreen || function () {}).call(w);
            else
                (document.exitFullscreen || document.webkitExitFullscreen || function () {}).call(document);
            resetActivityTimer();
        });
    }

    /* ============================================
       SHORTS NAVIGATION (function)
    =========================================== */
    function navigateShort(direction) {
        const shorts  = streamingVideos.filter(v => v.is_short);
        if (!shorts.length) return;
        const idx     = shorts.findIndex(v => v.youtube_video_id === currentVideoId);
        const safeIdx = idx === -1 ? 0 : idx;
        const newIdx  = direction === 'next'
            ? (safeIdx + 1) % shorts.length
            : (safeIdx - 1 + shorts.length) % shorts.length;
        if (shorts.length > 1 || idx === -1) loadVideo(shorts[newIdx].youtube_video_id);
    }

    /* ============================================
       VIDEO LOADING & INFO
    =========================================== */
    function loadVideo(videoId) {
        if (!player || !ready) return;
        console.log('▶️ loadVideo:', videoId);

        // FIX 2 & 3: Update currentVideoId BEFORE loading so end-screen
        // and any subsequent state can reference the new video correctly.
        currentVideoId = videoId;

        if (cover) cover.classList.remove('hidden');
        // FIX 1: Show spinner (not big play) when loading a new video
        hideBigPlay();
        showSpinner();
        hideEndScreen();

        player.loadVideoById(videoId);
        history.pushState({ videoId }, '', `/channel/${currentChannelId}/video/${videoId}/`);
        updateVideoInfo(videoId);
        scrollToPlayer();
        updateCurrentVideoBadge(videoId);
    }

    function scrollToPlayer() {
        if (wrapper) wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function updateCurrentVideoBadge(videoId) {
        document.querySelectorAll('.vid-card').forEach(card => {
            card.classList.remove('current-video');
            const b = card.querySelector('.vid-current-badge');
            if (b) b.remove();
        });
        const cur = document.querySelector(`.vid-card[data-video-id="${videoId}"]`);
        if (cur) {
            cur.classList.add('current-video');
            const tw = cur.querySelector('.vid-thumb-wrap');
            if (tw && !tw.querySelector('.vid-current-badge')) {
                const b = document.createElement('div');
                b.className = 'vid-current-badge'; b.textContent = 'Now Playing';
                tw.appendChild(b);
            }
        }
    }

    function updateVideoInfo(videoId) {
        const v = streamingVideos.find(v => v.youtube_video_id === videoId);
        if (!v) return;

        const t = document.querySelector('.vp-info-title');
        if (t) t.textContent = v.title;

        const d = document.querySelector('.vp-info-meta span:nth-child(2)');
        if (d) {
            const date = new Date(v.published_at);
            d.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg> '
                + date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        }

        const ve = document.querySelector('.vp-info-meta span:nth-child(3)');
        if (ve) {
            const fmtN = (typeof window.formatNumber === 'function') ? window.formatNumber : (n => n);
            const raw  = v.view_count || 0;
            ve.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg> '
                + fmtN(raw) + ' views';
            ve.setAttribute('data-bs-toggle', 'tooltip');
            ve.setAttribute('data-bs-placement', 'top');
            ve.setAttribute('title', raw.toLocaleString() + ' views');
        }

        const infoCard = document.querySelector('.vp-info-card');
        if (infoCard && typeof window.reinitializeTooltips === 'function') {
            window.reinitializeTooltips(infoCard);
        }
    }

    window.addEventListener('popstate', (e) => {
        if (e.state && e.state.videoId) loadVideo(e.state.videoId);
    });

    /* ============================================
       AUTO SKIP
    =========================================== */
    function autoSkipToNext() {
        const avail = streamingVideos.filter(v => !unembeddableVideos.includes(v.youtube_video_id));
        if (!avail.length) { if (errorEl) errorEl.classList.add('show'); return; }
        if (cover) cover.classList.remove('hidden');
        hideBigPlay(); showSpinner();
        if (errorEl) errorEl.classList.remove('show');
        setTimeout(() => { loadVideo(avail[0].youtube_video_id); }, 2000);
    }

    /* ============================================
       END SCREEN
    =========================================== */
    let endScreenIndex = 0;
    let endSuggestions = [];

    /* -- build a single end-screen card -------- */
    function buildEndCard(video, idx) {
        const esc  = (typeof window.escapeHtml === 'function') ? window.escapeHtml : (t => String(t).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
        const card = document.createElement('div');
        card.className = 'vp-end-video-card';
        card.setAttribute('data-video-id', video.youtube_video_id);
        card.setAttribute('data-end-idx', idx);

        const thumbStyle = (isShort && !isMobile)
            ? 'style="aspect-ratio:9/16;max-height:140px;overflow:hidden;"'
            : 'style="aspect-ratio:16/9;overflow:hidden;"';

        const rawTitle     = video.title || '';
        const displayTitle = rawTitle.length > 55 ? rawTitle.slice(0, 52) + '…' : rawTitle;

        card.innerHTML = `
            <div class="vp-end-thumb-wrap" ${thumbStyle}>
                <img src="${video.thumbnail_url}" loading="lazy" alt="${esc(rawTitle)}"
                     style="width:100%;height:100%;object-fit:cover;display:block;pointer-events:none;">
            </div>
            <div class="vp-end-video-title"
                 style="color:#fff;padding:0px;font-size:12px;font-weight:500;
                        line-height:1.4;word-break:break-word;overflow-wrap:break-word;
                        display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
                        overflow:hidden;">${esc(displayTitle)}</div>
        `;

        // Store the target videoId directly on element
        card.dataset.videoId = video.youtube_video_id;

        // FIX 2 & 3: Use both click and touchend, capture videoId from dataset at event time
        function handleCardActivation(e) {
            e.preventDefault();
            e.stopPropagation();
            const targetId = card.dataset.videoId;
            console.log('🎬 End card activated, loading:', targetId);
            loadVideo(targetId);
        }

        card.addEventListener('click', handleCardActivation);
        card.addEventListener('touchend', function(e) {
            // Only fire if it's a tap (not a scroll)
            handleCardActivation(e);
        }, { passive: false });

        card.style.cursor = 'pointer';
        card.style.cssText += ';-webkit-tap-highlight-color:rgba(255,255,255,0.1);touch-action:manipulation;';
        return card;
    }

    /* -- create mobile overlay nav buttons ----- */
    function createMobileNavButtons() {
        if (!wrapper) return;

        destroyMobileNavButtons();

        const existingPrev = document.getElementById('vp-nav-prev');
        const existingNext = document.getElementById('vp-nav-next');

        function wireBtn(btn, direction) {
            if (!btn) return null;
            const fresh = btn.cloneNode(true);
            btn.parentNode.replaceChild(fresh, btn);

            fresh.style.cssText += ';pointer-events:auto !important;cursor:pointer;position:relative;z-index:9999;touch-action:manipulation;-webkit-tap-highlight-color:transparent;';

            function handleNav(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('📱 Nav btn activated:', direction, 'idx before:', endScreenIndex);
                scrollEndGridToIndex(endScreenIndex + (direction === 'next' ? 1 : -1));
            }

            fresh.addEventListener('click', handleNav);
            fresh.addEventListener('touchend', handleNav, { passive: false });
            return fresh;
        }

        mobileNavPrev = wireBtn(existingPrev, 'prev');
        mobileNavNext = wireBtn(existingNext, 'next');

        const navContainer = (mobileNavPrev || mobileNavNext)?.closest('.vp-mobile-nav') ||
                             document.getElementById('vp-mobile-nav');
        if (navContainer) {
            navContainer.style.cssText += ';pointer-events:none;display:flex;z-index:9999;';
        }
    }

    function destroyMobileNavButtons() {
        mobileNavPrev = null;
        mobileNavNext = null;
    }

    /* -- show end screen ----------------------- */
    function showEndScreen() {
        if (!endScreen || !endGrid || !streamingVideos.length) return;

        const avail = streamingVideos.filter(v => !unembeddableVideos.includes(v.youtube_video_id));
        if (!avail.length) return;

        endGrid.innerHTML = '';
        endScreenIndex    = 0;
        endSuggestions    = avail.filter(v => v.youtube_video_id !== currentVideoId).slice(0, 6);

        endSuggestions.forEach((video, idx) => endGrid.appendChild(buildEndCard(video, idx)));

        if (!isMobile) {
            // Desktop: 3-col grid
            endGrid.style.cssText = `
                display:grid;
                grid-template-columns:repeat(3,1fr);
                gap:14px;
                width:100%;
                max-width:860px;
                overflow-y:auto;
                overflow-x:hidden;
                max-height:calc(100% - 24px);
            `;
        } else {
            // FIX 4: Mobile — full-width cards (one per "slide"), horizontal snap scroll
            endGrid.style.cssText = `
                display:flex;
                flex-direction:row;
                overflow-x:auto;
                overflow-y:hidden;
                scroll-snap-type:x mandatory;
                -webkit-overflow-scrolling:touch;
                scrollbar-width:none;
                gap:0px;
                padding:6px 0;
                width:100%;
                align-items:flex-start;
                box-sizing:border-box;
            `;
            endGrid.style.msOverflowStyle = 'none';

            // Set card widths to full wrapper width after layout
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const gridW = endGrid.offsetWidth || (wrapper ? wrapper.offsetWidth : window.innerWidth);
                    // FIX 4: Use 100% width so each card fills the screen, no peeking
                    const cardW = gridW;
                    endGrid.querySelectorAll('.vp-end-video-card').forEach(card => {
                        card.style.flex      = `0 0 ${cardW}px`;
                        card.style.maxWidth  = `${cardW}px`;
                        card.style.minWidth  = `${cardW}px`;
                        card.style.width     = `${cardW}px`;
                        card.style.scrollSnapAlign = 'start';
                        card.style.padding   = '0 12px';
                        card.style.boxSizing = 'border-box';
                    });
                    endGrid.style.paddingLeft  = '0';
                    endGrid.style.paddingRight = '0';
                    endGrid.scrollLeft = 0;
                    console.log('📱 End grid built (full-width): gridW', gridW, 'cardW', cardW);
                });
            });

            createMobileNavButtons();
        }

        endScreen.classList.add('show');
        showControls(true);

        const mobileNavContainer = document.getElementById('vp-mobile-nav');
        if (mobileNavContainer) {
            mobileNavContainer.style.display = isMobile && endSuggestions.length > 1 ? 'flex' : 'none';
        }
    }

    function hideEndScreen() {
        if (endScreen) endScreen.classList.remove('show');
        endScreenIndex = 0;
        destroyMobileNavButtons();
    }

    /* -- scroll grid to card index ------------- */
    function scrollEndGridToIndex(idx) {
        if (!endGrid || !endSuggestions.length) return;
        idx = Math.max(0, Math.min(endSuggestions.length - 1, idx));
        endScreenIndex = idx;

        const cards = endGrid.querySelectorAll('.vp-end-video-card');
        if (!cards.length) return;

        const cardW = cards[0].offsetWidth;
        if (cardW === 0) {
            const gridW   = endGrid.offsetWidth || window.innerWidth;
            endGrid.scrollTo({ left: idx * gridW, behavior: 'smooth' });
            return;
        }

        // FIX 4: With full-width cards and no gap, scrollLeft = idx * cardW
        const computedGap = parseInt(window.getComputedStyle(endGrid).gap || '0') || 0;
        const scrollLeft  = idx * (cardW + computedGap);
        console.log('📱 Scroll → idx', idx, 'cardW', cardW, 'gap', computedGap, 'scrollLeft', scrollLeft);
        endGrid.scrollTo({ left: scrollLeft, behavior: 'smooth' });
    }

    /* ============================================
       LOAD STREAMING DATA
    =========================================== */
    function loadStreamingData() {
        const el = document.getElementById('streaming-data');
        if (el) {
            try {
                streamingVideos = JSON.parse(el.textContent);
                console.log('📊 Streaming data loaded:', streamingVideos.length, 'videos');
            } catch (e) { console.error('Error parsing streaming data', e); }
        } else { console.warn('⚠️ Streaming data element not found'); }
    }

    window.addEventListener('resize', () => { isMobile = window.innerWidth <= 767; });
    loadStreamingData();

    /* ============================================
       INIT RELATED VIDEO CARDS
    =========================================== */
    document.addEventListener('DOMContentLoaded', () => {
        console.log('🎬 Player DOM loaded');
        setTimeout(() => {
            document.querySelectorAll('.vid-card:not(.current-video)').forEach(card => {
                const link = card.querySelector('a');
                if (!link) return;
                const m = (link.getAttribute('href') || '').match(/\/video\/([^\/]+)/);
                if (!m) return;
                const videoId = m[1];
                card.setAttribute('data-video-id', videoId);
                const parent = link.parentNode;
                while (link.firstChild) parent.insertBefore(link.firstChild, link);
                link.remove();
                card.addEventListener('click', (e) => {
                    e.preventDefault(); e.stopPropagation();
                    const id = card.getAttribute('data-video-id');
                    if (id && id !== currentVideoId) loadVideo(id);
                });
                card.style.cursor = 'pointer';
            });
        }, 500);
    });

})();