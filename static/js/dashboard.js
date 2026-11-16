/**
 * Teacher Dashboard & Analytics Controller for Prof. Msalbi
 */
class TeacherDashboard {
    constructor() {
        this.activityChart = null;
        this.filesChart = null;
        this.studentsCache = [];
        this.currentDossierStudentId = null;
    }

    async fetchWithAuth(url, options = {}) {
        const token = localStorage.getItem('auth_token');
        const headers = options.headers ? { ...options.headers } : {};
        if (token && !headers['Authorization']) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return fetch(url, {
            ...options,
            headers,
            credentials: 'same-origin'
        });
    }

    async loadDashboard() {
        try {
            const res = await this.fetchWithAuth('/api/teacher/dashboard');
            if (!res.ok) throw new Error('Impossible de charger le tableau de bord');
            const data = await res.json();

            this.renderKPIs(data.kpi);
            try {
                this.renderCharts(data.daily_stats, data.top_files);
            } catch (ce) {
                console.warn('Charts render warning:', ce);
            }
            this.renderTopStudents(data.top_students);
            this.renderRecentActivity(data.recent_activity);

            // Load full students table
            await this.loadStudentsList();
            // Load classes & populate selectors
            await this.loadClasses();
        } catch (err) {
            console.error('Error loading dashboard:', err);
        }
    }

    renderKPIs(kpi) {
        document.getElementById('kpiTotalStudents').textContent = kpi.total_students || 0;
        
        // Total study time format
        const totalSecs = kpi.total_time_seconds || 0;
        const hours = Math.floor(totalSecs / 3600);
        const mins = Math.floor((totalSecs % 3600) / 60);
        document.getElementById('kpiTotalTime').textContent = hours > 0 ? `${hours}h ${mins}m` : `${mins} min`;

        document.getElementById('kpiTotalConsultations').textContent = kpi.total_consultations || 0;
        document.getElementById('kpiTotalDownloads').textContent = kpi.total_downloads || 0;
        document.getElementById('kpiOnlineStudents').textContent = kpi.online_students || 0;
    }

    renderCharts(dailyStats, topFiles) {
        // Daily Activity Chart
        const dailyCanvas = document.getElementById('dailyActivityChart');
        if (dailyCanvas) {
            const labels = dailyStats.map(d => {
                const parts = d.day.split('-');
                return `${parts[2]}/${parts[1]}`;
            });
            const minutesData = dailyStats.map(d => d.duration_minutes);

            if (this.activityChart) this.activityChart.destroy();

            const ctx = dailyCanvas.getContext('2d');
            this.activityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels.length ? labels : ['Aujourd\'hui'],
                    datasets: [{
                        label: 'Temps d\'étude (Minutes)',
                        data: minutesData.length ? minutesData : [0],
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#2563eb',
                        pointRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f1f5f9' },
                            ticks: { callback: v => `${v} min` }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        // Top Files Chart
        const filesCanvas = document.getElementById('topFilesChart');
        if (filesCanvas) {
            const fileLabels = topFiles.map(f => f.file_name.length > 18 ? f.file_name.substring(0, 18) + '...' : f.file_name);
            const viewCounts = topFiles.map(f => f.view_count);

            if (this.filesChart) this.filesChart.destroy();

            const ctx2 = filesCanvas.getContext('2d');
            this.filesChart = new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: fileLabels.length ? fileLabels : ['Aucun fichier'],
                    datasets: [{
                        label: 'Vues',
                        data: viewCounts.length ? viewCounts : [0],
                        backgroundColor: ['#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', '#10b981'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f1f5f9' },
                            ticks: { stepSize: 1 }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    }

    renderTopStudents(students) {
        const container = document.getElementById('topStudentsList');
        if (!container) return;

        if (!students || students.length === 0) {
            container.innerHTML = '<p class="text-sm text-slate-500 py-3 text-center">Aucune activité enregistrée pour le moment.</p>';
            return;
        }

        const maxSecs = Math.max(...students.map(s => s.total_seconds), 1);

        container.innerHTML = students.map((s, idx) => {
            const hours = Math.floor(s.total_seconds / 3600);
            const mins = Math.floor((s.total_seconds % 3600) / 60);
            const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins} min`;
            const pct = Math.round((s.total_seconds / maxSecs) * 100);

            const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx + 1}`;

            return `
                <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors">
                    <div class="flex items-center gap-3">
                        <span class="text-lg font-bold text-slate-500 w-6 text-center">${medal}</span>
                        <div>
                            <div class="font-semibold text-slate-800 text-sm">${s.full_name}</div>
                            <div class="text-xs text-slate-500">${s.classe} • @${s.username}</div>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm font-bold text-blue-600">${timeStr}</div>
                        <div class="text-xs text-slate-500">${s.total_files_viewed} docs consultés</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderRecentActivity(activities) {
        const container = document.getElementById('recentActivityFeed');
        if (!container) return;

        if (!activities || activities.length === 0) {
            container.innerHTML = '<p class="text-sm text-slate-500 py-3 text-center">Aucune activité récente.</p>';
            return;
        }

        container.innerHTML = activities.map(a => {
            let icon = '📖';
            let badgeColor = 'bg-blue-50 text-blue-700 border-blue-200';

            if (a.action_type === 'LOGIN') {
                icon = '🔑';
                badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
            } else if (a.action_type === 'DOWNLOAD_FILE') {
                icon = '⬇️';
                badgeColor = 'bg-amber-50 text-amber-700 border-amber-200';
            } else if (a.action_type === 'VIEW_FILE') {
                icon = '📄';
                badgeColor = 'bg-indigo-50 text-indigo-700 border-indigo-200';
            }

            return `
                <div class="flex items-start gap-3 p-3 rounded-xl border border-slate-100 bg-white hover:border-slate-200 transition-all">
                    <div class="text-xl p-2 rounded-lg ${badgeColor} border">${icon}</div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between gap-2">
                            <span class="font-semibold text-sm text-slate-900 truncate">${a.full_name} <span class="text-xs font-normal text-slate-500">(${a.classe})</span></span>
                            <span class="text-xs text-slate-400 whitespace-nowrap">${this.formatRelativeTime(a.created_at)}</span>
                        </div>
                        <div class="text-xs text-slate-600 mt-0.5 truncate">${a.description}</div>
                        ${a.extra_data ? `<div class="text-[11px] text-slate-500 mt-1 bg-slate-50 px-2 py-0.5 rounded inline-block">${a.extra_data}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    async loadStudentsList() {
        try {
            const res = await this.fetchWithAuth('/api/teacher/students');
            const data = await res.json();
            this.studentsCache = data.students || [];
            this.renderStudentsTable(this.studentsCache);
            this.populateClassFilter(this.studentsCache);
        } catch (err) {
            console.error('Error fetching students:', err);
        }
    }

    populateClassFilter(students) {
        const select = document.getElementById('studentClassFilter');
        if (!select) return;

        const classes = [...new Set(students.map(s => s.classe).filter(Boolean))];
        const currentVal = select.value;
        select.innerHTML = '<option value="all">Toutes les classes</option>' + 
            classes.map(c => `<option value="${c}">${c}</option>`).join('');
        select.value = currentVal;
    }

    renderStudentsTable(students) {
        const tbody = document.getElementById('studentsTableBody');
        if (!tbody) return;

        const countEl = document.getElementById('studentsFilteredCount');
        if (countEl) countEl.textContent = `${students.length} élève(s)`;

        if (students.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-8 text-center text-slate-500">
                        Aucun élève trouvé avec ces critères de recherche.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = students.map(s => {
            const hours = Math.floor(s.total_seconds / 3600);
            const mins = Math.floor((s.total_seconds % 3600) / 60);
            const timeStr = hours > 0 ? `${hours}h ${mins}min` : `${mins} min`;

            const onlineBadge = s.is_online ? `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 online-dot"></span> En ligne
                </span>
            ` : `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                    <span class="w-2 h-2 rounded-full bg-slate-400"></span> Hors ligne
                </span>
            `;

            return `
                <tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-100">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm shadow-sm">
                                ${s.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <div class="font-semibold text-slate-900">${s.full_name}</div>
                                <div class="text-xs text-slate-500">@${s.username} ${s.email ? `• ${s.email}` : ''}</div>
                            </div>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-3 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded-lg border border-slate-200">
                            ${s.classe}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        ${onlineBadge}
                        <div class="text-[11px] text-slate-400 mt-1">Dernière visite : ${this.formatRelativeTime(s.last_active_at)}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="font-bold text-slate-800">${timeStr}</div>
                        <div class="text-xs text-slate-500">${s.total_sessions} connexion(s)</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center gap-3 text-xs">
                            <span class="inline-flex items-center gap-1 text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                                👁️ ${s.views_count} vues
                            </span>
                            <span class="inline-flex items-center gap-1 text-amber-700 font-medium bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                                ⬇️ ${s.downloads_count} téléch.
                            </span>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm space-x-1.5">
                        <button onclick="teacherDashboard.openStudentDossier(${s.id})" 
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition-all hover:scale-102">
                            <span>📂</span> Historique & Dossier
                        </button>
                        <button onclick="teacherDashboard.deleteStudent(${s.id}, '${s.full_name.replace(/'/g, "\\'")}')" 
                                class="inline-flex items-center p-1.5 rounded-lg text-xs font-semibold bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 transition-all" title="Supprimer définitivement l'élève">
                            🗑️
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    filterStudents() {
        const search = (document.getElementById('studentSearchInput')?.value || '').toLowerCase().trim();
        const selectedClass = document.getElementById('studentClassFilter')?.value || 'all';

        const filtered = this.studentsCache.filter(s => {
            const matchesSearch = !search || 
                s.full_name.toLowerCase().includes(search) || 
                s.username.toLowerCase().includes(search) || 
                (s.email && s.email.toLowerCase().includes(search));

            const matchesClass = selectedClass === 'all' || s.classe === selectedClass;

            return matchesSearch && matchesClass;
        });

        this.renderStudentsTable(filtered);
    }

    async openStudentDossier(studentId) {
        this.currentDossierStudentId = studentId;
        const modal = document.getElementById('studentDossierModal');
        if (!modal) return;

        // Show modal with loading state
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        document.getElementById('dossierContent').innerHTML = `
            <div class="py-16 text-center text-slate-500">
                <div class="inline-block animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-3"></div>
                <div>Chargement de l'historique détaillé de l'élève...</div>
            </div>
        `;

        try {
            const res = await this.fetchWithAuth(`/api/teacher/students/${studentId}`);
            if (!res.ok) throw new Error('Erreur lors de la récupération du dossier');
            const data = await res.json();
            this.renderDossierModal(data);
        } catch (err) {
            document.getElementById('dossierContent').innerHTML = `
                <div class="p-6 text-center text-red-600 bg-red-50 rounded-xl">
                    Erreur de chargement : ${err.message}
                </div>
            `;
        }
    }

    renderDossierModal(data) {
        const { student, stats, files_consulted, timeline, sessions } = data;

        const hours = Math.floor(stats.total_time_seconds / 3600);
        const mins = Math.floor((stats.total_time_seconds % 3600) / 60);
        const timeStr = hours > 0 ? `${hours}h ${mins}min` : `${mins} min`;

        const filesHtml = files_consulted.length === 0 ? `
            <p class="text-sm text-slate-500 py-4 text-center">Aucun fichier consulté pour l'instant.</p>
        ` : `
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead>
                        <tr class="bg-slate-100 text-slate-700 text-xs uppercase tracking-wider">
                            <th class="px-4 py-3 rounded-l-lg">Document</th>
                            <th class="px-4 py-3">Cours & Matière</th>
                            <th class="px-4 py-3 text-center">Vues</th>
                            <th class="px-4 py-3 text-center">Temps de lecture</th>
                            <th class="px-4 py-3 text-center">Téléchargé</th>
                            <th class="px-4 py-3 rounded-r-lg">Dernière consultation</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        ${files_consulted.map(f => {
                            const readMins = Math.floor(f.total_reading_seconds / 60);
                            const readSecs = f.total_reading_seconds % 60;
                            const readTime = readMins > 0 ? `${readMins}m ${readSecs}s` : `${readSecs}s`;

                            return `
                                <tr class="hover:bg-slate-50 transition-colors">
                                    <td class="px-4 py-3 font-semibold text-slate-800 flex items-center gap-2">
                                        <span class="text-lg">📄</span>
                                        <span>${f.file_name}</span>
                                    </td>
                                    <td class="px-4 py-3 text-xs text-slate-600">${f.course_title || 'Cours'} <br/><span class="text-slate-400">${f.subject || ''}</span></td>
                                    <td class="px-4 py-3 text-center font-bold text-blue-600">${f.view_count} fois</td>
                                    <td class="px-4 py-3 text-center font-bold text-emerald-700">${readTime}</td>
                                    <td class="px-4 py-3 text-center">${f.download_count > 0 ? `<span class="px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-800 rounded">Oui (${f.download_count}x)</span>` : '<span class="text-slate-400 text-xs">Non</span>'}</td>
                                    <td class="px-4 py-3 text-xs text-slate-500">${this.formatRelativeTime(f.last_consultation_at)}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        const timelineHtml = timeline.length === 0 ? `
            <p class="text-sm text-slate-500 py-4 text-center">Aucun événement enregistré.</p>
        ` : `
            <div class="relative border-l-2 border-blue-200 ml-4 space-y-4 my-2">
                ${timeline.map(t => {
                    let dotColor = 'bg-blue-500';
                    let badge = '📖 Action';
                    if (t.action_type === 'LOGIN') {
                        dotColor = 'bg-emerald-500';
                        badge = '🔑 Connexion';
                    } else if (t.action_type === 'DOWNLOAD_FILE') {
                        dotColor = 'bg-amber-500';
                        badge = '⬇️ Téléchargement';
                    } else if (t.action_type === 'VIEW_FILE') {
                        dotColor = 'bg-indigo-500';
                        badge = '👁️ Lecture';
                    }

                    return `
                        <div class="relative pl-6">
                            <span class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full ${dotColor} ring-4 ring-white shadow-sm"></span>
                            <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
                                <div class="flex items-center justify-between text-xs mb-1">
                                    <span class="font-bold text-slate-800">${badge}</span>
                                    <span class="text-slate-400">${this.formatFullDate(t.created_at)}</span>
                                </div>
                                <div class="text-sm text-slate-700 font-medium">${t.description}</div>
                                ${t.extra_data ? `<div class="text-xs text-slate-500 mt-1 bg-white p-1.5 rounded border border-slate-200 inline-block font-mono">${t.extra_data}</div>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;

        const sessionsHtml = sessions.length === 0 ? `
            <p class="text-sm text-slate-500 py-4 text-center">Aucune session enregistrée.</p>
        ` : `
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead>
                        <tr class="bg-slate-100 text-slate-700 text-xs uppercase">
                            <th class="px-4 py-2 rounded-l-lg">Début de session</th>
                            <th class="px-4 py-2">Durée active</th>
                            <th class="px-4 py-2">Adresse IP</th>
                            <th class="px-4 py-2 rounded-r-lg">Statut</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        ${sessions.map(s => {
                            const smins = Math.floor(s.duration_seconds / 60);
                            const ssecs = s.duration_seconds % 60;
                            return `
                                <tr class="hover:bg-slate-50 text-xs">
                                    <td class="px-4 py-2.5 font-medium text-slate-800">${this.formatFullDate(s.started_at)}</td>
                                    <td class="px-4 py-2.5 font-bold text-blue-600">${smins}m ${ssecs}s</td>
                                    <td class="px-4 py-2.5 font-mono text-slate-500">${s.ip_address || 'Local'}</td>
                                    <td class="px-4 py-2.5">${s.is_active ? '<span class="text-emerald-600 font-bold">Active</span>' : '<span class="text-slate-400">Terminée</span>'}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        document.getElementById('dossierContent').innerHTML = `
            <div class="space-y-6">
                <!-- Header profile banner -->
                <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-blue-700 to-indigo-800 text-white shadow-md">
                    <div class="flex items-center gap-4">
                        <div class="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center text-2xl font-black text-white shadow-inner">
                            ${student.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <h3 class="text-xl font-bold tracking-tight">${student.full_name}</h3>
                            <p class="text-blue-100 text-xs">Classe : <span class="font-semibold text-white">${student.classe}</span> • Identifiant : <span class="font-mono bg-white/10 px-2 py-0.5 rounded">@${student.username}</span></p>
                            <p class="text-blue-200 text-xs mt-0.5">${student.email || 'Aucun email spécifié'}</p>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="teacherDashboard.resetPasswordPrompt(${student.id}, '${student.full_name}')" 
                                class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/20 hover:bg-white/30 text-white transition-all">
                            🔑 Réinitialiser MDP
                        </button>
                    </div>
                </div>

                <!-- 3 Stat cards -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div class="p-4 rounded-xl bg-blue-50/70 border border-blue-200">
                        <div class="text-xs text-blue-700 font-medium">Temps Total sur le Site</div>
                        <div class="text-2xl font-black text-blue-900 mt-1">${timeStr}</div>
                        <div class="text-[11px] text-blue-600 mt-0.5">Mesuré pendant la présence active</div>
                    </div>
                    <div class="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
                        <div class="text-xs text-emerald-700 font-medium">Fichiers Distincts Consultés</div>
                        <div class="text-2xl font-black text-emerald-900 mt-1">${stats.files_count}</div>
                        <div class="text-[11px] text-emerald-600 mt-0.5">Supports ouverts et lus</div>
                    </div>
                    <div class="p-4 rounded-xl bg-purple-50/70 border border-purple-200">
                        <div class="text-xs text-purple-700 font-medium">Nombre de Sessions</div>
                        <div class="text-2xl font-black text-purple-900 mt-1">${stats.total_sessions}</div>
                        <div class="text-[11px] text-purple-600 mt-0.5">Dernière visite : ${this.formatRelativeTime(student.last_active_at)}</div>
                    </div>
                </div>

                <!-- Tabs inside Dossier: Fichiers / Timeline / Sessions -->
                <div class="border-b border-slate-200 flex gap-4">
                    <button onclick="teacherDashboard.switchDossierTab('files')" id="dossierTabBtn-files" 
                            class="pb-2.5 text-sm font-bold text-blue-600 border-b-2 border-blue-600 transition-all flex items-center gap-1.5">
                        <span>📑</span> Fichiers & Documents (${files_consulted.length})
                    </button>
                    <button onclick="teacherDashboard.switchDossierTab('timeline')" id="dossierTabBtn-timeline" 
                            class="pb-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-all flex items-center gap-1.5">
                        <span>⏱️</span> Chronologie de l'activité (${timeline.length})
                    </button>
                    <button onclick="teacherDashboard.switchDossierTab('sessions')" id="dossierTabBtn-sessions" 
                            class="pb-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-all flex items-center gap-1.5">
                        <span>🌐</span> Sessions de connexion (${sessions.length})
                    </button>
                </div>

                <!-- Tab Contents -->
                <div id="dossierTab-files">${filesHtml}</div>
                <div id="dossierTab-timeline" class="hidden">${timelineHtml}</div>
                <div id="dossierTab-sessions" class="hidden">${sessionsHtml}</div>
            </div>
        `;
    }

    switchDossierTab(tabName) {
        ['files', 'timeline', 'sessions'].forEach(t => {
            const btn = document.getElementById(`dossierTabBtn-${t}`);
            const content = document.getElementById(`dossierTab-${t}`);
            if (t === tabName) {
                btn.className = 'pb-2.5 text-sm font-bold text-blue-600 border-b-2 border-blue-600 transition-all flex items-center gap-1.5';
                content.classList.remove('hidden');
            } else {
                btn.className = 'pb-2.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-all flex items-center gap-1.5';
                content.classList.add('hidden');
            }
        });
    }

    closeDossierModal() {
        const modal = document.getElementById('studentDossierModal');
        if (modal) modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    async resetPasswordPrompt(studentId, studentName) {
        const newPwd = prompt(`Réinitialiser le mot de passe pour "${studentName}" :`, 'eleve123');
        if (!newPwd) return;

        try {
            const res = await fetch(`/api/teacher/students/${studentId}/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_password: newPwd })
            });
            const data = await res.json();
            alert(data.message || 'Mot de passe modifié avec succès.');
        } catch (err) {
            alert('Erreur : ' + err.message);
        }
    }

    formatRelativeTime(dateStr) {
        if (!dateStr) return 'Jamais';
        const d = new Date(dateStr.replace(' ', 'T') + 'Z');
        const now = new Date();
        const diffSecs = Math.floor((now - d) / 1000);

        if (diffSecs < 60) return 'À l\'instant';
        if (diffSecs < 3600) return `Il y a ${Math.floor(diffSecs / 60)} min`;
        if (diffSecs < 86400) return `Il y a ${Math.floor(diffSecs / 3600)} h`;
        return `Il y a ${Math.floor(diffSecs / 86400)} j`;
    }

    formatFullDate(dateStr) {
        if (!dateStr) return '-';
        const d = new Date(dateStr.replace(' ', 'T') + 'Z');
        return d.toLocaleString('fr-FR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    // --- Classes Management Methods ---
    async loadClasses() {
        try {
            const res = await this.fetchWithAuth('/api/teacher/classes');
            if (!res.ok) throw new Error('Impossible de charger les classes');
            const data = await res.json();
            const classes = data.classes || [];

            this.classesCache = classes;
            this.renderClassesGrid(classes);
            this.updateClassSelectDropdowns(classes);
        } catch (err) {
            console.error('Error loading classes:', err);
        }
    }

    updateClassSelectDropdowns(classes) {
        // Update #studentClassFilter in the Dashboard
        const filterSelect = document.getElementById('studentClassFilter');
        if (filterSelect) {
            const curVal = filterSelect.value || 'all';
            let html = '<option value="all">Toutes les classes</option>';
            classes.forEach(c => {
                html += `<option value="${c.name}">${c.name} (${c.student_count} élève${c.student_count > 1 ? 's' : ''})</option>`;
            });
            filterSelect.innerHTML = html;
            filterSelect.value = curVal;
        }

        // Update #newStudentClasse
        const studentSelect = document.getElementById('newStudentClasse');
        if (studentSelect) {
            const curVal = studentSelect.value;
            let html = '';
            classes.forEach(c => {
                html += `<option value="${c.name}">${c.name}</option>`;
            });
            studentSelect.innerHTML = html;
            if (curVal && Array.from(studentSelect.options).some(o => o.value === curVal)) {
                studentSelect.value = curVal;
            }
        }

        // Update course class select if exists
        const courseClassSelect = document.querySelector('#newCourseForm select[name="classe"]');
        if (courseClassSelect) {
            const curVal = courseClassSelect.value;
            let html = '<option value="Toutes les classes">Toutes les classes (Tous les élèves)</option>';
            classes.forEach(c => {
                html += `<option value="${c.name}">${c.name}</option>`;
            });
            courseClassSelect.innerHTML = html;
            if (curVal) courseClassSelect.value = curVal;
        }
    }

    renderClassesGrid(classes) {
        const grid = document.getElementById('classesCardsGrid');
        if (!grid) return;

        if (!classes.length) {
            grid.innerHTML = `
                <div class="col-span-full py-12 text-center bg-white rounded-3xl border border-slate-200">
                    <span class="text-4xl">🏫</span>
                    <h3 class="font-bold text-slate-800 text-base mt-2">Aucune classe pour le moment</h3>
                    <p class="text-xs text-slate-500 mt-1">Créez votre première classe pour commencer à organiser vos élèves.</p>
                    <button onclick="app.openNewClassModal()" class="mt-4 px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold">
                        ➕ Créer une classe
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = classes.map(c => {
            const studentCount = c.students_count !== undefined ? c.students_count : (c.student_count || 0);
            const courseCount = c.courses_count !== undefined ? c.courses_count : (c.course_count || 0);
            const onlineCount = c.online_count !== undefined ? c.online_count : (c.online_students || 0);
            const totalSecs = c.total_time_seconds || 0;
            const hours = Math.floor(totalSecs / 3600);
            const mins = Math.floor((totalSecs % 3600) / 60);
            const timeDisplay = hours > 0 ? `${hours}h ${mins}m` : `${mins} min`;

            return `
                <div class="bg-white rounded-3xl border border-slate-200/80 shadow-xs hover:shadow-md transition-all p-6 flex flex-col justify-between group">
                    <div>
                        <!-- Header with Name & Level -->
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <span class="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                                    ${c.level || 'Classe Active'}
                                </span>
                                <h3 class="text-xl font-black text-slate-900 mt-2 tracking-tight group-hover:text-blue-600 transition-colors">
                                    ${c.name}
                                </h3>
                                ${c.description ? `<p class="text-xs text-slate-500 mt-1 line-clamp-2">${c.description}</p>` : ''}
                            </div>
                            <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl shadow-md shadow-blue-500/20 shrink-0">
                                🎓
                            </div>
                        </div>

                        <!-- Stats Pill Grid -->
                        <div class="grid grid-cols-3 gap-2 mt-5 p-3 rounded-2xl bg-slate-50 border border-slate-100 text-center">
                            <div>
                                <div class="text-[10px] font-bold uppercase text-slate-400">Élèves</div>
                                <div class="text-lg font-black text-slate-800 mt-0.5">${studentCount}</div>
                            </div>
                            <div>
                                <div class="text-[10px] font-bold uppercase text-slate-400">Cours</div>
                                <div class="text-lg font-black text-blue-600 mt-0.5">${courseCount}</div>
                            </div>
                            <div>
                                <div class="text-[10px] font-bold uppercase text-slate-400">Temps Étudié</div>
                                <div class="text-xs font-bold text-slate-700 mt-1">${timeDisplay}</div>
                            </div>
                        </div>

                        ${onlineCount > 0 ? `
                            <div class="mt-3 flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                                <span class="w-2 h-2 rounded-full bg-emerald-500 online-dot"></span>
                                ${onlineCount} élève(s) actuellement en ligne
                            </div>
                        ` : ''}
                    </div>

                    <!-- Card Action Buttons -->
                    <div class="mt-6 pt-4 border-t border-slate-100 space-y-2">
                        <button onclick="teacherDashboard.openClassDetail(${c.id}, '${c.name.replace(/'/g, "\\'")}', '${(c.level || '').replace(/'/g, "\\'")}')" 
                                class="w-full py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-2">
                            <span>👥</span> Voir les élèves (${studentCount})
                        </button>

                        <div class="flex items-center gap-2">
                            <button onclick="app.openNewStudentModalForClass('${c.name.replace(/'/g, "\\'")}')" 
                                    class="flex-1 py-2 px-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-bold transition-all text-center">
                                ➕ Élève
                            </button>
                            <button onclick="app.openExcelImportModalForClass('${c.name.replace(/'/g, "\\'")}')" 
                                    class="flex-1 py-2 px-2.5 rounded-xl border border-emerald-200 bg-emerald-50/50 hover:bg-emerald-100/50 text-emerald-800 text-[11px] font-bold transition-all text-center">
                                📗 Excel
                            </button>
                            ${window.app?.currentUser?.is_admin ? `
                                <button onclick="teacherDashboard.deleteClass(${c.id}, '${c.name.replace(/'/g, "\\'")}')" 
                                        class="p-2 rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 text-red-600 text-xs transition-all" title="Supprimer la classe">
                                    🗑️
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async openClassDetail(classId, className, classLevel) {
        const grid = document.getElementById('classesCardsGrid');
        const detailContainer = document.getElementById('classDetailContainer');
        const titleEl = document.getElementById('classDetailTitle');
        const descEl = document.getElementById('classDetailDesc');
        const addBtn = document.getElementById('classDetailAddStudentBtn');
        const importBtn = document.getElementById('classDetailImportExcelBtn');
        const tbody = document.getElementById('classStudentsTableBody');

        if (grid) grid.classList.add('hidden');
        if (detailContainer) detailContainer.classList.remove('hidden');

        if (titleEl) titleEl.textContent = `Classe : ${className} ${classLevel ? `(${classLevel})` : ''}`;
        if (descEl) descEl.textContent = `Liste des élèves appartenant exclusivement à la classe ${className}`;

        if (addBtn) addBtn.onclick = () => app.openNewStudentModalForClass(className);
        if (importBtn) importBtn.onclick = () => app.openExcelImportModalForClass(className);

        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-xs text-slate-400">Chargement des élèves de la classe...</td></tr>`;
        }

        try {
            const res = await this.fetchWithAuth(`/api/teacher/classes/${classId}/students`);
            if (!res.ok) throw new Error('Impossible de charger les élèves');
            const data = await res.json();
            const students = data.students || [];

            if (!students.length) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="p-12 text-center text-slate-500">
                            <span class="text-3xl">👥</span>
                            <div class="font-bold text-sm mt-2">Aucun élève inscrit dans cette classe</div>
                            <div class="text-xs text-slate-400 mt-1">Utilisez le bouton "Inscrire un élève" ou "Importer Excel" pour ajouter des élèves à cette classe.</div>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = students.map(s => {
                const totalSecs = s.total_seconds !== undefined ? s.total_seconds : (s.total_time_seconds || 0);
                const hours = Math.floor(totalSecs / 3600);
                const mins = Math.floor((totalSecs % 3600) / 60);
                const secs = totalSecs % 60;
                const timeString = hours > 0 ? `${hours}h ${mins}m` : `${mins}m ${secs}s`;

                const initials = (s.full_name || 'EL').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
                const isOnline = Boolean(s.is_online);
                const viewsCount = s.views_count !== undefined ? s.views_count : (s.consultations_count || 0);

                return `
                    <tr class="hover:bg-slate-50/80 transition-colors">
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-slate-700 to-slate-800 text-white font-bold text-xs flex items-center justify-center shrink-0">
                                    ${initials}
                                </div>
                                <div>
                                    <div class="font-bold text-slate-900">${s.full_name}</div>
                                    <div class="text-xs text-slate-400">@${s.username} ${s.email ? `• ${s.email}` : ''}</div>
                                </div>
                            </div>
                        </td>
                        <td class="px-6 py-4">
                            ${isOnline ? `
                                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 online-dot"></span> Connecté
                                </span>
                            ` : `
                                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
                                    Inactif (${this.formatRelativeTime(s.last_active_at)})
                                </span>
                            `}
                        </td>
                        <td class="px-6 py-4 font-mono font-bold text-blue-700 text-sm">
                            ${timeString}
                        </td>
                        <td class="px-6 py-4">
                            <span class="font-bold text-slate-800">${viewsCount}</span>
                            <span class="text-xs text-slate-400"> consultations (${s.downloads_count || 0} tél.)</span>
                        </td>
                        <td class="px-6 py-4 text-right space-x-1.5 whitespace-nowrap">
                            <button onclick="teacherDashboard.openStudentDossier(${s.id})" 
                                    class="px-2.5 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-bold transition-all" title="Dossier d'audit">
                                🔎 Audit
                            </button>
                            <button onclick="teacherDashboard.resetPasswordPrompt(${s.id}, '${s.full_name.replace(/'/g, "\\'")}')" 
                                    class="px-2 py-1.5 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 text-xs font-semibold transition-all" title="Changer le mot de passe">
                                🔑
                            </button>
                            <button onclick="teacherDashboard.removeStudentFromClass(${s.id}, '${s.full_name.replace(/'/g, "\\'")}', ${classId}, '${className.replace(/'/g, "\\'")}')" 
                                    class="px-2.5 py-1.5 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 text-xs font-semibold transition-all" title="Retirer l'élève de la classe ${className}">
                                🚫 Retirer
                            </button>
                            <button onclick="teacherDashboard.deleteStudent(${s.id}, '${s.full_name.replace(/'/g, "\\'")}', ${classId}, '${className.replace(/'/g, "\\'")}')" 
                                    class="px-2 py-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 text-xs font-semibold transition-all" title="Supprimer définitivement l'élève">
                                🗑️
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-xs text-red-500">Erreur : ${err.message}</td></tr>`;
        }
    }

    closeClassDetail() {
        const grid = document.getElementById('classesCardsGrid');
        const detailContainer = document.getElementById('classDetailContainer');
        if (grid) grid.classList.remove('hidden');
        if (detailContainer) detailContainer.classList.add('hidden');
    }

    async deleteClass(classId, className) {
        if (!confirm(`Êtes-vous certain de vouloir supprimer la classe "${className}" ?\nSes élèves seront réassignés à la classe "Général".`)) {
            return;
        }

        try {
            const res = await this.fetchWithAuth(`/api/teacher/classes/${classId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la suppression de la classe');
            alert(data.message || `Classe "${className}" supprimée.`);
            await this.loadClasses();
        } catch (err) {
            alert('Erreur : ' + err.message);
        }
    }

    async removeStudentFromClass(studentId, studentName, classId, className) {
        if (!confirm(`Voulez-vous retirer l'élève "${studentName}" de la classe "${className}" ?\n(Son compte sera conservé mais ne sera plus associé à cette classe).`)) {
            return;
        }

        try {
            const res = await this.fetchWithAuth(`/api/teacher/students/${studentId}/remove-from-class`, {
                method: 'POST'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors du retrait de l\'élève');
            alert(data.message || `L'élève "${studentName}" a été retiré de la classe.`);
            if (classId) {
                await this.openClassDetail(classId, className);
            }
            await this.loadClasses();
            await this.loadStudentsList();
        } catch (err) {
            alert('Erreur : ' + err.message);
        }
    }

    async deleteStudent(studentId, studentName, classId = null, className = null) {
        if (!confirm(`ATTENTION : Êtes-vous certain de vouloir supprimer DÉFINITIVEMENT l'élève "${studentName}" ?\nCette action supprimera son compte, son accès et l'ensemble de son historique d'audit.`)) {
            return;
        }

        try {
            const res = await this.fetchWithAuth(`/api/teacher/students/${studentId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la suppression');
            alert(data.message || `Compte de l'élève "${studentName}" supprimé.`);
            if (classId) {
                await this.openClassDetail(classId, className);
            }
            await this.loadClasses();
            await this.loadStudentsList();
            await this.loadDashboard();
        } catch (err) {
            alert('Erreur : ' + err.message);
        }
    }
}

// Global instance
window.teacherDashboard = new TeacherDashboard();
