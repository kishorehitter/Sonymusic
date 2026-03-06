// home.js - Only for homepage (menu.html)
// Contains: channels dropdown modal, carousel, SVG animation, artist marquee, enquiry modal

(function() {
    'use strict';

    // ============================================================================
    // ENQUIRY MODAL FUNCTIONS
    // ============================================================================
    window.openEnquiryModal = function(type, email) {
        console.log('📧 Opening enquiry modal for:', type);
        
        const modal = document.getElementById('enquiryModal');
        if (!modal) {
            console.error('❌ Enquiry modal not found');
            return;
        }
        
        // Set modal title and subject
        const titleEl = document.getElementById('enquiryModalTitle');
        const subjectEl = document.getElementById('enquirySubject');
        if (titleEl) titleEl.textContent = type + ' Enquiry';
        if (subjectEl) subjectEl.value = type + ' Enquiry — Sony Music India';
        
        // Reset form
        const nameEl = document.getElementById('enquiryName');
        const emailEl = document.getElementById('enquiryEmail');
        const msgEl = document.getElementById('enquiryMessage');
        if (nameEl) nameEl.value = '';
        if (emailEl) emailEl.value = '';
        if (msgEl) msgEl.value = '';
        
        // Show/hide sections
        const formArea = document.getElementById('enquiryFormArea');
        const successArea = document.getElementById('enquirySuccess');
        const errorArea = document.getElementById('enquiryError');
        const footer = document.getElementById('enquiryFooter');
        
        if (formArea) formArea.classList.remove('d-none');
        if (successArea) successArea.classList.add('d-none');
        if (errorArea) errorArea.classList.add('d-none');
        if (footer) footer.classList.remove('d-none');
        
        // Reset send button
        const sendBtn = document.getElementById('enquirySendBtn');
        if (sendBtn) {
            sendBtn.innerHTML = '<i class="bi bi-send me-1"></i> Send Message';
            sendBtn.disabled = false;
        }
        
        // Open Bootstrap modal
        try {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        } catch (e) {
            console.error('❌ Error opening modal:', e);
        }
    };

    window.submitEnquiry = function() {
        const name    = document.getElementById('enquiryName')?.value.trim();
        const email   = document.getElementById('enquiryEmail')?.value.trim();
        const subject = document.getElementById('enquirySubject')?.value.trim();
        const message = document.getElementById('enquiryMessage')?.value.trim();
        const errorEl = document.getElementById('enquiryError');
        const sendBtn = document.getElementById('enquirySendBtn');

        // Validation
        if (errorEl) errorEl.classList.add('d-none');
        
        if (!name) {
            if (errorEl) {
                errorEl.textContent = 'Please enter your name.';
                errorEl.classList.remove('d-none');
            }
            return;
        }
        if (!email || !email.includes('@')) {
            if (errorEl) {
                errorEl.textContent = 'Please enter a valid email address.';
                errorEl.classList.remove('d-none');
            }
            return;
        }
        if (!message) {
            if (errorEl) {
                errorEl.textContent = 'Please enter your message.';
                errorEl.classList.remove('d-none');
            }
            return;
        }

        // Loading state
        if (sendBtn) {
            sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Sending...';
            sendBtn.disabled = true;
        }

        fetch('/api/enquiry/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ name, email, subject, message })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Show success
                const formArea = document.getElementById('enquiryFormArea');
                const successArea = document.getElementById('enquirySuccess');
                const footer = document.getElementById('enquiryFooter');
                if (formArea) formArea.classList.add('d-none');
                if (footer) footer.classList.add('d-none');
                if (successArea) successArea.classList.remove('d-none');
            } else {
                throw new Error(data.error || 'Failed to send');
            }
        })
        .catch(err => {
            if (errorEl) {
                errorEl.textContent = err.message || 'Network error. Please try again.';
                errorEl.classList.remove('d-none');
            }
            if (sendBtn) {
                sendBtn.innerHTML = '<i class="bi bi-send me-1"></i> Send Message';
                sendBtn.disabled = false;
            }
        });
    };

    function getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) return value;
        }
        return '';
    }

    // ============================================================================
    // CHANNELS DROPDOWN + MODAL (from menu.html)
    // ============================================================================
    let _activeCh = null;
    let _ytPopup = null;
    let _killAt = 0;
    let _ticker = null;
    let _cdSecs = 10;
    let _descFull = false;
    const POPUP_SECS = 10;
    const DESC_TRIM = 160;
    const LS_SUB = 'sny_sub_state';
    let _CHANNELS = [];

    function lsGet() { try { return JSON.parse(localStorage.getItem(LS_SUB) || '{}'); } catch (e) { return {}; } }
    function lsSet(id, val) { try { const d = lsGet(); d[id] = val; localStorage.setItem(LS_SUB, JSON.stringify(d)); } catch (e) { } }
    function lsRead(id) { const d = lsGet(); return id in d ? d[id] : null; }

    function buildDropdown(channels) {
        const menu = document.getElementById('channelsDropdownMenu');
        if (!menu) return;
        if (!channels || !channels.length) {
            menu.innerHTML = '<li class="sny-dd-loading">No channels found.</li>';
            return;
        }
        let html = '';
        channels.forEach((ch, idx) => {
            const safe = window.escapeHtml ? window.escapeHtml(ch.name) : ch.name;
            const chId = ch.youtube_channel_id || ch.id || String(idx);
            const badge = lsRead(chId) === true ? '<span class="sny-row-badge">Subscribed</span>' : '';
            html += '<li><button class="sny-ch-row" id="sny-row-' + idx + '" onclick="window._snyOpen(' + idx + ')">'
                + '<span class="sny-row-dot"></span>'
                + '<img class="sny-row-thumb" src="' + (ch.thumbnail_url || '') + '" alt="' + safe + '" onerror="this.style.visibility=\'hidden\'">'
                + '<div class="sny-row-info"><div class="sny-row-name">' + safe + '</div>'
                + '<div class="sny-row-subs">' + (window.formatNumber ? window.formatNumber(ch.subscriber_count) : ch.subscriber_count) + ' subscribers</div></div>'
                + badge + '</button></li>';
        });
        menu.innerHTML = html;
    }

    function fetchChannels() {
        fetch('/api/channels/dropdown/')
            .then(r => { if (!r.ok) throw 0; return r.json(); })
            .then(d => { _CHANNELS = d.channels || []; buildDropdown(_CHANNELS); })
            .catch(() => {
                const m = document.getElementById('channelsDropdownMenu');
                if (m) m.innerHTML = '<li class="sny-dd-loading" style="color:#f66">Failed to load.</li>';
            });
    }

    window._snyOpen = function(idx) {
        const ch = _CHANNELS[idx];
        if (!ch) return;
        _activeCh = ch;
        _descFull = false;
        tickerStop();
        popupKill();
        const countdown = document.getElementById('snyCountdown');
        const askCard = document.getElementById('snyAskCard');
        if (countdown) countdown.style.display = 'none';
        if (askCard) askCard.style.display = 'none';
        setSubBtn(lsRead(ch.youtube_channel_id || ch.id || String(idx)));
        const overlay = document.getElementById('snyOverlay');
        if (overlay) overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
        const skeleton = document.getElementById('snySkeleton');
        const content = document.getElementById('snyContent');
        if (skeleton) skeleton.style.display = 'flex';
        if (content) content.style.display = 'none';
        setTimeout(() => { fillModal(ch); if (skeleton) skeleton.style.display = 'none'; if (content) content.style.display = 'block'; }, 280);
    };

    function fillModal(ch) {
        const img = document.getElementById('snyAvatarImg');
        const fb = document.getElementById('snyAvatarFb');
        if (!img || !fb) return;

        if (ch.thumbnail_url) {
            img.src = ch.thumbnail_url;
            img.alt = ch.name;
            img.style.display = 'block';
            fb.style.display = 'none';
        } else {
            img.style.display = 'none';
            fb.textContent = (ch.name || '?')[0].toUpperCase();
            fb.style.display = 'flex';
        }

        const nameEl = document.getElementById('snyCHName');
        if (nameEl) {
            nameEl.innerHTML = (window.escapeHtml ? window.escapeHtml(ch.name) : ch.name) +
                '<span class="sny-verified" title="Verified"><svg viewBox="0 0 24 24" fill="#0f0f0f"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg></span>';
        }
        const handleEl = document.getElementById('snyCHHandle');
        if (handleEl) handleEl.textContent = ch.handle || '';
        const statsEl = document.getElementById('snyCHStats');
        if (statsEl) {
            statsEl.textContent = [(window.formatNumber ? window.formatNumber(ch.subscriber_count) : ch.subscriber_count) + ' subscribers',
                ch.video_count ? (window.formatNumber ? window.formatNumber(ch.video_count) : ch.video_count) + ' videos' : ''].filter(Boolean).join(' · ');
        }
        renderDesc(ch.description || '');
    }

    function setSubBtn(state) {
        const btn = document.getElementById('snySubBtn');
        if (!btn) return;
        btn.className = 'sny-sub-btn';
        btn.onclick = window.launchSubscribe;
        btn.title = '';
        if (state === true) {
            btn.innerHTML = '&#x2714; Subscribed';
            btn.classList.add('is-subscribed');
            btn.title = 'Click to update';
        } else {
            btn.innerHTML = 'Subscribe';
        }
    }

    function setSubBtnWaiting() {
        const btn = document.getElementById('snySubBtn');
        if (!btn) return;
        btn.className = 'sny-sub-btn is-waiting';
        btn.innerHTML = 'YouTube is open&#8230;';
        btn.onclick = null;
    }

    window.launchSubscribe = function() {
        if (!_activeCh) return;
        const askCard = document.getElementById('snyAskCard');
        if (askCard) askCard.style.display = 'none';
        const base = _activeCh.youtube_url || ('https://www.youtube.com/channel/' + _activeCh.youtube_channel_id);
        const url = base + (base.indexOf('?') >= 0 ? '&' : '?') + 'sub_confirmation=1';

        if (/Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || window.innerWidth < 768) {
            showMobileSheet(url);
            return;
        }
        const pw = 500, ph = 320;
        _ytPopup = window.open(url, 'sny_yt',
            'width=' + pw + ',height=' + ph + ',left=' + Math.round(screen.width / 2 - pw / 2) + ',top=' + Math.round(screen.height / 2 - ph / 2) + ',toolbar=no,menubar=no,scrollbars=yes,resizable=no');
        if (!_ytPopup || _ytPopup.closed) {
            _ytPopup = null;
            window.open(url, '_blank');
        }

        _killAt = Date.now() + POPUP_SECS * 1000;
        _cdSecs = POPUP_SECS;
        const countdown = document.getElementById('snyCountdown');
        if (countdown) countdown.style.display = 'block';
        updateCDUI();
        setSubBtnWaiting();
        tickerStop();
        _ticker = setInterval(onTick, 500);
    };

    function onTick() {
        const now = Date.now();
        if (now >= _killAt) { tickerStop(); popupKill(); onPopupDone(); return; }
        if (_ytPopup && _ytPopup.closed) { tickerStop(); _ytPopup = null; onPopupDone(); return; }
        const s = Math.ceil((_killAt - now) / 1000);
        if (s !== _cdSecs) { _cdSecs = s; updateCDUI(); }
    }

    function updateCDUI() {
        const e = document.getElementById('snySeconds');
        const b = document.getElementById('snyCDBar');
        if (e) e.textContent = _cdSecs;
        if (b) b.style.width = ((_cdSecs / POPUP_SECS) * 100) + '%';
    }

    function onPopupDone() {
        const countdown = document.getElementById('snyCountdown');
        if (countdown) countdown.style.display = 'none';
        showAskCard();
    }

    function tickerStop() { if (_ticker) { clearInterval(_ticker); _ticker = null; } }
    function popupKill() { if (_ytPopup && !_ytPopup.closed) { try { _ytPopup.close(); } catch (e) { } } _ytPopup = null; }
    window.addEventListener('beforeunload', popupKill);

    window.snyForceClose = function() { tickerStop(); popupKill(); const c = document.getElementById('snyCountdown'); if (c) c.style.display = 'none'; showAskCard(); };
    window.snyReopen = function() { tickerStop(); popupKill(); if (_activeCh) window.launchSubscribe(); };

    function showAskCard() {
        const chId = _activeCh ? (_activeCh.youtube_channel_id || _activeCh.id || '') : '';
        const prev = lsRead(chId);
        const titleEl = document.getElementById('snyAskTitle');
        const subEl = document.getElementById('snyAskSub');
        if (titleEl) titleEl.textContent = prev === true ? 'Did you unsubscribe?' : 'Did you subscribe?';
        if (subEl) subEl.textContent = prev === true ? 'Update your status below.' : 'Let us know so we remember.';
        const askCard = document.getElementById('snyAskCard');
        if (askCard) askCard.style.display = 'block';
        setSubBtn(prev);
    }

    window.snyAnswerYes = function() {
        if (!_activeCh) return;
        const chId = _activeCh.youtube_channel_id || _activeCh.id || '';
        lsSet(chId, true);
        const askCard = document.getElementById('snyAskCard');
        if (askCard) askCard.style.display = 'none';
        setSubBtn(true);
        refreshBadge(chId, true);
        showToast('Subscribed to ' + _activeCh.name);
    };

    window.snyAnswerNo = function() {
        if (!_activeCh) return;
        const chId = _activeCh.youtube_channel_id || _activeCh.id || '';
        lsSet(chId, false);
        const askCard = document.getElementById('snyAskCard');
        if (askCard) askCard.style.display = 'none';
        setSubBtn(false);
        refreshBadge(chId, false);
    };

    function refreshBadge(chId, sub) {
        _CHANNELS.forEach((ch, idx) => {
            const rowId = ch.youtube_channel_id || ch.id || String(idx);
            if (rowId !== chId) return;
            const row = document.getElementById('sny-row-' + idx);
            if (!row) return;
            const badge = row.querySelector('.sny-row-badge');
            if (sub) {
                if (!badge) {
                    const newBadge = document.createElement('span');
                    newBadge.className = 'sny-row-badge';
                    newBadge.textContent = 'Subscribed';
                    row.appendChild(newBadge);
                }
            } else {
                if (badge) badge.remove();
            }
        });
    }

    function showMobileSheet(url) {
        const cd = document.getElementById('snyCountdown');
        if (!cd) return;
        cd.style.display = 'block';
        cd.innerHTML = '<div class="sny-mobile-sheet">'
            + '<div class="sny-ms-icon"><svg width="26" height="26" viewBox="0 0 24 24" fill="#FF0000"><path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.6-.8-2-.9C16.4 5 12 5 12 5s-4.4 0-7 .1c-.4.1-1.2.1-2 .9-.6.6-.8 2-.8 2S2 9.6 2 11.2v1.5c0 1.6.2 3.2.2 3.2s.2 1.4.8 2c.8.8 1.8.7 2.2.8C6.4 19 12 19 12 19s4.4 0 7-.2c.4-.1 1.2-.1 2-.9.6-.6.8-2 .8-2s.2-1.6.2-3.2v-1.5C22 9.6 21.8 8 21.8 8zM9.7 14.5V9l5.4 2.8-5.4 2.7z"/></svg></div>'
            + '<p class="sny-ms-title">Subscribe on YouTube</p>'
            + '<p class="sny-ms-msg">Tap below, subscribe, then come back and let us know!</p>'
            + '<a class="sny-ms-btn" href="' + url + '" target="_blank" rel="noopener" onclick="setTimeout(function(){document.getElementById(\'snyCountdown\').style.display=\'none\';showAskCard();},2500)">Open YouTube to Subscribe</a>'
            + '</div>';
    }

    function showToast(msg) {
        let t = document.getElementById('snyToast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'snyToast';
            t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(16px);background:#111;color:#4ade80;border:1px solid rgba(74,222,128,.25);border-radius:20px;padding:9px 20px;font-size:13px;font-weight:600;z-index:99999;opacity:0;transition:opacity .22s,transform .22s;white-space:nowrap;pointer-events:none;font-family:inherit;';
            document.body.appendChild(t);
        }
        t.textContent = msg;
        requestAnimationFrame(() => { t.style.opacity = '1'; t.style.transform = 'translateX(-50%) translateY(0)'; });
        clearTimeout(t._h);
        t._h = setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(-50%) translateY(16px)'; }, 2500);
    }

    function renderDesc(text) {
        const d = document.getElementById('snyCHDesc');
        const m = document.getElementById('snyMoreBtn');
        if (!d || !m) return;
        const need = text.length > DESC_TRIM;
        d.textContent = (need && !_descFull) ? text.slice(0, DESC_TRIM) + '…' : text;
        m.style.display = need ? 'inline' : 'none';
        m.textContent = _descFull ? 'Show less' : '…more';
    }

    window.snyToggleDesc = function() {
        _descFull = !_descFull;
        renderDesc(_activeCh ? (_activeCh.description || '') : '');
    };

    function closeModal() {
        tickerStop();
        popupKill();
        const overlay = document.getElementById('snyOverlay');
        if (overlay) overlay.classList.remove('open');
        document.body.style.overflow = '';
        const askCard = document.getElementById('snyAskCard');
        const countdown = document.getElementById('snyCountdown');
        if (askCard) askCard.style.display = 'none';
        if (countdown) countdown.style.display = 'none';
    }

    // ============================================================================
    // SVG ANIMATION
    // ============================================================================
    function initSVGAnimation() {
        const grid = document.getElementById('dotGrid');
        if (!grid) {
            console.log('⚠️ SVG grid not found');
            return;
        }

        const CONFIG = { centerX: 200, centerY: 200, dotSize: 5, spacing: 20 };
        const PATTERN = [3, 7, 9, 9, 11, 11, 11, 9, 9, 7, 3];
        let dots = [];

        function createDots() {
            grid.innerHTML = '';
            dots = [];
            const startY = CONFIG.centerY - ((PATTERN.length - 1) * CONFIG.spacing) / 2;

            PATTERN.forEach((count, rowIdx) => {
                const y = startY + rowIdx * CONFIG.spacing;
                const startX = CONFIG.centerX - ((count - 1) * CONFIG.spacing) / 2;
                for (let i = 0; i < count; i++) {
                    const x = startX + i * CONFIG.spacing;
                    const dist = Math.hypot(x - CONFIG.centerX, y - CONFIG.centerY);
                    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    circle.setAttribute('cx', x);
                    circle.setAttribute('cy', y);
                    circle.setAttribute('r', 0);
                    circle.setAttribute('fill', 'url(#dotGradient)');
                    circle.setAttribute('filter', 'url(#glow)');
                    circle.style.transition = 'r 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    grid.appendChild(circle);
                    dots.push({ el: circle, dist });
                }
            });
            dots.sort((a, b) => a.dist - b.dist);
        }

        function animate() {
            dots.forEach(d => d.el.setAttribute('r', 0));
            const delay = 2000 / dots.length;
            dots.forEach((d, i) => setTimeout(() => d.el.setAttribute('r', CONFIG.dotSize), i * delay));
        }

        createDots();
        setTimeout(animate, 500);
        setInterval(animate, 10000);
    }

    // ============================================================================
    // RELEASES CAROUSEL
    // ============================================================================
    function initReleasesCarousel() {
        const track = document.getElementById('releasesSlider');
        if (!track) {
            console.log('⚠️ Releases carousel not found');
            return;
        }
        
        const originals = track.querySelectorAll('.release-slide-item:not(.clone)');
        if (!originals.length) return;

        const total = originals.length;
        let current = 0;
        let autoTimer, isMoving = false;

        // Remove old clones
        track.querySelectorAll('.clone').forEach(c => c.remove());

        // Add clones at end
        originals.forEach(s => {
            const clone = s.cloneNode(true);
            clone.classList.add('clone');
            clone.removeAttribute('data-video-id');
            track.appendChild(clone);
        });

        // Add clones at beginning
        for (let i = originals.length - 1; i >= 0; i--) {
            const clone = originals[i].cloneNode(true);
            clone.classList.add('clone');
            clone.removeAttribute('data-video-id');
            track.insertBefore(clone, track.firstChild);
        }

        const allSlides = track.querySelectorAll('.release-slide-item');

        function update(smooth = true) {
            const firstSlide = allSlides[0];
            if (!firstSlide) return;
            
            const w = firstSlide.offsetWidth + 30;
            const containerW = track.parentElement.offsetWidth;
            const offset = (containerW - w) / 2;
            const pos = - (total + current) * w + offset;
            track.style.transition = smooth ? 'transform 0.8s cubic-bezier(0.25,0.46,0.45,0.94)' : 'none';
            track.style.transform = `translateX(${pos}px)`;

            allSlides.forEach((s, i) => {
                s.classList.remove('active', 'adjacent');
                if (i === total + current) {
                    s.classList.add('active');
                    s.setAttribute('aria-hidden', 'false');
                } else {
                    s.setAttribute('aria-hidden', 'true');
                    if (i === total + current - 1 || i === total + current + 1) {
                        s.classList.add('adjacent');
                    }
                }
            });
        }

        function next() {
            if (isMoving) return;
            isMoving = true;
            current++;
            update(true);
            setTimeout(() => {
                if (current >= total) {
                    current = 0;
                    update(false);
                }
                isMoving = false;
            }, 850);
        }

        function prev() {
            if (isMoving) return;
            isMoving = true;
            current--;
            update(true);
            setTimeout(() => {
                if (current < 0) {
                    current = total - 1;
                    update(false);
                }
                isMoving = false;
            }, 850);
        }

        function startAuto() {
            stopAuto();
            autoTimer = setInterval(next, 3500);
        }
        function stopAuto() { if (autoTimer) clearInterval(autoTimer); }

        // Initialize
        update(false);
        setTimeout(startAuto, 500);

        // Event listeners
        document.getElementById('nextSlide')?.addEventListener('click', () => { next(); stopAuto(); setTimeout(startAuto, 100); });
        document.getElementById('prevSlide')?.addEventListener('click', () => { prev(); stopAuto(); setTimeout(startAuto, 100); });
        
        if (track.parentElement) {
            track.parentElement.addEventListener('mouseenter', stopAuto);
            track.parentElement.addEventListener('mouseleave', startAuto);
        }

        // Indicators
        const indicators = document.getElementById('carouselIndicators');
        if (indicators) {
            indicators.innerHTML = '';
            for (let i = 0; i < total; i++) {
                const dot = document.createElement('div');
                dot.className = 'carousel-dot';
                if (i === 0) dot.classList.add('active');
                dot.addEventListener('click', () => {
                    current = i;
                    update(true);
                    stopAuto();
                    setTimeout(startAuto, 3500);
                    
                    // Update active dot
                    document.querySelectorAll('.carousel-dot').forEach((d, idx) => {
                        d.classList.toggle('active', idx === i);
                    });
                });
                indicators.appendChild(dot);
            }
        }
    }

    // ============================================================================
    // ARTIST MARQUEE (with tooltip reinitialization)
    // ============================================================================
    // function initArtistMarquee() {
    //     const marquee = document.querySelector('.marquee-content');
    //     if (!marquee) {
    //         console.log('⚠️ Artist marquee not found');
    //         return;
    //     }

    //     // Clone content for seamless loop
    //     const content = marquee.innerHTML;
    //     marquee.innerHTML = content + content;
        
    //     // Re-initialize tooltips for the duplicated content
    //     setTimeout(() => {
    //         if (window.reinitializeTooltips) {
    //             const count = window.reinitializeTooltips(marquee);
    //             console.log(`🎨 Artist marquee: ${count} tooltips re-initialized`);
    //         }
    //     }, 50);
    // }

    // ============================================================================
    // TIME AGO UPDATE
    // ============================================================================
    function initTimeAgo() {
        function getTimeAgo(dateStr) {
            if (!dateStr) return 'just now';
            
            const d = new Date(dateStr);
            const now = new Date();
            const sec = Math.floor((now - d) / 1000);
            
            if (sec < 60) return 'just now';
            const min = Math.floor(sec / 60);
            if (min < 60) return min + ' minute' + (min > 1 ? 's' : '') + ' ago';
            const hr = Math.floor(min / 60);
            if (hr < 24) return hr + ' hour' + (hr > 1 ? 's' : '') + ' ago';
            const day = Math.floor(hr / 24);
            if (day < 30) return day + ' day' + (day > 1 ? 's' : '') + ' ago';
            return d.toLocaleDateString();
        }

        function updateTime() {
            const active = document.querySelector('.release-slide-item.active');
            const timeEl = document.querySelector('.time-text');
            if (active && timeEl && active.dataset.publishedAt) {
                timeEl.textContent = getTimeAgo(active.dataset.publishedAt);
            }
        }

        // Initial update
        setTimeout(updateTime, 100);
        
        // Observe slide changes
        const observer = new MutationObserver(updateTime);
        document.querySelectorAll('.release-slide-item').forEach(s => observer.observe(s, { attributes: true }));
    }

    // ============================================================================
    // GROWTH BAR TEASER (hover fill animation)
    // ============================================================================
    function initGrowthBars() {
        document.querySelectorAll('.growth-bar-col').forEach(function(col) {
            var bar   = col.querySelector('.growth-bar');
            var fill  = col.querySelector('.bar-fill');
            var tip   = col.querySelector('.bar-tip');
            var name  = col.querySelector('.bar-name');
            var hint  = col.querySelector('.bar-hint');
            if (!bar) return;

            var color = bar.classList.contains('hot-bar')    ? '#ff4500'
                    : bar.classList.contains('daily-bar')  ? '#22c55e'
                    : '#38bdf8';

            col.addEventListener('mouseenter', function() {
                if (fill) fill.style.height = '100%';
                if (tip)  { tip.style.opacity = '1'; tip.style.top = '-48px'; }
                if (name) name.style.color = color;
                if (hint) hint.style.color = color;
                if (bar)  bar.style.boxShadow = '0 0 24px ' + color + '55';
            });
            col.addEventListener('mouseleave', function() {
                if (fill) fill.style.height = '0%';
                if (tip)  { tip.style.opacity = '0'; tip.style.top = '-38px'; }
                if (name) name.style.color = '#555';
                if (hint) hint.style.color = '#333';
                if (bar)  bar.style.boxShadow = 'none';
            });
        });
    }

    // ============================================================================
    // INITIALIZE
    // ============================================================================
    document.addEventListener('DOMContentLoaded', function() {
        console.log('🏠 Home JS initialized');

        // Channels modal (from menu.html)
        fetchChannels();
        
        const closeBtn = document.getElementById('snyClose');
        if (closeBtn) closeBtn.addEventListener('click', closeModal);
        
        const overlay = document.getElementById('snyOverlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeModal();
            });
        }
        
        document.addEventListener('keydown', (e) => { 
            if (e.key === 'Escape') closeModal(); 
        });

        // Homepage features
        initSVGAnimation();
        initReleasesCarousel();
        // initArtistMarquee();
        initTimeAgo();
        initGrowthBars();
    });

})();