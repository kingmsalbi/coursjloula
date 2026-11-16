/**
 * Active Presence & Document Consultation Tracker
 * Responsibilities:
 * - Accurately track active student presence (pauses when tab is hidden or idle)
 * - Measure exact time spent on documents/courses
 * - Periodically send heartbeat pings to /api/track/ping
 */
class StudentTracker {
    constructor() {
        this.sessionToken = null;
        this.userId = null;
        this.userRole = null;
        this.heartbeatTimer = null;
        this.localTimer = null;
        this.activeSecondsBucket = 0;
        this.totalStudySeconds = 0;
        this.currentFileId = null;
        this.currentFileName = null;
        this.fileReadingSeconds = 0;
        this.isTabActive = !document.hidden;
        this.isUserIdle = false;
        this.lastUserActivity = Date.now();
        this.idleThresholdMs = 120000; // 2 minutes without mouse/key/touch -> pause

        this.initEventListeners();
    }

    init(user, sessionToken) {
        if (!user || user.role !== 'student') {
            this.stop();
            return;
        }

        this.userId = user.id;
        this.userRole = user.role;
        this.sessionToken = sessionToken;
        this.activeSecondsBucket = 0;
        this.start();
    }

    initEventListeners() {
        // Tab visibility change
        document.addEventListener('visibilitychange', () => {
            this.isTabActive = !document.hidden;
            if (this.isTabActive) {
                this.lastUserActivity = Date.now();
                this.isUserIdle = false;
            }
        });

        // User activity listeners
        const recordActivity = () => {
            this.lastUserActivity = Date.now();
            if (this.isUserIdle) {
                this.isUserIdle = false;
            }
        };

        ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'].forEach(evt => {
            window.addEventListener(evt, recordActivity, { passive: true });
        });

        // Flush tracking ping before page unloads
        window.addEventListener('beforeunload', () => {
            if (this.userRole === 'student' && this.activeSecondsBucket > 0) {
                navigator.sendBeacon('/api/track/ping', JSON.stringify({
                    session_token: this.sessionToken,
                    active_seconds: this.activeSecondsBucket,
                    file_id: this.currentFileId
                }));
            }
        });
    }

    start() {
        this.stop();

        // 1-second interval to count real active seconds and update UI
        this.localTimer = setInterval(() => {
            const now = Date.now();
            if (now - this.lastUserActivity > this.idleThresholdMs) {
                this.isUserIdle = true;
            }

            if (this.isTabActive && !this.isUserIdle) {
                this.activeSecondsBucket++;
                this.totalStudySeconds++;

                if (this.currentFileId) {
                    this.fileReadingSeconds++;
                    this.updateFileReaderTimerUI();
                }

                this.updateHeaderTimerUI();
            }
        }, 1000);

        // Heartbeat to server every 60 seconds (optimized to reduce request frequency and stay within server limits)
        this.heartbeatTimer = setInterval(() => {
            if (!document.hidden && this.activeSecondsBucket > 0) {
                this.sendHeartbeat();
            }
        }, 60000);
    }

    stop() {
        if (this.localTimer) clearInterval(this.localTimer);
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
        this.localTimer = null;
        this.heartbeatTimer = null;
        this.currentFileId = null;
    }

    async sendHeartbeat() {
        const secondsToSend = this.activeSecondsBucket;
        this.activeSecondsBucket = 0;

        try {
            const token = this.sessionToken || localStorage.getItem('auth_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch('/api/track/ping', {
                method: 'POST',
                headers,
                credentials: 'same-origin',
                body: JSON.stringify({
                    session_token: this.sessionToken,
                    active_seconds: secondsToSend,
                    file_id: this.currentFileId
                })
            });
            const data = await res.json();
            if (data && data.total_time_seconds !== undefined) {
                this.totalStudySeconds = data.total_time_seconds;
                this.updateHeaderTimerUI();
            }
        } catch (err) {
            console.warn('[Tracker] Heartbeat error:', err);
            // Put unsent seconds back in bucket
            this.activeSecondsBucket += secondsToSend;
        }
    }

    // Call when opening a document modal
    startFileReading(fileId, courseId, fileName) {
        this.currentFileId = fileId;
        this.currentFileName = fileName;
        this.fileReadingSeconds = 0;

        fetch('/api/track/file-start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_id: fileId,
                course_id: courseId,
                file_name: fileName
            })
        }).catch(err => console.warn(err));

        this.updateFileReaderTimerUI();
    }

    // Call when closing the document modal
    stopFileReading() {
        if (!this.currentFileId) return;

        // Force an immediate ping with any pending bucket
        if (this.activeSecondsBucket > 0) {
            this.sendHeartbeat();
        }

        this.currentFileId = null;
        this.currentFileName = null;
        this.fileReadingSeconds = 0;
    }

    updateFileReaderTimerUI() {
        const el = document.getElementById('docReadingTimer');
        if (el) {
            const mins = Math.floor(this.fileReadingSeconds / 60);
            const secs = this.fileReadingSeconds % 60;
            el.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }
    }

    updateHeaderTimerUI() {
        const el = document.getElementById('headerActiveTimer');
        const mobEl = document.getElementById('mobileHeaderActiveTimer');
        const hours = Math.floor(this.totalStudySeconds / 3600);
        const mins = Math.floor((this.totalStudySeconds % 3600) / 60);
        const secs = this.totalStudySeconds % 60;
        const text = hours > 0 ? `${hours}h ${mins}m` : `${mins}m ${secs}s`;

        if (el) el.textContent = text;
        if (mobEl) mobEl.textContent = text;
    }
}

// Global instance
window.studentTracker = new StudentTracker();
