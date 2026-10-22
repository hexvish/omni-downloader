// State variables
let currentMode = 'auto';
let currentTab = 'audio';
let mediaData = null;
let selectedFormat = 'mp3';
let selectedBitrate = '320';
let selectedVideoFormat = 'mp4';
let selectedVideoRes = '1080p';
let targetDownloadUrl = '';
let pollingInterval = null;

// Elements
const urlInput = document.getElementById('urlInput');
const clearBtn = document.getElementById('clearBtn');
const fetchBtn = document.getElementById('fetchBtn');
const fetchBtnText = document.getElementById('fetchBtnText');
const fetchBtnLoader = document.getElementById('fetchBtnLoader');
const statusBox = document.getElementById('statusBox');
const resultsSection = document.getElementById('resultsSection');
const mediaThumb = document.getElementById('mediaThumb');
const mediaTitle = document.getElementById('mediaTitle');
const mediaUploader = document.getElementById('mediaUploader');
const mediaTypeBadge = document.getElementById('mediaTypeBadge');
const mediaDurationBadge = document.getElementById('mediaDurationBadge');

// Audio Tab Elements
const formatGrid = document.getElementById('formatGrid');
const bitrateRow = document.getElementById('bitrateRow');
const actionTargetText = document.getElementById('actionTargetText');
const actionSpecsText = document.getElementById('actionSpecsText');
const btnDownloadAudio = document.getElementById('btnDownloadAudio');

// Video Tab Elements
const videoFormatGrid = document.getElementById('videoFormatGrid');
const videoResRow = document.getElementById('videoResRow');
const videoActionTargetText = document.getElementById('videoActionTargetText');
const videoActionSpecsText = document.getElementById('videoActionSpecsText');
const btnDownloadVideo = document.getElementById('btnDownloadVideo');

// Playlist Elements
const playlistTracksSection = document.getElementById('playlistTracksSection');
const tracklistCount = document.getElementById('tracklistCount');
const tracklistBody = document.getElementById('tracklistBody');

// Multi-Download Elements
const downloadsManager = document.getElementById('downloadsManager');
const downloadsList = document.getElementById('downloadsList');
const activeDownloadsCount = document.getElementById('activeDownloadsCount');
const activeTasks = {};

function updateActiveTasksCount() {
    const count = Object.keys(activeTasks).length;
    if (activeDownloadsCount) activeDownloadsCount.textContent = count;
    if (downloadsManager) {
        downloadsManager.style.display = count > 0 ? 'block' : 'none';
    }
}

function dismissTask(taskId) {
    if (activeTasks[taskId]) {
        if (activeTasks[taskId].interval) clearInterval(activeTasks[taskId].interval);
        delete activeTasks[taskId];
    }
    const card = document.getElementById(`task-card-${taskId}`);
    if (card) card.remove();
    updateActiveTasksCount();
}

function clearUI() {
    urlInput.value = '';
    statusBox.style.display = 'none';
    statusBox.textContent = '';
    resultsSection.style.display = 'none';
    mediaData = null;
}

if (clearBtn) clearBtn.addEventListener('click', clearUI);
if (urlInput) urlInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleFetch(); });

function showStatus(msg, type) {
    statusBox.textContent = msg;
    statusBox.className = 'status-box ' + type;
    statusBox.style.display = 'block';
}

function setFetchLoading(isLoading) {
    fetchBtn.disabled = isLoading;
    fetchBtnText.style.display = isLoading ? 'none' : 'inline';
    fetchBtnLoader.style.display = isLoading ? 'inline-block' : 'none';
}

async function handleFetch() {
    const url = urlInput.value.trim();
    if (!url) {
        return showStatus('Please enter a media URL first.', 'error');
    }

    setFetchLoading(true);
    showStatus('Analyzing media details and available formats...', 'info');
    resultsSection.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append('url', url);
        formData.append('mode', 'auto');

        const response = await fetch('/fetch_formats', { method: 'POST', body: formData });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || 'Failed to fetch media details.');
        }

        mediaData = data;
        targetDownloadUrl = url;
        renderResults(data);
        showStatus('Media details loaded! Choose your format and quality below.', 'success');
    } catch (err) {
        showStatus(err.message || 'Failed to connect to server.', 'error');
    } finally {
        setFetchLoading(false);
    }
}

function renderResults(data) {
    resultsSection.style.display = 'block';
    mediaTitle.textContent = data.title;
    mediaUploader.textContent = data.uploader || 'Creator';
    mediaThumb.src = data.preview_url || '';

    // Dynamic platform badge based on analyzed link
    if (data.platform) {
        mediaTypeBadge.textContent = `${data.platform.icon} ${data.platform.name}`;
        mediaTypeBadge.style.background = `${data.platform.color}25`;
        mediaTypeBadge.style.border = `1px solid ${data.platform.color}55`;
        mediaTypeBadge.style.color = '#ffffff';
    } else if (data.is_playlist) {
        mediaTypeBadge.textContent = '📦 Playlist';
        mediaTypeBadge.className = 'mini-badge playlist-badge';
    } else {
        mediaTypeBadge.textContent = '🎬 Media';
        mediaTypeBadge.className = 'mini-badge';
    }

    if (data.is_playlist) {
        mediaDurationBadge.textContent = `${data.track_count} tracks`;
        playlistTracksSection.style.display = 'block';
        tracklistCount.textContent = `${data.track_count} Tracks`;
        renderTracklist(data.entries);
    } else {
        mediaDurationBadge.textContent = data.duration_str || '';
        playlistTracksSection.style.display = 'none';
    }

    renderAudioFormats(data.audio_formats || []);
    renderVideoFormats(data.video_formats || []);
    renderVideoResolutions(data.video_resolutions || []);
    updateActionSummary();
    updateTracklistButtons();
}

function renderTracklist(entries) {
    tracklistBody.innerHTML = '';
    if (!entries || !entries.length) return;

    const btnLabel = currentTab === 'video' ? '⬇ Video' : '⬇ Audio';
    entries.forEach(track => {
        const item = document.createElement('div');
        item.className = 'track-item';
        item.innerHTML = `
            <div class="track-num">${track.index}</div>
            <div class="track-info">
                <div class="track-title" title="${track.title}">${track.title}</div>
                <div class="track-sub">${track.uploader || ''} ${track.duration_str ? '• ' + track.duration_str : ''}</div>
            </div>
            <button type="button" class="btn-track-dl" onclick="downloadSingleTrack('${track.url || ''}', '${track.title.replace(/'/g, "\\'")}')">
                ${btnLabel}
            </button>
        `;
        tracklistBody.appendChild(item);
    });
}

function updateTracklistButtons() {
    const btnLabel = currentTab === 'video' ? '⬇ Video' : '⬇ Audio';
    document.querySelectorAll('.btn-track-dl').forEach(btn => {
        btn.textContent = btnLabel;
    });
}

// --- Audio Controls ---
function renderAudioFormats(formats) {
    formatGrid.innerHTML = '';
    formats.forEach(f => {
        const card = document.createElement('div');
        card.className = `format-card ${f.codec === selectedFormat ? 'selected' : ''}`;
        card.onclick = (e) => selectAudioFormat(f.codec, e.currentTarget);
        card.innerHTML = `
            <div class="format-name">${f.label}</div>
            <div class="format-sub">${f.badge}</div>
        `;
        formatGrid.appendChild(card);
    });
    renderBitrates();
}

function selectAudioFormat(codec, el) {
    selectedFormat = codec;
    formatGrid.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
    if (el) el.classList.add('selected');
    renderBitrates();
    updateActionSummary();
}

function renderBitrates() {
    bitrateRow.innerHTML = '';
    const activeFormatObj = (mediaData?.audio_formats || []).find(f => f.codec === selectedFormat);
    const bitrates = activeFormatObj ? activeFormatObj.bitrates : ['320', '256', '192', '128'];

    if (!bitrates.includes(selectedBitrate)) {
        selectedBitrate = activeFormatObj ? activeFormatObj.default_bitrate : bitrates[0];
    }

    bitrates.forEach(b => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className = `bitrate-pill ${b === selectedBitrate ? 'selected' : ''}`;
        pill.textContent = b === 'Lossless' ? '✨ Lossless Studio Quality' : `${b} kbps`;
        pill.onclick = (e) => selectBitrate(b, e.currentTarget);
        bitrateRow.appendChild(pill);
    });
}

function selectBitrate(b, el) {
    selectedBitrate = b;
    bitrateRow.querySelectorAll('.bitrate-pill').forEach(p => p.classList.remove('selected'));
    if (el) el.classList.add('selected');
    updateActionSummary();
}

// --- Video Controls ---
function renderVideoFormats(formats) {
    videoFormatGrid.innerHTML = '';
    const containerList = (formats && formats.length) ? formats : [
        { codec: 'mp4', label: 'MP4', badge: 'Universal' },
        { codec: 'mkv', label: 'MKV', badge: 'Matroska' },
        { codec: 'webm', label: 'WEBM', badge: 'Modern Web' }
    ];

    containerList.forEach(f => {
        const card = document.createElement('div');
        card.className = `format-card ${f.codec === selectedVideoFormat ? 'selected' : ''}`;
        card.onclick = (e) => selectVideoFormat(f.codec, e.currentTarget);
        card.innerHTML = `
            <div class="format-name">${f.label}</div>
            <div class="format-sub">${f.badge}</div>
        `;
        videoFormatGrid.appendChild(card);
    });
}

function selectVideoFormat(codec, el) {
    selectedVideoFormat = codec;
    videoFormatGrid.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
    if (el) el.classList.add('selected');
    updateActionSummary();
}

function renderVideoResolutions(resList) {
    videoResRow.innerHTML = '';
    const resolutions = (resList && resList.length) ? resList : ['1080p', '720p', '480p', '360p'];

    if (!resolutions.includes(selectedVideoRes)) {
        selectedVideoRes = resolutions[0] || '1080p';
    }

    resolutions.forEach(r => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className = `bitrate-pill ${r === selectedVideoRes ? 'selected' : ''}`;
        pill.textContent = r;
        pill.onclick = (e) => selectVideoResolution(r, e.currentTarget);
        videoResRow.appendChild(pill);
    });
}

function selectVideoResolution(res, el) {
    selectedVideoRes = res;
    videoResRow.querySelectorAll('.bitrate-pill').forEach(p => p.classList.remove('selected'));
    if (el) el.classList.add('selected');
    updateActionSummary();
}

// --- Tab Switching ---
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active', 'music-tab'));
    if (tab === 'audio') {
        document.getElementById('tabBtnAudio').classList.add('active', 'music-tab');
        document.getElementById('audioTabContent').style.display = 'block';
        document.getElementById('videoTabContent').style.display = 'none';
    } else {
        document.getElementById('tabBtnVideo').classList.add('active');
        document.getElementById('audioTabContent').style.display = 'none';
        document.getElementById('videoTabContent').style.display = 'block';
    }
    updateActionSummary();
    updateTracklistButtons();
}

function updateActionSummary() {
    const isPlaylist = mediaData?.is_playlist;
    
    // Audio Tab Summary
    const formatUpper = selectedFormat.toUpperCase();
    const bitrateStr = selectedBitrate === 'Lossless' ? 'Lossless' : `${selectedBitrate} kbps`;

    if (isPlaylist) {
        actionTargetText.textContent = `Download Entire Playlist (${mediaData?.track_count || 0} Tracks)`;
        actionSpecsText.textContent = `All songs packaged into ZIP • ${formatUpper} @ ${bitrateStr}`;
        btnDownloadAudio.innerHTML = `<span>📦 Download Full Playlist (ZIP)</span>`;
    } else {
        actionTargetText.textContent = `Download: ${mediaData?.title || 'Selected Track'}`;
        actionSpecsText.textContent = `${formatUpper} • ${bitrateStr} • High Quality Audio`;
        btnDownloadAudio.innerHTML = `<span>⬇ Download Audio Track</span>`;
    }

    // Video Tab Summary
    const videoFormatUpper = selectedVideoFormat.toUpperCase();
    const videoResStr = selectedVideoRes;

    if (isPlaylist) {
        videoActionTargetText.textContent = `Download Entire Playlist (${mediaData?.track_count || 0} Videos)`;
        videoActionSpecsText.textContent = `All videos packaged into ZIP • ${videoFormatUpper} @ ${videoResStr}`;
        btnDownloadVideo.innerHTML = `<span>📦 Download Full Playlist (ZIP)</span>`;
    } else {
        videoActionTargetText.textContent = `Download: ${mediaData?.title || 'Selected Video'}`;
        videoActionSpecsText.textContent = `${videoFormatUpper} • ${videoResStr} • High Definition Video`;
        btnDownloadVideo.innerHTML = `<span>⬇ Download Video</span>`;
    }
}

function downloadSingleTrack(trackUrl, title) {
    if (!trackUrl) return;
    if (currentTab === 'video') {
        startDownloadProcess({
            url: trackUrl,
            type: 'video',
            codec: selectedVideoFormat,
            resolution: selectedVideoRes,
            is_playlist: false,
            title: title
        });
    } else {
        startDownloadProcess({
            url: trackUrl,
            type: 'audio',
            codec: selectedFormat,
            bitrate: selectedBitrate,
            is_playlist: false,
            title: title
        });
    }
}

function triggerDownload(type) {
    if (type === 'video') {
        startDownloadProcess({
            url: targetDownloadUrl,
            type: 'video',
            codec: selectedVideoFormat,
            resolution: selectedVideoRes,
            is_playlist: mediaData?.is_playlist || false,
            title: mediaData?.title || 'Video'
        });
    } else {
        startDownloadProcess({
            url: targetDownloadUrl,
            type: 'audio',
            codec: selectedFormat,
            bitrate: selectedBitrate,
            is_playlist: mediaData?.is_playlist || false,
            title: mediaData?.title || 'Audio'
        });
    }
}

function createTaskCard(taskId, params, totalExpected) {
    const isVideo = params.type === 'video';
    const isPlaylist = params.is_playlist || totalExpected > 1;
    const itemIcon = isVideo ? '🎬' : '🎵';
    const typeLabel = isPlaylist 
        ? (isVideo ? 'Video Playlist' : 'Audio Playlist') 
        : (isVideo ? 'Video' : 'Audio');

    const card = document.createElement('div');
    card.className = 'progress-card';
    card.id = `task-card-${taskId}`;
    card.innerHTML = `
        <div class="progress-header">
            <div id="status-text-${taskId}" class="progress-status-text">
                <span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span>
                <span>Starting ${typeLabel} download...</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div id="counter-badge-${taskId}" class="mini-badge" style="${isPlaylist ? 'display: inline-flex;' : 'display: none;'} background: rgba(168, 85, 247, 0.25); border: 1px solid rgba(168, 85, 247, 0.4); color: #e9d5ff; font-size: 0.82rem; padding: 4px 10px; font-weight: 700;">
                    <span id="counter-text-${taskId}">${itemIcon} 0 of ${totalExpected} Completed</span>
                </div>
                <div id="percent-${taskId}" class="progress-percent">0%</div>
                <button type="button" class="btn-cancel-task" id="btn-cancel-${taskId}" onclick="cancelDownloadTask('${taskId}')" title="Cancel this download">Cancel</button>
                <button type="button" class="btn-dismiss-task" id="btn-dismiss-${taskId}" onclick="dismissTask('${taskId}')" title="Dismiss">&times;</button>
            </div>
        </div>
        <div class="progress-bar-bg">
            <div id="bar-fill-${taskId}" class="progress-bar-fill"></div>
        </div>
        <div class="progress-meta">
            <span id="item-info-${taskId}">${params.title || 'Preparing download engine...'}</span>
            <span id="speed-${taskId}">-- MB/s</span>
        </div>
        <div id="success-action-${taskId}" class="progress-success-action" style="display: none;">
            <a id="btn-save-${taskId}" href="#" class="btn-save-file" download>
                <span>💾 Save Downloaded File</span>
            </a>
        </div>
    `;
    downloadsList.prepend(card);
    downloadsManager.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return card;
}

async function cancelDownloadTask(taskId) {
    const btnCancel = document.getElementById(`btn-cancel-${taskId}`);
    if (btnCancel) {
        btnCancel.disabled = true;
        btnCancel.textContent = 'Cancelling...';
    }
    try {
        await fetch(`/cancel_download/${taskId}`, { method: 'POST' });
    } catch (e) {
        console.error('Cancel request error:', e);
    }

    if (activeTasks[taskId]) {
        if (activeTasks[taskId].interval) clearInterval(activeTasks[taskId].interval);
        activeTasks[taskId].completed = true;
    }

    const statusText = document.getElementById(`status-text-${taskId}`);
    const itemInfo = document.getElementById(`item-info-${taskId}`);
    const speed = document.getElementById(`speed-${taskId}`);
    const btnDismiss = document.getElementById(`btn-dismiss-${taskId}`);
    const barFill = document.getElementById(`bar-fill-${taskId}`);

    if (statusText) statusText.innerHTML = `<span style="color: #f87171;">🚫 Cancelled by user</span>`;
    if (itemInfo) itemInfo.textContent = 'Download cancelled. Temporary files cleaned up.';
    if (speed) speed.textContent = 'Cancelled';
    if (barFill) {
        barFill.style.background = '#ef4444';
        barFill.style.boxShadow = 'none';
    }
    if (btnCancel) btnCancel.style.display = 'none';
    if (btnDismiss) btnDismiss.style.display = 'inline-block';

    updateActiveTasksCount();
}

async function startDownloadProcess(params) {
    const totalExpected = params.total_items || (params.is_playlist ? (mediaData?.track_count || 1) : 1);
    showStatus('Download initiated! Check the active tasks below.', 'info');

    try {
        const formData = new FormData();
        formData.append('url', params.url);
        formData.append('type', params.type || 'audio');
        formData.append('codec', params.codec || 'mp3');
        formData.append('bitrate', params.bitrate || '320');
        formData.append('resolution', params.resolution || '1080p');
        formData.append('is_playlist', params.is_playlist ? 'true' : 'false');
        formData.append('total_items', totalExpected);

        const response = await fetch('/start_download', { method: 'POST', body: formData });
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || 'Failed to start download task.');
        }

        createTaskCard(data.task_id, params, totalExpected);
        pollTaskStatus(data.task_id, params, totalExpected);
    } catch (err) {
        showStatus(err.message || 'Download failed.', 'error');
    }
}

function pollTaskStatus(taskId, params, fallbackTotal = 1) {
    const isVideo = params.type === 'video';
    const itemIcon = isVideo ? '🎬' : '🎵';
    const itemTypeStr = isVideo ? 'Video' : 'Song';

    const statusText = document.getElementById(`status-text-${taskId}`);
    const counterBadge = document.getElementById(`counter-badge-${taskId}`);
    const counterText = document.getElementById(`counter-text-${taskId}`);
    const percent = document.getElementById(`percent-${taskId}`);
    const barFill = document.getElementById(`bar-fill-${taskId}`);
    const itemInfo = document.getElementById(`item-info-${taskId}`);
    const speed = document.getElementById(`speed-${taskId}`);
    const successAction = document.getElementById(`success-action-${taskId}`);
    const btnSave = document.getElementById(`btn-save-${taskId}`);
    const btnCancel = document.getElementById(`btn-cancel-${taskId}`);
    const btnDismiss = document.getElementById(`btn-dismiss-${taskId}`);

    const intervalId = setInterval(async () => {
        try {
            const res = await fetch(`/task_status/${taskId}`);
            if (!res.ok) throw new Error('Task lost');
            const task = await res.json();

            const total = task.total_items || fallbackTotal || 1;
            const completed = task.completed_items !== undefined ? task.completed_items : 0;
            const current = task.current_item || 1;
            const isPlaylist = params.is_playlist || total > 1;

            if (counterBadge && counterText) {
                if (isPlaylist) {
                    counterBadge.style.display = 'inline-flex';
                    counterText.textContent = `${itemIcon} ${completed} of ${total} Completed`;
                } else {
                    counterBadge.style.display = 'none';
                }
            }

            if (task.status === 'downloading' || task.status === 'starting') {
                const pct = Math.round(task.progress || 0);
                if (barFill) barFill.style.width = pct + '%';
                if (percent) percent.textContent = pct + '%';
                
                if (statusText) {
                    if (isPlaylist) {
                        statusText.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> <span>Downloading ${itemTypeStr} ${current} of ${total} • <b>${completed}/${total} Completed</b></span>`;
                    } else {
                        statusText.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> <span>Downloading ${isVideo ? 'video stream' : 'audio stream'}...</span>`;
                    }
                }
                if (itemInfo) {
                    if (isPlaylist) {
                        itemInfo.textContent = task.current_title ? `${itemTypeStr}: "${task.current_title}" (${completed} of ${total} finished)` : `Processing items (${completed} of ${total} finished)...`;
                    } else {
                        itemInfo.textContent = task.current_title || params.title;
                    }
                }
                if (speed) speed.textContent = task.speed || '';
            } else if (task.status === 'converting') {
                if (statusText) {
                    if (isPlaylist) {
                        statusText.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> <span>Processing ${itemTypeStr} ${current} of ${total} • <b>${completed}/${total} Completed</b></span>`;
                    } else {
                        if (barFill) barFill.style.width = '96%';
                        if (percent) percent.textContent = '96%';
                        statusText.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> <span>Transcoding with FFmpeg...</span>`;
                    }
                }
                if (itemInfo) {
                    itemInfo.textContent = isVideo
                        ? `Transcoding into ${params.codec.toUpperCase()} (${params.resolution}) with metadata`
                        : `Encoding into ${params.codec.toUpperCase()} (${params.bitrate} kbps) with metadata tags`;
                }
            } else if (task.status === 'zipping') {
                if (barFill) barFill.style.width = '98%';
                if (percent) percent.textContent = '98%';
                if (counterText && isPlaylist) counterText.textContent = `📦 ${total} of ${total} Ready`;
                if (statusText) {
                    statusText.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> <span>Packaging all ${total} ${itemTypeStr.toLowerCase()}s into ZIP archive...</span>`;
                }
                if (itemInfo) itemInfo.textContent = `All ${total} items processed! Generating final package...`;
            } else if (task.status === 'completed') {
                clearInterval(intervalId);
                if (activeTasks[taskId]) activeTasks[taskId].completed = true;
                updateActiveTasksCount();

                if (barFill) barFill.style.width = '100%';
                if (percent) percent.textContent = '100%';
                if (counterText && isPlaylist) counterText.textContent = `✅ ${total} of ${total} Completed`;
                if (statusText) {
                    statusText.innerHTML = `<span style="color: var(--success);">🎉 ${isPlaylist ? `All ${total} ${itemTypeStr}s Completed!` : 'Download Complete!'}</span>`;
                }
                if (itemInfo) {
                    itemInfo.textContent = isPlaylist
                        ? `Playlist archive ready: ${task.filename} (${total} items included)`
                        : `File ready: ${task.filename}`;
                }
                if (speed) speed.textContent = 'Completed';
                if (btnCancel) btnCancel.style.display = 'none';
                if (btnDismiss) btnDismiss.style.display = 'inline-block';

                // Auto-trigger browser download
                if (btnSave) {
                    btnSave.href = task.download_url;
                    btnSave.download = task.filename;
                }
                if (successAction) successAction.style.display = 'block';

                const autoAnchor = document.createElement('a');
                autoAnchor.href = task.download_url;
                autoAnchor.download = task.filename;
                document.body.appendChild(autoAnchor);
                autoAnchor.click();
                document.body.removeChild(autoAnchor);
            } else if (task.status === 'cancelled') {
                clearInterval(intervalId);
                if (activeTasks[taskId]) activeTasks[taskId].completed = true;
                updateActiveTasksCount();

                if (statusText) statusText.innerHTML = `<span style="color: #f87171;">🚫 Download Cancelled</span>`;
                if (itemInfo) itemInfo.textContent = 'Download cancelled. Temporary files cleaned up.';
                if (speed) speed.textContent = 'Cancelled';
                if (barFill) {
                    barFill.style.background = '#ef4444';
                    barFill.style.boxShadow = 'none';
                }
                if (btnCancel) btnCancel.style.display = 'none';
                if (btnDismiss) btnDismiss.style.display = 'inline-block';
            } else if (task.status === 'error') {
                clearInterval(intervalId);
                if (activeTasks[taskId]) activeTasks[taskId].completed = true;
                updateActiveTasksCount();

                if (statusText) statusText.innerHTML = `<span style="color: var(--error);">❌ Error Occurred</span>`;
                if (itemInfo) itemInfo.textContent = task.error || 'Download failed.';
                if (btnCancel) btnCancel.style.display = 'none';
                if (btnDismiss) btnDismiss.style.display = 'inline-block';
            }
        } catch (e) {
            // keep polling on temporary network glitch
        }
    }, 750);

    activeTasks[taskId] = {
        interval: intervalId,
        params: params,
        completed: false
    };
    updateActiveTasksCount();
}
