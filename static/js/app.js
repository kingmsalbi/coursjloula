/**
 * Main Application Controller for Espace Pédagogique Msalbi
 */
class App {
    constructor() {
        this.currentUser = null;
        this.currentView = 'loading';
        this.courses = [];
        this.selectedSubject = 'all';
        this.selectedClass = 'all';
        this.searchQuery = '';
        this.activeReadingFile = null;

        // Messaging state
        this.activeConversation = null;
        this.messagingPollInterval = null;
        this.cachedConversations = { channels: [], direct_chats: [] };
        this.cachedContacts = [];

        this.initEventListeners();
        this.restoreRememberedUser();
        this.init();
    }

    getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('auth_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
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

    async init() {
        if (window.isAndroidApp || window.AndroidBridge) {
            document.getElementById('mobileAppInstallBanner')?.remove();
        }
        await this.loadPublicClasses();
        const initialClasse = document.getElementById('loginClasse')?.value || '2 IT';
        const savedUsername = localStorage.getItem('saved_username');
        if (initialClasse !== 'teacher') {
            await this.loadStudentsForClasse(initialClasse, savedUsername);
        } else {
            await this.onClasseChanged('teacher');
        }
        await this.checkAuth();
        await this.checkUnreadMessages();
        // Vérification des non-lus toutes les 30s uniquement si l'onglet est actif
        setInterval(() => {
            if (!document.hidden) this.checkUnreadMessages();
        }, 30000);
    }

    async loadPublicClasses() {
        try {
            const res = await fetch('/api/public/classes');
            let apiClasses = [];
            if (res.ok) {
                const data = await res.json();
                apiClasses = data.classes || [];
            }

            const select = document.getElementById('loginClasse');
            if (!select) return;

            // Liste garantie de toutes les classes officielles
            const defaultClasses = [
                '1s1', '1s2', '1s3', '2 IT', '2 ECO', '2 Lettre', '2 science', '3eco', '4 science', '4eco'
            ];

            const existingNames = new Set(apiClasses.map(c => c.name));
            defaultClasses.forEach(defName => {
                if (!existingNames.has(defName)) {
                    apiClasses.push({ id: 999, name: defName, level: 'Secondaire' });
                }
            });

            this.cachedPublicClasses = apiClasses;
            this.populateNewCourseClasses();

            const curVal = select.value;
            let html = '';
            apiClasses.forEach(c => {
                html += `<option value="${c.name}">🎓 Classe : ${c.name}</option>`;
            });
            html += `<option value="teacher">👨‍🏫 Espace Enseignants</option>`;
            select.innerHTML = html;

            if (curVal && Array.from(select.options).some(o => o.value === curVal)) {
                select.value = curVal;
            } else if (apiClasses.length > 0) {
                select.value = apiClasses[0].name;
            }

            if (select.value !== 'teacher') {
                await this.loadStudentsForClasse(select.value);
            }
        } catch (e) {
            console.warn('Could not load public classes', e);
        }
    }

    populateNewCourseClasses() {
        const select = document.getElementById('newCourseClasse');
        if (!select) return;
        const isAdmin = this.currentUser?.is_admin;
        const curVal = select.value;
        let html = '';

        if (isAdmin) {
            html += '<option value="Toutes les classes">Toutes les classes</option>';
            const classes = this.cachedPublicClasses || [];
            classes.forEach(c => {
                html += `<option value="${c.name}">${c.name}</option>`;
            });
        } else {
            const assigned = this.currentUser?.assigned_classes || [];
            if (assigned.length === 0) {
                html += '<option value="">Aucune classe assignée</option>';
            } else {
                assigned.forEach(cname => {
                    html += `<option value="${cname}">${cname}</option>`;
                });
            }
        }
        select.innerHTML = html;
        if (curVal && Array.from(select.options).some(o => o.value === curVal)) {
            select.value = curVal;
        }
    }

    async onClasseChanged(classe) {
        const studentContainer = document.getElementById('loginStudentSelectContainer');
        const manualContainer = document.getElementById('loginUsernameInputContainer');
        const usernameInput = document.getElementById('loginUsername');
        const studentSelect = document.getElementById('loginStudentSelect');
        const selectLabel = document.getElementById('loginSelectLabel');
        const manualLabel = document.getElementById('loginUsernameLabel');

        if (manualContainer) manualContainer.classList.add('hidden');
        if (studentContainer) studentContainer.classList.remove('hidden');

        if (classe === 'teacher') {
            if (selectLabel) selectLabel.textContent = 'Sélectionnez votre Nom (Enseignant) *';
            if (manualLabel) manualLabel.textContent = 'Identifiant Enseignant *';
            if (usernameInput) usernameInput.placeholder = 'Ex: msalbi ou jamila.rahmeni';
            await this.loadTeachers();
        } else {
            if (selectLabel) selectLabel.textContent = 'Sélectionnez votre Nom (Élève) *';
            if (manualLabel) manualLabel.textContent = 'Identifiant de connexion *';
            if (usernameInput) {
                usernameInput.placeholder = 'Ex: msalbi ou prenom.nom';
                usernameInput.value = '';
            }
            await this.loadStudentsForClasse(classe);
        }
    }

    async loadTeachers(selectUsername = null) {
        const studentSelect = document.getElementById('loginStudentSelect');
        const usernameInput = document.getElementById('loginUsername');
        if (!studentSelect) return;

        studentSelect.innerHTML = '<option value="">⏳ Chargement des enseignants...</option>';

        let teachers = [
            { id: 1, username: "msalbi", full_name: "👨‍🏫 Professeur Msalbi" },
            { id: 88, username: "jamila.rahmeni", full_name: "👩‍🏫 Jamila Rahmeni" }
        ];

        try {
            const res = await fetch('/api/public/teachers');
            if (res.ok) {
                const data = await res.json();
                if (data.teachers && data.teachers.length > 0) {
                    teachers = data.teachers.map(t => {
                        let name = t.full_name || t.username;
                        let prefix = t.username === 'msalbi' ? '👨‍🏫 ' : '👩‍🏫 ';
                        return {
                            id: t.id,
                            username: t.username,
                            full_name: `${prefix}${name}`
                        };
                    });
                }
            }
        } catch (e) {
            console.warn('Fallback static teachers:', e);
        }

        let html = '<option value="">-- Choisissez votre nom d\'enseignant --</option>';
        teachers.forEach(t => {
            html += `<option value="${t.username}">${t.full_name} (${t.username})</option>`;
        });
        studentSelect.innerHTML = html;

        const targetUser = selectUsername || (usernameInput ? usernameInput.value : '') || 'msalbi';
        if (targetUser && Array.from(studentSelect.options).some(o => o.value === targetUser)) {
            studentSelect.value = targetUser;
            if (usernameInput) usernameInput.value = targetUser;
        } else if (teachers.length > 0) {
            studentSelect.value = teachers[0].username;
            if (usernameInput) usernameInput.value = teachers[0].username;
        }

        document.getElementById('loginPassword')?.focus();
    }

    async loadStudentsForClasse(classe, selectUsername = null) {
        const studentSelect = document.getElementById('loginStudentSelect');
        const usernameInput = document.getElementById('loginUsername');
        if (!studentSelect) return;

        studentSelect.innerHTML = '<option value="">⏳ Chargement des élèves...</option>';

        try {
            const res = await fetch(`/api/public/students?classe=${encodeURIComponent(classe)}`);
            if (!res.ok) throw new Error('Erreur chargement élèves');
            const data = await res.json();
            const students = data.students || [];

            if (!students.length) {
                studentSelect.innerHTML = '<option value="">Aucun élève trouvé dans cette classe</option>';
                this.toggleManualLoginInput(true);
                return;
            }

            let html = '<option value="">-- Choisissez votre nom dans la liste --</option>';
            students.forEach(s => {
                html += `<option value="${s.username}">${s.full_name}</option>`;
            });
            studentSelect.innerHTML = html;

            const targetUser = selectUsername || (usernameInput ? usernameInput.value : '');
            if (targetUser && Array.from(studentSelect.options).some(o => o.value === targetUser)) {
                studentSelect.value = targetUser;
                if (usernameInput) usernameInput.value = targetUser;
            }
        } catch (e) {
            console.warn('Error fetching class students:', e);
            studentSelect.innerHTML = '<option value="">Impossible de charger la liste (saisie manuelle)</option>';
            this.toggleManualLoginInput(true);
        }
    }

    onStudentSelected(username) {
        const usernameInput = document.getElementById('loginUsername');
        if (usernameInput) usernameInput.value = username;
        if (username) {
            document.getElementById('loginPassword')?.focus();
        }
    }

    toggleManualLoginInput(isManual) {
        const studentContainer = document.getElementById('loginStudentSelectContainer');
        const manualContainer = document.getElementById('loginUsernameInputContainer');
        const usernameInput = document.getElementById('loginUsername');
        const studentSelect = document.getElementById('loginStudentSelect');

        if (isManual) {
            if (studentContainer) studentContainer.classList.add('hidden');
            if (manualContainer) manualContainer.classList.remove('hidden');
            if (usernameInput) {
                if (studentSelect && studentSelect.value) {
                    usernameInput.value = studentSelect.value;
                }
                usernameInput.focus();
            }
        } else {
            if (manualContainer) manualContainer.classList.add('hidden');
            if (studentContainer) studentContainer.classList.remove('hidden');
            if (studentSelect && usernameInput && usernameInput.value) {
                studentSelect.value = usernameInput.value;
            }
        }
    }

    restoreRememberedUser() {
        try {
            const savedUsername = localStorage.getItem('saved_username');
            const savedClasse = localStorage.getItem('saved_classe');
            const usernameInput = document.getElementById('loginUsername');
            const classeInput = document.getElementById('loginClasse');
            const rememberMeCheckbox = document.getElementById('loginRememberMe');
            if (savedUsername && usernameInput) {
                usernameInput.value = savedUsername;
                if (rememberMeCheckbox) rememberMeCheckbox.checked = true;
            }
            if (savedClasse && classeInput) {
                classeInput.value = savedClasse;
            }
        } catch (e) {}
    }

    async checkAuth() {
        try {
            const res = await this.fetchWithAuth('/api/auth/me');
            const data = await res.json();
            if (data.authenticated && data.user) {
                this.currentUser = data.user;
                if (data.session_token) {
                    localStorage.setItem('auth_token', data.session_token);
                }
                this.updateUserBadge();
                this.checkUnreadMessages();

                // Initialize tracker for students
                if (data.user.role === 'student') {
                    window.studentTracker.init(data.user, data.session_token);
                    this.switchView('student-courses');
                    await this.loadCourses();
                } else if (data.user.role === 'teacher') {
                    this.switchView('teacher-dashboard');
                    await window.teacherDashboard.loadDashboard();
                }
            } else {
                this.currentUser = null;
                window.studentTracker.stop();
                this.switchView('auth');
            }
        } catch (err) {
            console.error('Auth check error:', err);
            this.switchView('auth');
        }
    }

    initEventListeners() {
        // Close menus when clicking outside
        document.addEventListener('click', (e) => {
            const userMenuBtn = document.getElementById('userProfileMenuBtn');
            const userDropdown = document.getElementById('userProfileDropdown');
            if (userDropdown && !userDropdown.classList.contains('hidden')) {
                if (!userMenuBtn?.contains(e.target) && !userDropdown.contains(e.target)) {
                    this.closeUserMenu();
                }
            }
            const mobMenuBtn = document.getElementById('mobileMenuToggleBtn');
            const mobMenu = document.getElementById('mobileNavMenu');
            if (mobMenu && !mobMenu.classList.contains('hidden')) {
                if (!mobMenuBtn?.contains(e.target) && !mobMenu.contains(e.target)) {
                    this.closeMobileMenu();
                }
            }
        });

        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        // Search input
        const searchInput = document.getElementById('courseSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase().trim();
                this.renderCourses();
            });
        }

        // New Course form
        const newCourseForm = document.getElementById('newCourseForm');
        if (newCourseForm) {
            newCourseForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCreateCourse();
            });
        }

        // Edit Course form
        const editCourseForm = document.getElementById('editCourseForm');
        if (editCourseForm) {
            editCourseForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleUpdateCourse();
            });
        }

        // Import Excel form
        const importExcelForm = document.getElementById('importExcelForm');
        if (importExcelForm) {
            importExcelForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleExcelImport();
            });
        }

        // Change Password form
        const changePasswordForm = document.getElementById('changePasswordForm');
        if (changePasswordForm) {
            changePasswordForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleChangePassword();
            });
        }
    }

    switchView(viewName) {
        // STRICT ROLE-BASED ACCESS CONTROL:
        // A student ONLY has access to student-courses (courses & messaging)
        if (this.currentUser?.role === 'student') {
            if (viewName !== 'student-courses' && viewName !== 'auth') {
                viewName = 'student-courses';
            }
        } else if (this.currentUser?.role === 'teacher') {
            if (viewName === 'student-courses') {
                viewName = 'teacher-dashboard';
            }
        }

        this.currentView = viewName;
        
        // Hide all main view containers
        const views = ['authView', 'studentCoursesView', 'teacherDashboardView', 'teacherClassesView', 'teacherCoursesView'];
        views.forEach(v => {
            const el = document.getElementById(v);
            if (el) el.classList.add('hidden');
        });

        // Toggle user header elements
        const userMenu = document.getElementById('userNavMenu');
        const navTeacher = document.getElementById('navTeacherLinks');
        const mobTeacher = document.getElementById('mobileTeacherLinks');
        const mobStudent = document.getElementById('mobileStudentLinks');
        const navStudentPill = document.getElementById('navStudentPill');

        if (viewName === 'auth') {
            if (userMenu) userMenu.classList.add('hidden');
            if (navTeacher) {
                navTeacher.style.setProperty('display', 'none', 'important');
                navTeacher.classList.add('hidden');
            }
            if (mobTeacher) mobTeacher.classList.add('hidden');
            if (mobStudent) mobStudent.classList.add('hidden');
            this.closeMobileMenu();
            this.closeUserMenu();
            const authEl = document.getElementById('authView');
            if (authEl) authEl.classList.remove('hidden');
            this.loadPublicClasses();
        } else {
            if (userMenu) userMenu.classList.remove('hidden');
            this.closeMobileMenu();
            this.closeUserMenu();

            const isTeacher = this.currentUser?.role === 'teacher';

            if (isTeacher) {
                // TEACHER: Show teacher navigation bar
                if (navTeacher) {
                    navTeacher.style.setProperty('display', 'flex', 'important');
                    navTeacher.classList.remove('hidden');
                }
                if (mobTeacher) mobTeacher.classList.remove('hidden');
                if (mobStudent) mobStudent.classList.add('hidden');
                if (navStudentPill) navStudentPill.style.setProperty('display', 'none', 'important');

                if (viewName === 'teacher-dashboard') {
                    const el = document.getElementById('teacherDashboardView');
                    if (el) el.classList.remove('hidden');
                    this.setTeacherNavActive('dashboard');
                    window.teacherDashboard?.loadDashboard();
                } else if (viewName === 'teacher-classes') {
                    const el = document.getElementById('teacherClassesView');
                    if (el) el.classList.remove('hidden');
                    this.setTeacherNavActive('classes');
                    window.teacherDashboard?.closeClassDetail();
                    window.teacherDashboard?.loadClasses();
                } else if (viewName === 'teacher-courses') {
                    const el = document.getElementById('teacherCoursesView');
                    if (el) el.classList.remove('hidden');
                    this.setTeacherNavActive('courses');
                }
            } else {
                // STUDENT: L'élève n'a QUE les cours et les messages!
                // Cacher TOUS les liens, boutons et suivis enseignants
                if (navTeacher) {
                    navTeacher.style.setProperty('display', 'none', 'important');
                    navTeacher.classList.add('hidden');
                }
                if (mobTeacher) mobTeacher.classList.add('hidden');
                if (mobStudent) mobStudent.classList.remove('hidden');
                if (navStudentPill) navStudentPill.style.setProperty('display', 'none', 'important');

                const el = document.getElementById('studentCoursesView');
                if (el) el.classList.remove('hidden');
            }
        }
    }

    setTeacherNavActive(activeTab) {
        const btnDash = document.getElementById('navBtnTeacherDash');
        const btnClasses = document.getElementById('navBtnTeacherClasses');
        const btnCourses = document.getElementById('navBtnTeacherCourses');

        const mobDash = document.getElementById('mobBtnTeacherDash');
        const mobClasses = document.getElementById('mobBtnTeacherClasses');
        const mobCourses = document.getElementById('mobBtnTeacherCourses');

        const resetBtn = (btn) => {
            if (!btn) return;
            btn.classList.remove('bg-blue-700', 'text-white', 'shadow-xs');
            btn.classList.add('text-slate-600', 'hover:text-slate-900');
        };
        const activateBtn = (btn) => {
            if (!btn) return;
            btn.classList.add('bg-blue-700', 'text-white', 'shadow-xs');
            btn.classList.remove('text-slate-600', 'hover:text-slate-900');
        };

        const resetMobBtn = (btn) => {
            if (!btn) return;
            btn.classList.remove('bg-blue-600', 'text-white', 'shadow-xs');
            btn.classList.add('text-slate-700', 'hover:bg-blue-50', 'hover:text-blue-700');
        };
        const activateMobBtn = (btn) => {
            if (!btn) return;
            btn.classList.add('bg-blue-600', 'text-white', 'shadow-xs');
            btn.classList.remove('text-slate-700', 'hover:bg-blue-50', 'hover:text-blue-700');
        };

        resetBtn(btnDash);
        resetBtn(btnClasses);
        resetBtn(btnCourses);

        resetMobBtn(mobDash);
        resetMobBtn(mobClasses);
        resetMobBtn(mobCourses);

        if (activeTab === 'dashboard') {
            activateBtn(btnDash);
            activateMobBtn(mobDash);
        } else if (activeTab === 'classes') {
            activateBtn(btnClasses);
            activateMobBtn(mobClasses);
        } else if (activeTab === 'courses') {
            activateBtn(btnCourses);
            activateMobBtn(mobCourses);
        }
    }

    updateUserBadge() {
        if (!this.currentUser) return;
        const nameEl = document.getElementById('headerUserName');
        const roleEl = document.getElementById('headerUserRole');
        const avatarEl = document.getElementById('headerUserAvatar');
        const adminBtn = document.getElementById('navBtnAdminTeachers');
        const newClassBtn = document.getElementById('btnOpenNewClass');

        if (nameEl) nameEl.textContent = this.currentUser.full_name;
        if (roleEl) {
            if (this.currentUser.role === 'teacher') {
                roleEl.textContent = this.currentUser.is_admin ? 'Admin & Professeur' : 'Professeur';
            } else {
                roleEl.textContent = `Élève (${this.currentUser.classe})`;
            }
        }
        if (avatarEl) {
            const initials = this.currentUser.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            avatarEl.textContent = initials;
        }

        // Contrôle des accès selon le statut Administrateur
        if (adminBtn) {
            if (this.currentUser.is_admin) {
                adminBtn.classList.remove('hidden');
            } else {
                adminBtn.classList.add('hidden');
            }
        }
        if (newClassBtn) {
            if (this.currentUser.is_admin) {
                newClassBtn.classList.remove('hidden');
            } else {
                newClassBtn.classList.add('hidden');
            }
        }

        // Student Banner Greeting
        const greetingName = document.getElementById('studentGreetingName');
        if (greetingName) greetingName.textContent = this.currentUser.full_name;
        const greetingClass = document.getElementById('studentGreetingClass');
        if (greetingClass) greetingClass.textContent = this.currentUser.classe;

        // User Dropdown Details
        const dropName = document.getElementById('dropdownUserName');
        const dropRole = document.getElementById('dropdownUserRole');
        if (dropName) dropName.textContent = this.currentUser.full_name;
        if (dropRole) {
            dropRole.textContent = this.currentUser.role === 'teacher' 
                ? (this.currentUser.is_admin ? 'Admin & Professeur' : 'Professeur')
                : `Élève (${this.currentUser.classe})`;
        }

        // Mobile Drawer Details
        const mobName = document.getElementById('mobileUserName');
        const mobRole = document.getElementById('mobileUserRole');
        const mobAvatar = document.getElementById('mobileUserAvatar');
        const mobAdminBtn = document.getElementById('mobileNavBtnAdminTeachers');
        if (mobName) mobName.textContent = this.currentUser.full_name;
        if (mobRole) {
            mobRole.textContent = this.currentUser.role === 'teacher' 
                ? (this.currentUser.is_admin ? 'Admin & Professeur' : 'Professeur')
                : `Élève (${this.currentUser.classe})`;
        }
        if (mobAvatar) {
            const initials = this.currentUser.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            mobAvatar.textContent = initials;
        }
        if (mobAdminBtn) {
            if (this.currentUser.is_admin) mobAdminBtn.classList.remove('hidden');
            else mobAdminBtn.classList.add('hidden');
        }
    }

    // --- Header & Navigation Menu Handlers ---
    toggleUserMenu(e) {
        if (e) e.stopPropagation();
        const dropdown = document.getElementById('userProfileDropdown');
        if (dropdown) dropdown.classList.toggle('hidden');
    }

    closeUserMenu() {
        const dropdown = document.getElementById('userProfileDropdown');
        if (dropdown) dropdown.classList.add('hidden');
    }

    toggleMobileMenu(e) {
        if (e) e.stopPropagation();
        const menu = document.getElementById('mobileNavMenu');
        const backdrop = document.getElementById('mobileNavBackdrop');
        const hIcon = document.getElementById('hamburgerIcon');
        const cIcon = document.getElementById('closeMenuIcon');
        if (!menu) return;
        const isHidden = menu.classList.contains('hidden');
        if (isHidden) {
            menu.classList.remove('hidden');
            backdrop?.classList.remove('hidden');
            hIcon?.classList.add('hidden');
            cIcon?.classList.remove('hidden');
        } else {
            menu.classList.add('hidden');
            backdrop?.classList.add('hidden');
            hIcon?.classList.remove('hidden');
            cIcon?.classList.add('hidden');
        }
    }

    closeMobileMenu() {
        const menu = document.getElementById('mobileNavMenu');
        const backdrop = document.getElementById('mobileNavBackdrop');
        const hIcon = document.getElementById('hamburgerIcon');
        const cIcon = document.getElementById('closeMenuIcon');
        if (menu) menu.classList.add('hidden');
        if (backdrop) backdrop.classList.add('hidden');
        hIcon?.classList.remove('hidden');
        cIcon?.classList.add('hidden');
    }

    // --- Authentication Handlers ---
    async handleLogin() {
        const usernameInput = document.getElementById('loginUsername');
        const passwordInput = document.getElementById('loginPassword');
        const classeInput = document.getElementById('loginClasse');
        const studentSelect = document.getElementById('loginStudentSelect');
        const studentContainer = document.getElementById('loginStudentSelectContainer');
        const isStudentSelectVisible = studentContainer && !studentContainer.classList.contains('hidden');
        const submitBtn = document.querySelector('#loginForm button[type="submit"]');
        const errorEl = document.getElementById('loginError');

        let username = usernameInput ? usernameInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value : '';
        const classe = classeInput ? classeInput.value : '';
        const rememberMe = document.getElementById('loginRememberMe')?.checked || false;

        // If student dropdown is active, sync its value
        if (isStudentSelectVisible && studentSelect && studentSelect.value) {
            username = studentSelect.value;
            if (usernameInput) usernameInput.value = username;
        }

        if (!username || !password) {
            if (errorEl) {
                if (isStudentSelectVisible && (!studentSelect || !studentSelect.value)) {
                    errorEl.textContent = classe === 'teacher'
                        ? 'Veuillez sélectionner votre nom dans la liste des enseignants.'
                        : 'Veuillez sélectionner votre nom dans la liste des élèves.';
                } else {
                    errorEl.textContent = 'Veuillez renseigner votre identifiant et votre mot de passe.';
                }
                errorEl.classList.remove('hidden');
            }
            return;
        }

        if (errorEl) {
            errorEl.classList.add('hidden');
            errorEl.textContent = '';
        }

        const originalBtnText = submitBtn ? submitBtn.innerHTML : 'Se connecter';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">🔄</span> Connexion en cours...';
        }

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ username, password, classe, remember_me: rememberMe })
            });
            let data;
            const text = await res.text();
            try {
                data = text ? JSON.parse(text) : {};
            } catch (jsonErr) {
                throw new Error('Le serveur se réveille (démarrage du backend). Veuillez patienter quelques secondes et réessayer.');
            }
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la connexion');

            // Save token, username and class in localStorage
            try {
                if (data.session_token) {
                    localStorage.setItem('auth_token', data.session_token);
                }
                if (rememberMe) {
                    localStorage.setItem('saved_username', username);
                    if (classe) localStorage.setItem('saved_classe', classe);
                } else {
                    localStorage.removeItem('saved_username');
                    localStorage.removeItem('saved_classe');
                }
            } catch (e) {}

            if (submitBtn) {
                submitBtn.innerHTML = '✓ Connexion réussie ! Chargement...';
            }

            this.currentUser = data.user;
            this.updateUserBadge();

            // Native Android Bridge Biometric Notification
            if (window.AndroidBridge && typeof window.AndroidBridge.promptSaveBiometric === 'function') {
                try {
                    window.AndroidBridge.promptSaveBiometric(username, password, classe || '');
                    if (typeof window.AndroidBridge.onLoginSuccess === 'function') {
                        window.AndroidBridge.onLoginSuccess(username, data.session_token || '', data.user.role || '');
                    }
                } catch(e) {}
            }

            if (data.user.role === 'student') {
                window.studentTracker.init(data.user, data.session_token);
                this.switchView('student-courses');
                window.scrollTo({ top: 0, behavior: 'smooth' });
                await this.loadCourses();
            } else {
                this.switchView('teacher-dashboard');
                window.scrollTo({ top: 0, behavior: 'smooth' });
                await window.teacherDashboard.loadDashboard();
            }
        } catch (err) {
            if (errorEl) {
                errorEl.textContent = err.message;
                errorEl.classList.remove('hidden');
            }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        }
    }

    async quickLogin(username, password, classe = null) {
        const u = document.getElementById('loginUsername');
        const p = document.getElementById('loginPassword');
        const c = document.getElementById('loginClasse');
        if (u) u.value = username;
        if (p) p.value = password;
        if (c && classe) {
            c.value = classe;
            await this.onClasseChanged(classe);
            if (classe !== 'teacher') {
                const studentSelect = document.getElementById('loginStudentSelect');
                if (studentSelect) studentSelect.value = username;
            }
            if (u) u.value = username;
        }
        this.handleLogin();
    }

    async logout() {
        try {
            await this.fetchWithAuth('/api/auth/logout', { method: 'POST' });
        } catch (e) {}
        try {
            localStorage.removeItem('auth_token');
        } catch (e) {}
        window.studentTracker.stop();
        this.currentUser = null;
        if (window.AndroidBridge && typeof window.AndroidBridge.onLogout === 'function') {
            try { window.AndroidBridge.onLogout(); } catch(e) {}
        }
        this.switchView('auth');
        await this.loadPublicClasses();
    }

    // --- Change Password Handlers ---
    openChangePasswordModal() {
        const modal = document.getElementById('changePasswordModal');
        const errEl = document.getElementById('changePwdError');
        const succEl = document.getElementById('changePwdSuccess');
        if (errEl) errEl.classList.add('hidden');
        if (succEl) succEl.classList.add('hidden');
        document.getElementById('changePasswordForm')?.reset();

        modal?.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    closeChangePasswordModal() {
        document.getElementById('changePasswordModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    async handleChangePassword() {
        const old_password = document.getElementById('oldPasswordInput').value;
        const new_password = document.getElementById('newPasswordInput').value;
        const confirm_password = document.getElementById('confirmPasswordInput').value;
        const errEl = document.getElementById('changePwdError');
        const succEl = document.getElementById('changePwdSuccess');
        const submitBtn = document.getElementById('submitChangePwdBtn');

        errEl.classList.add('hidden');
        succEl.classList.add('hidden');

        if (new_password.length < 4) {
            errEl.textContent = 'Le nouveau mot de passe doit comporter au moins 4 caractères.';
            errEl.classList.remove('hidden');
            return;
        }

        if (new_password !== confirm_password) {
            errEl.textContent = 'La confirmation ne correspond pas au nouveau mot de passe.';
            errEl.classList.remove('hidden');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement...';

        try {
            const res = await this.fetchWithAuth('/api/auth/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_password, new_password, confirm_password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la modification du mot de passe');

            succEl.textContent = data.message || 'Mot de passe modifié avec succès !';
            succEl.classList.remove('hidden');
            document.getElementById('changePasswordForm')?.reset();

            setTimeout(() => {
                this.closeChangePasswordModal();
            }, 1800);
        } catch (err) {
            errEl.textContent = err.message;
            errEl.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enregistrer le mot de passe';
        }
    }

    // --- Courses Loading & Rendering ---
    async loadCourses() {
        try {
            const res = await this.fetchWithAuth('/api/courses?_t=' + Date.now());
            if (!res.ok) throw new Error('Impossible de charger les cours');
            const data = await res.json();
            this.courses = data.courses || [];
            this.availableSubjects = data.subjects || [];

            this.renderSubjectPills(this.availableSubjects);
            this.renderCourses();

            // Also update teacher course management table if needed
            if (this.currentUser?.role === 'teacher') {
                this.renderTeacherCoursesTable();
            }
        } catch (err) {
            console.error('Error loading courses:', err);
        }
    }

    renderSubjectPills(subjects) {
        const container = document.getElementById('subjectFilters');
        if (!container) return;

        const allSubjects = ['all', ...subjects];
        container.innerHTML = allSubjects.map(sub => {
            const isSelected = this.selectedSubject === sub;
            const label = sub === 'all' ? 'Toutes les matières' : sub;
            const activeClass = isSelected ? 
                'bg-blue-600 text-white font-bold shadow-sm' : 
                'bg-white text-slate-600 hover:bg-slate-100 font-medium border border-slate-200';

            return `
                <button onclick="app.filterBySubject('${sub}')" 
                        class="px-4 py-2 rounded-xl text-xs sm:text-sm transition-all ${activeClass}">
                    ${label}
                </button>
            `;
        }).join('');
    }

    filterBySubject(sub) {
        this.selectedSubject = sub;
        this.renderSubjectPills(this.availableSubjects || []);
        this.renderCourses();
    }

    renderCourses() {
        const container = document.getElementById('coursesContainer');
        if (!container) return;

        const filtered = this.courses.filter(c => {
            const matchSubject = this.selectedSubject === 'all' || c.subject === this.selectedSubject;
            const matchSearch = !this.searchQuery || 
                c.title.toLowerCase().includes(this.searchQuery) ||
                (c.chapter && c.chapter.toLowerCase().includes(this.searchQuery)) ||
                (c.description && c.description.toLowerCase().includes(this.searchQuery));

            return matchSubject && matchSearch;
        });

        const countEl = document.getElementById('coursesCount');
        if (countEl) countEl.textContent = `${filtered.length} cours disponible(s)`;

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="col-span-full py-16 text-center bg-white rounded-2xl border border-slate-200 p-8">
                    <div class="text-4xl mb-3">📚</div>
                    <h4 class="text-lg font-bold text-slate-800">Aucun cours trouvé</h4>
                    <p class="text-slate-500 text-sm mt-1">Aucun support ne correspond à vos filtres actuels.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(c => {
            let badgeClass = 'badge-default';
            if (c.subject.includes('Math')) badgeClass = 'badge-math';
            else if (c.subject.includes('Info')) badgeClass = 'badge-info';
            else if (c.subject.includes('Phys')) badgeClass = 'badge-phys';

            const authQuery = this.token ? `?auth_token=${encodeURIComponent(this.token)}` : '';
            const filesList = c.files && c.files.length > 0 ? c.files.map(f => {
                const sizeKb = Math.round((f.file_size || 0) / 1024);
                const ext = (f.file_name.split('.').pop() || 'DOC').toUpperCase();
                return `
                    <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100 hover:border-blue-200 hover:bg-blue-50/40 transition-all">
                        <div class="flex items-center gap-2.5 min-w-0 pr-2">
                            <span class="text-blue-600 text-lg">📄</span>
                            <div class="truncate">
                                <div class="text-xs font-semibold text-slate-800 truncate">${f.file_name}</div>
                                <div class="text-[11px] text-slate-400">${sizeKb} Ko • ${ext}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            <button onclick="app.openDocumentViewer(${f.id}, ${c.id}, '${f.file_name.replace(/'/g, "\\'")}')" 
                                    class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 shadow-xs transition-all flex items-center gap-1">
                                <span>👁️</span> Lire
                            </button>
                            <a href="/api/files/${f.id}/download${authQuery}" 
                               class="px-2 py-1 text-xs font-semibold rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 transition-all" 
                               title="Télécharger sur votre appareil">
                                <span>⬇️</span>
                            </a>
                        </div>
                    </div>
                `;
            }).join('') : `
                <div class="text-xs text-slate-400 italic py-1">Aucun fichier attaché à ce cours.</div>
            `;

            return `
                <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col justify-between">
                    <div class="p-5">
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide ${badgeClass}">
                                ${c.subject}
                            </span>
                            <div class="flex items-center gap-1.5 flex-wrap justify-end">
                                <span class="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md flex items-center gap-1">
                                    <span>${c.author_name && c.author_name.toLowerCase().includes('jamila') ? '👩‍🏫' : '👨‍🏫'}</span>
                                    <span>${c.author_name || 'Professeur'}</span>
                                </span>
                                <span class="text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-md">
                                    ${c.classe}
                                </span>
                            </div>
                        </div>

                        ${c.chapter ? `<div class="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">${c.chapter}</div>` : ''}
                        <h3 class="text-base font-bold text-slate-900 leading-snug mb-2">${c.title}</h3>
                        <p class="text-xs text-slate-600 leading-relaxed line-clamp-3 mb-4">${c.description || ''}</p>

                        ${c.content_html ? `
                            <div class="p-3 rounded-xl bg-slate-50/70 border border-slate-100 text-xs text-slate-700 mb-4 prose-sm max-h-32 overflow-y-auto">
                                ${c.content_html}
                            </div>
                        ` : ''}
                    </div>

                    <div class="p-4 bg-slate-50/50 border-t border-slate-100 space-y-2">
                        <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                            <span>📎</span> Documents & Fiches du cours :
                        </div>
                        <div class="space-y-1.5">
                            ${filesList}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // --- In-Browser Document Viewer with Active Reading Timer ---
    openDocumentViewer(fileId, courseId, fileName) {
        this.activeReadingFile = { fileId, courseId, fileName };
        const modal = document.getElementById('documentViewerModal');
        const titleEl = document.getElementById('viewerFileName');
        const frameEl = document.getElementById('documentViewerFrame');
        const downloadLink = document.getElementById('viewerDownloadBtn');

        if (!modal) return;

        titleEl.textContent = fileName;
        const authParam = this.token ? `?auth_token=${encodeURIComponent(this.token)}` : '';
        frameEl.src = `/api/files/${fileId}/view${authParam}`;
        downloadLink.href = `/api/files/${fileId}/download${authParam}`;

        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');

        // Start document reading timer tracking
        window.studentTracker.startFileReading(fileId, courseId, fileName);
    }

    closeDocumentViewer() {
        const modal = document.getElementById('documentViewerModal');
        const frameEl = document.getElementById('documentViewerFrame');
        if (modal) modal.classList.add('hidden');
        if (frameEl) frameEl.src = 'about:blank';
        document.body.classList.remove('overflow-hidden');

        // Stop document timer
        window.studentTracker.stopFileReading();
        this.activeReadingFile = null;
    }

    // --- Teacher Course Management Handlers ---
    renderTeacherCoursesTable() {
        const tbody = document.getElementById('teacherCoursesTableBody');
        if (!tbody) return;

        if (this.courses.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="6" class="px-6 py-6 text-center text-slate-500">Aucun cours publié.</td></tr>
            `;
            return;
        }

        const isAdmin = this.currentUser?.is_admin;
        const currentUserId = this.currentUser?.id;

        tbody.innerHTML = this.courses.map(c => {
            const filesCount = c.files ? c.files.length : 0;
            const canManage = isAdmin || (c.author_id === currentUserId);
            const authorName = c.author_name || 'Prof. Msalbi';
            const icon = authorName.toLowerCase().includes('jamila') ? '👩‍🏫' : '👨‍🏫';

            return `
                <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100">
                    <td class="px-6 py-4">
                        <div class="font-bold text-slate-800 text-sm">${c.title}</div>
                        <div class="text-xs text-blue-600">${c.chapter || 'Sans chapitre'}</div>
                    </td>
                    <td class="px-6 py-4">
                        <span class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700">
                            <span>${icon}</span>
                            <span>${authorName}</span>
                        </span>
                    </td>
                    <td class="px-6 py-4">
                        <span class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-50 text-blue-700 border border-blue-200">${c.subject}</span>
                    </td>
                    <td class="px-6 py-4 text-xs font-medium text-slate-600">${c.classe}</td>
                    <td class="px-6 py-4 text-xs font-bold text-slate-700">${filesCount} document(s)</td>
                    <td class="px-6 py-4 text-right space-x-2">
                        ${canManage ? `
                            <button onclick="app.openEditCourseModal(${c.id})" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200 transition-all">
                                ✏️ Modifier
                            </button>
                            <button onclick="app.deleteCourse(${c.id})" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 transition-all">
                                🗑️ Supprimer
                            </button>
                        ` : `
                            <span class="text-xs text-slate-400 italic">Lecture seule</span>
                        `}
                    </td>
                </tr>
            `;
        }).join('');
    }

    openEditCourseModal(courseId) {
        const c = this.courses.find(item => item.id === courseId);
        if (!c) {
            alert('Cours introuvable');
            return;
        }

        document.getElementById('editCourseId').value = c.id;
        document.getElementById('editCourseTitle').value = c.title || '';
        document.getElementById('editCourseSubject').value = c.subject || 'Informatique';
        document.getElementById('editCourseChapter').value = c.chapter || '';
        document.getElementById('editCourseDescription').value = c.description || '';

        // Populate editCourseClasse
        const select = document.getElementById('editCourseClasse');
        if (select) {
            const isAdmin = this.currentUser?.is_admin;
            let html = '';
            if (isAdmin) {
                const classes = this.cachedPublicClasses || [];
                html = '<option value="Toutes les classes">Toutes les classes</option>';
                classes.forEach(cls => {
                    html += `<option value="${cls.name}">${cls.name}</option>`;
                });
            } else {
                const assigned = this.currentUser?.assigned_classes || [];
                assigned.forEach(cname => {
                    html += `<option value="${cname}">${cname}</option>`;
                });
            }
            select.innerHTML = html;
            if (c.classe && Array.from(select.options).some(o => o.value === c.classe)) {
                select.value = c.classe;
            } else if (select.options.length > 0) {
                select.value = select.options[0].value;
            }
        }

        document.getElementById('editCourseModal')?.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    closeEditCourseModal() {
        document.getElementById('editCourseModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        document.getElementById('editCourseForm')?.reset();
    }

    async handleUpdateCourse() {
        const form = document.getElementById('editCourseForm');
        const courseId = document.getElementById('editCourseId').value;
        if (!courseId) return;

        const formData = new FormData(form);
        const submitBtn = document.getElementById('submitEditCourseBtn');

        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement en cours...';

        try {
            const res = await this.fetchWithAuth(`/api/courses/${courseId}`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la modification du cours');

            alert(data.message || 'Cours mis à jour avec succès !');
            this.closeEditCourseModal();
            await this.loadCourses();
        } catch (err) {
            alert('Erreur : ' + err.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enregistrer les modifications';
        }
    }

    openNewCourseModal() {
        this.populateNewCourseClasses();
        document.getElementById('newCourseModal')?.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    closeNewCourseModal() {
        document.getElementById('newCourseModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    async handleCreateCourse() {
        const form = document.getElementById('newCourseForm');
        const formData = new FormData(form);
        const submitBtn = document.getElementById('submitCourseBtn');

        submitBtn.disabled = true;
        submitBtn.textContent = 'Publication en cours...';

        try {
            const res = await this.fetchWithAuth('/api/courses', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la création du cours');

            alert(data.message || 'Cours créé avec succès !');
            form.reset();
            this.closeNewCourseModal();
            await this.loadCourses();
        } catch (err) {
            alert('Erreur : ' + err.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Publier le cours';
        }
    }

    async deleteCourse(courseId) {
        if (!confirm('Êtes-vous certain de vouloir supprimer ce cours et tous ses fichiers attachés ?')) return;

        try {
            const res = await this.fetchWithAuth(`/api/courses/${courseId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la suppression');
            alert(data.message || 'Cours supprimé');
            await this.loadCourses();
        } catch (err) {
            alert('Erreur : ' + err.message);
        }
    }

    // --- Excel Import Handlers ---
    openExcelImportModal() {
        document.getElementById('importExcelModal')?.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    closeExcelImportModal() {
        document.getElementById('importExcelModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    async handleExcelImport() {
        const form = document.getElementById('importExcelForm');
        const formData = new FormData(form);
        const submitBtn = document.getElementById('submitImportExcelBtn');

        submitBtn.disabled = true;
        submitBtn.textContent = 'Importation en cours...';

        try {
            const res = await fetch('/api/teacher/students/import-excel', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de l\'importation');

            alert(data.message || 'Élèves importés avec succès !');
            form.reset();
            this.closeExcelImportModal();
            await window.teacherDashboard.loadDashboard();
            await this.loadPublicClasses();
        } catch (err) {
            alert('Erreur : ' + err.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Lancer l\'importation';
        }
    }

    // --- Teacher Add Student Handlers ---
    openNewStudentModal() {
        document.getElementById('newStudentModal')?.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    closeNewStudentModal() {
        document.getElementById('newStudentModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    async handleCreateStudent() {
        const full_name = document.getElementById('newStudentFullName').value.trim();
        const username = document.getElementById('newStudentUsername').value.trim();
        const email = document.getElementById('newStudentEmail').value.trim();
        const classe = document.getElementById('newStudentClasse').value;
        const password = document.getElementById('newStudentPassword').value.trim() || 'eleve123';

        try {
            const res = await fetch('/api/teacher/students', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name, username, email, classe, password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de l\'ajout de l\'élève');

            alert(data.message || 'Élève inscrit avec succès !');
            document.getElementById('newStudentForm').reset();
            this.closeNewStudentModal();
            await window.teacherDashboard.loadStudentsList();
            await window.teacherDashboard.loadClasses();
            await this.loadPublicClasses();
        } catch (err) {
            alert('Erreur : ' + err.message);
        }
    }

    // --- Classes Management Handlers ---
    openNewClassModal() {
        const modal = document.getElementById('newClassModal');
        const err = document.getElementById('newClassError');
        if (err) err.classList.add('hidden');
        if (modal) modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    closeNewClassModal() {
        const modal = document.getElementById('newClassModal');
        if (modal) modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    async handleCreateClass() {
        const nameInput = document.getElementById('newClassName');
        const levelInput = document.getElementById('newClassLevel');
        const descInput = document.getElementById('newClassDescription');
        const submitBtn = document.getElementById('submitCreateClassBtn');
        const errorEl = document.getElementById('newClassError');

        const name = nameInput.value.trim();
        const level = levelInput.value.trim();
        const description = descInput.value.trim();

        if (!name) {
            if (errorEl) {
                errorEl.textContent = 'Le nom de la classe est obligatoire.';
                errorEl.classList.remove('hidden');
            }
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Création en cours...';

        try {
            const res = await this.fetchWithAuth('/api/teacher/classes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, level, description })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de la création de la classe');

            alert(data.message || `Classe "${name}" créée avec succès !`);
            document.getElementById('newClassForm').reset();
            this.closeNewClassModal();
            await window.teacherDashboard.loadClasses();
            await this.loadPublicClasses();
        } catch (err) {
            if (errorEl) {
                errorEl.textContent = err.message;
                errorEl.classList.remove('hidden');
            } else {
                alert('Erreur : ' + err.message);
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Créer la classe';
        }
    }

    openNewStudentModalForClass(className) {
        this.openNewStudentModal();
        const classSelect = document.getElementById('newStudentClasse');
        if (classSelect) {
            let exists = Array.from(classSelect.options).some(o => o.value === className);
            if (!exists) {
                const opt = document.createElement('option');
                opt.value = className;
                opt.textContent = className;
                classSelect.appendChild(opt);
            }
            classSelect.value = className;
        }
    }

    openExcelImportModalForClass(className) {
        this.openExcelImportModal();
        const classInput = document.getElementById('importExcelClasse');
        if (classInput) classInput.value = className;
    }

    // ==========================================
    // --- Messagerie & Échange de Messages ---
    // ==========================================
    async checkUnreadMessages() {
        if (!this.currentUser) return;
        try {
            const res = await this.fetchWithAuth('/api/messages/unread-count');
            if (!res.ok) return;
            const data = await res.json();
            const badge = document.getElementById('unreadMessagesBadge');
            if (badge) {
                const count = data.unread_count || 0;
                if (count > 0) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.classList.remove('hidden');

                    // Notification native Android lors de nouveaux messages
                    if (this.lastReportedUnreadCount !== undefined && count > this.lastReportedUnreadCount) {
                        if (window.AndroidBridge && typeof window.AndroidBridge.showNotification === 'function') {
                            window.AndroidBridge.showNotification(
                                "Nouveau message 💬",
                                `Vous avez ${count} message${count > 1 ? 's' : ''} non lu${count > 1 ? 's' : ''} sur l'Espace Msalbi.`,
                                1001
                            );
                        }
                    }
                } else {
                    badge.classList.add('hidden');
                }
                this.lastReportedUnreadCount = count;
            }
        } catch (e) {
            console.warn('Erreur vérification messages non lus:', e);
        }
    }

    async openMessagingModal() {
        const modal = document.getElementById('messagingModal');
        if (modal) modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');

        // Réinitialise la vue sur mobile pour afficher d'abord la liste
        const sidebar = document.getElementById('chatSidebarContainer');
        const chatArea = document.getElementById('chatAreaContainer');
        if (window.innerWidth < 768) {
            if (sidebar) {
                sidebar.classList.remove('hidden');
                sidebar.classList.add('flex');
            }
            if (chatArea) {
                chatArea.classList.add('hidden');
                chatArea.classList.remove('flex');
            }
        }

        // Bouton diffuser pour le professeur uniquement
        const broadcastBtn = document.getElementById('broadcastNewBtn');
        if (broadcastBtn) {
            if (this.currentUser?.role === 'teacher') {
                broadcastBtn.classList.remove('hidden');
            } else {
                broadcastBtn.classList.add('hidden');
            }
        }

        // Initialisation de la capture de collage (Ctrl+V d'une capture d'écran / image)
        if (!this.chatPasteInitialized) {
            this.chatPasteInitialized = true;
            const input = document.getElementById('chatInputText');
            if (input) {
                input.addEventListener('paste', (e) => {
                    const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
                    if (!items) return;
                    for (const item of items) {
                        if (item.kind === 'file') {
                            const file = item.getAsFile();
                            if (file) {
                                this.setChatAttachment(file);
                                break;
                            }
                        }
                    }
                });
            }
        }

        await this.loadConversations();

        // Rafraîchissement automatique de la messagerie toutes les 5 secondes uniquement si l'onglet est actif
        if (this.messagingPollInterval) clearInterval(this.messagingPollInterval);
        this.messagingPollInterval = setInterval(async () => {
            if (document.hidden) return;
            if (this.activeConversation) {
                await this.refreshActiveThread(true);
            }
            await this.loadConversations(true);
        }, 5000);
    }

    closeMessagingModal() {
        const modal = document.getElementById('messagingModal');
        if (modal) modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        if (this.messagingPollInterval) {
            clearInterval(this.messagingPollInterval);
            this.messagingPollInterval = null;
        }
        this.removeChatAttachment();
        this.checkUnreadMessages();
    }

    async loadConversations(isBackground = false) {
        try {
            const res = await this.fetchWithAuth('/api/messages/conversations');
            if (!res.ok) return;
            const data = await res.json();
            this.cachedConversations = data;

            this.renderConversationsList();

            // Sur grand écran, sélectionne automatiquement la première conversation si aucune n'est active
            if (!this.activeConversation && !isBackground && window.innerWidth >= 768) {
                if (data.channels && data.channels.length > 0) {
                    const c = data.channels[0];
                    this.selectConversation('class_broadcast', c.target_class, c.name, "Messages de l'enseignant pour la classe", c.teacher_id);
                } else if (data.direct_chats && data.direct_chats.length > 0) {
                    const d = data.direct_chats[0];
                    this.selectConversation('direct', d.with_user_id, d.name, `Classe : ${d.classe}`);
                }
            }
        } catch (e) {
            console.warn('Erreur chargement conversations:', e);
        }
    }

    renderConversationsList(filterQuery = '') {
        const channelsContainer = document.getElementById('msgChannelsList');
        const directContainer = document.getElementById('msgDirectList');
        if (!channelsContainer || !directContainer) return;

        const q = filterQuery.toLowerCase().trim();
        const channels = (this.cachedConversations?.channels || []).filter(c => !q || c.name.toLowerCase().includes(q) || (c.last_message || '').toLowerCase().includes(q));
        const directChats = (this.cachedConversations?.direct_chats || []).filter(d => !q || d.name.toLowerCase().includes(q) || (d.last_message || '').toLowerCase().includes(q));

        // Rendu des canaux de diffusion
        let htmlChannels = '';
        if (channels.length === 0) {
            htmlChannels = '<p class="text-[11px] text-slate-400 p-2 italic">Aucun canal</p>';
        } else {
            channels.forEach(c => {
                const isActive = this.activeConversation?.type === 'class_broadcast' 
                    && this.activeConversation?.target_class === c.target_class
                    && (!c.teacher_id || this.activeConversation?.teacher_id === c.teacher_id);
                htmlChannels += `
                    <button onclick="app.selectConversation('class_broadcast', '${c.target_class}', '${c.name.replace(/'/g, "\\'")}', 'Diffusion collective de classe', ${c.teacher_id || 'null'})" 
                            class="w-full text-left p-2.5 rounded-2xl transition-all flex items-center justify-between gap-2.5 ${isActive ? 'bg-blue-600 text-white shadow-sm' : 'hover:bg-slate-200/60 text-slate-800'}">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <div class="w-8 h-8 rounded-xl ${isActive ? 'bg-white/20 text-white' : 'bg-blue-100 text-blue-700'} flex items-center justify-center text-sm shrink-0 font-bold">
                                📢
                            </div>
                            <div class="min-w-0 flex-1">
                                <div class="text-xs font-bold truncate">${c.name}</div>
                                <div class="text-[11px] truncate ${isActive ? 'text-blue-100' : 'text-slate-500'}">${c.last_message || 'Aucun message'}</div>
                            </div>
                        </div>
                        ${c.unread > 0 ? `<span class="px-1.5 py-0.5 rounded-full text-[10px] font-black ${isActive ? 'bg-white text-blue-700' : 'bg-red-500 text-white'} shrink-0">${c.unread}</span>` : ''}
                    </button>
                `;
            });
        }
        channelsContainer.innerHTML = htmlChannels;

        // Rendu des discussions privées
        let htmlDirect = '';
        if (directChats.length === 0) {
            htmlDirect = '<p class="text-[11px] text-slate-400 p-2 italic">Aucune discussion privée récente. Cliquez sur ➕ pour en démarrer une.</p>';
        } else {
            directChats.forEach(d => {
                const isActive = this.activeConversation?.type === 'direct' && this.activeConversation?.with_user_id === d.with_user_id;
                htmlDirect += `
                    <button onclick="app.selectConversation('direct', ${d.with_user_id}, '${d.name.replace(/'/g, "\\'")}', 'Classe : ${d.classe || 'Général'}')" 
                            class="w-full text-left p-2.5 rounded-2xl transition-all flex items-center justify-between gap-2.5 ${isActive ? 'bg-blue-600 text-white shadow-sm' : 'hover:bg-slate-200/60 text-slate-800'}">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <div class="w-8 h-8 rounded-xl ${isActive ? 'bg-white/20 text-white' : (d.is_teacher ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700')} flex items-center justify-center text-xs shrink-0 font-bold">
                                ${d.is_teacher ? '👨‍🏫' : '👤'}
                            </div>
                            <div class="min-w-0 flex-1">
                                <div class="text-xs font-bold truncate flex items-center gap-1.5">
                                    <span>${d.name}</span>
                                    <span class="text-[9px] px-1.5 py-0.2 rounded-md ${isActive ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'}">${d.badge}</span>
                                </div>
                                <div class="text-[11px] truncate ${isActive ? 'text-blue-100' : 'text-slate-500'}">${d.last_message || 'Démarrer discussion'}</div>
                            </div>
                        </div>
                        ${d.unread > 0 ? `<span class="px-1.5 py-0.5 rounded-full text-[10px] font-black ${isActive ? 'bg-white text-blue-700' : 'bg-red-500 text-white'} shrink-0">${d.unread}</span>` : ''}
                    </button>
                `;
            });
        }
        directContainer.innerHTML = htmlDirect;
    }

    filterConversations(query) {
        this.renderConversationsList(query);
    }

    backToConversationsList() {
        const sidebar = document.getElementById('chatSidebarContainer');
        const chatArea = document.getElementById('chatAreaContainer');
        if (sidebar) {
            sidebar.classList.remove('hidden');
            sidebar.classList.add('flex');
        }
        if (chatArea) {
            chatArea.classList.add('hidden');
            chatArea.classList.remove('flex');
        }
    }

    async selectConversation(type, target, title, subtitle, teacherId = null) {
        this.removeChatAttachment();
        this.activeConversation = { type, target, title, subtitle };
        if (type === 'class_broadcast') {
            this.activeConversation.target_class = target;
            this.activeConversation.teacher_id = teacherId;
        } else {
            this.activeConversation.with_user_id = target;
        }

        // Bascule responsive pour mobile
        const sidebar = document.getElementById('chatSidebarContainer');
        const chatArea = document.getElementById('chatAreaContainer');

        if (chatArea) {
            chatArea.classList.remove('hidden');
            chatArea.classList.add('flex');
        }
        if (sidebar && window.innerWidth < 768) {
            sidebar.classList.add('hidden');
            sidebar.classList.remove('flex');
        }

        // Met à jour l'en-tête de la zone de chat
        const titleEl = document.getElementById('chatActiveTitle');
        const subtitleEl = document.getElementById('chatActiveSubtitle');
        const avatarEl = document.getElementById('chatActiveAvatar');
        const badgeEl = document.getElementById('chatActiveBadge');

        if (titleEl) titleEl.textContent = title;
        if (subtitleEl) subtitleEl.textContent = subtitle;
        if (avatarEl) avatarEl.textContent = type === 'class_broadcast' ? '📢' : '💬';
        if (badgeEl) badgeEl.textContent = type === 'class_broadcast' ? 'Diffusion de classe' : 'Message Privé';

        // Pour les élèves dans un canal de diffusion : masquer la saisie et afficher la bannière explicative
        const isStudentBroadcast = type === 'class_broadcast' && this.currentUser?.role === 'student';
        const composerForm = document.getElementById('chatComposerForm');
        const broadcastBanner = document.getElementById('chatBroadcastReadOnlyBanner');

        if (isStudentBroadcast) {
            if (composerForm) composerForm.classList.add('hidden');
            if (broadcastBanner) broadcastBanner.classList.remove('hidden');
        } else {
            if (composerForm) composerForm.classList.remove('hidden');
            if (broadcastBanner) broadcastBanner.classList.add('hidden');
        }

        // Rafraîchit la sélection active dans la barre latérale
        this.renderConversationsList();

        // Charge les messages du fil
        await this.refreshActiveThread(false);

        // Focalise la zone de saisie si accessible
        if (!isStudentBroadcast) {
            setTimeout(() => {
                document.getElementById('chatInputText')?.focus();
            }, 100);
        }
    }

    openTeacherPrivateChat() {
        let teacherId = this.activeConversation?.teacher_id;
        let teacherName = 'Professeur';

        if (this.cachedConversations?.available_contacts) {
            const teachers = this.cachedConversations.available_contacts.filter(c => c.role === 'teacher');
            if (teacherId) {
                const found = teachers.find(t => t.id === teacherId);
                if (found) teacherName = found.full_name;
            } else if (teachers.length > 0) {
                teacherId = teachers[0].id;
                teacherName = teachers[0].full_name;
            }
        }

        if (teacherId) {
            this.selectConversation('direct', teacherId, teacherName, 'Professeur');
        } else {
            this.openNewChatPickerModal();
        }
    }

    handleChatFileSelected(event) {
        const file = event.target.files?.[0];
        if (file) {
            this.setChatAttachment(file);
        }
    }

    setChatAttachment(file) {
        if (!file) return;

        // Limite de taille max 50 Mo (conforme au serveur)
        const maxBytes = 50 * 1024 * 1024;
        if (file.size > maxBytes) {
            alert("Le fichier sélectionné dépasse la taille maximale autorisée (50 Mo).");
            const input = document.getElementById('chatFileInput');
            if (input) input.value = '';
            return;
        }

        this.chatAttachment = file;

        const previewContainer = document.getElementById('chatAttachmentPreview');
        const nameEl = document.getElementById('chatAttachmentName');
        const sizeEl = document.getElementById('chatAttachmentSize');
        const iconEl = document.getElementById('chatAttachmentIcon');

        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = this.formatFileSize(file.size);
        if (iconEl) iconEl.textContent = this.getFileIcon(file.name);
        if (previewContainer) previewContainer.classList.remove('hidden');

        document.getElementById('chatInputText')?.focus();
    }

    removeChatAttachment() {
        this.chatAttachment = null;
        const input = document.getElementById('chatFileInput');
        if (input) input.value = '';
        const previewContainer = document.getElementById('chatAttachmentPreview');
        if (previewContainer) previewContainer.classList.add('hidden');
    }

    formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '0 Ko';
        if (bytes < 1024 * 1024) {
            return Math.round(bytes / 1024) + ' Ko';
        }
        return (bytes / (1024 * 1024)).toFixed(1) + ' Mo';
    }

    getFileIcon(filename) {
        if (!filename) return '📎';
        const ext = (filename.split('.').pop() || '').toLowerCase();
        if (['pdf'].includes(ext)) return '📕';
        if (['doc', 'docx'].includes(ext)) return '📘';
        if (['xls', 'xlsx', 'csv'].includes(ext)) return '📊';
        if (['ppt', 'pptx'].includes(ext)) return '📙';
        if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return '🖼️';
        if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return '🗂️';
        if (['mp3', 'wav', 'ogg', 'm4a'].includes(ext)) return '🎵';
        if (['mp4', 'mov', 'webm'].includes(ext)) return '🎬';
        if (['py', 'js', 'html', 'css', 'sql', 'json'].includes(ext)) return '💻';
        return '📄';
    }

    isImageFile(filename) {
        if (!filename) return false;
        const ext = (filename.split('.').pop() || '').toLowerCase();
        return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext);
    }

    openMessageFileViewer(messageId, fileName) {
        const modal = document.getElementById('documentViewerModal');
        const titleEl = document.getElementById('viewerFileName');
        const frameEl = document.getElementById('documentViewerFrame');
        const downloadLink = document.getElementById('viewerDownloadBtn');

        if (!modal) return;

        titleEl.textContent = fileName || 'Pièce jointe';
        const token = localStorage.getItem('auth_token');
        const authParam = token ? `?auth_token=${encodeURIComponent(token)}` : '';
        if (frameEl) frameEl.src = `/api/messages/files/${messageId}/view${authParam}`;
        if (downloadLink) downloadLink.href = `/api/messages/files/${messageId}/download${authParam}`;

        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    renderMessageAttachmentHtml(m, isMine, authParam) {
        if (!m.file_name && !m.file_path) return '';

        const fileName = this.escapeHtml(m.file_name || 'Pièce jointe');
        const isImg = this.isImageFile(m.file_name);
        const icon = this.getFileIcon(m.file_name);
        const sizeFormatted = this.formatFileSize(m.file_size);
        const safeRawName = (m.file_name || '').replace(/'/g, "\\'");

        if (isImg) {
            return `
                <div class="mt-2 mb-1">
                    <a href="/api/messages/files/${m.id}/view${authParam}" target="_blank" onclick="event.preventDefault(); app.openMessageFileViewer(${m.id}, '${safeRawName}')" 
                       class="block group relative overflow-hidden rounded-xl border ${isMine ? 'border-blue-400/50' : 'border-slate-200'} bg-black/5" title="Agrandir l'image">
                        <img src="/api/messages/files/${m.id}/view${authParam}" alt="${fileName}" 
                             loading="lazy"
                             class="max-h-56 w-auto max-w-full rounded-xl object-contain group-hover:scale-[1.02] transition-transform duration-200" 
                             onerror="this.onerror=null; this.parentElement.innerHTML='<span class=\\'p-3 text-xs block text-slate-400\\'>🖼️ Image indisponible</span>';">
                    </a>
                    <div class="flex items-center justify-between text-[10px] mt-1 px-1 ${isMine ? 'text-blue-200' : 'text-slate-500'}">
                        <span class="truncate max-w-[180px]">${fileName}</span>
                        <span class="font-mono">${sizeFormatted}</span>
                    </div>
                </div>
            `;
        }

        return `
            <div class="mt-2 p-2 sm:p-2.5 rounded-xl ${isMine ? 'bg-blue-700/60 border border-blue-400/40 text-white' : 'bg-slate-50 border border-slate-200 text-slate-800'} flex items-center justify-between gap-2.5 shadow-xs">
                <div class="flex items-center gap-2 min-w-0">
                    <span class="text-xl shrink-0">${icon}</span>
                    <div class="min-w-0">
                        <div class="text-xs font-bold truncate max-w-[150px] sm:max-w-[210px]" title="${fileName}">
                            ${fileName}
                        </div>
                        <div class="text-[10px] ${isMine ? 'text-blue-200' : 'text-slate-400'} font-mono">
                            ${sizeFormatted}
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-1 shrink-0">
                    <button type="button" onclick="app.openMessageFileViewer(${m.id}, '${safeRawName}')" 
                            class="p-1.5 rounded-lg ${isMine ? 'bg-white/20 hover:bg-white/30 text-white' : 'bg-blue-100 hover:bg-blue-200 text-blue-800'} text-xs font-bold transition-colors" 
                            title="Visualiser">
                        👁️
                    </button>
                    <a href="/api/messages/files/${m.id}/download${authParam}" 
                       class="p-1.5 rounded-lg ${isMine ? 'bg-white/20 hover:bg-white/30 text-white' : 'bg-slate-200 hover:bg-slate-300 text-slate-700'} text-xs font-bold transition-colors" 
                       title="Télécharger sur votre appareil">
                        ⬇️
                    </a>
                </div>
            </div>
        `;
    }

    async refreshActiveThread(isBackground = false) {
        if (!this.activeConversation) return;
        const scrollContainer = document.getElementById('chatMessagesScroll');
        const emptyEl = document.getElementById('chatEmptyPlaceholder');
        if (!scrollContainer) return;

        try {
            let url = '';
            if (this.activeConversation.type === 'class_broadcast') {
                url = `/api/messages/thread?type=class_broadcast&target_class=${encodeURIComponent(this.activeConversation.target_class)}`;
                if (this.activeConversation.teacher_id) {
                    url += `&teacher_id=${encodeURIComponent(this.activeConversation.teacher_id)}`;
                }
            } else {
                url = `/api/messages/thread?type=direct&with_user_id=${encodeURIComponent(this.activeConversation.with_user_id)}`;
            }

            const res = await this.fetchWithAuth(url);
            if (!res.ok) return;
            const data = await res.json();
            const messages = data.messages || [];

            if (emptyEl) {
                if (messages.length === 0) {
                    emptyEl.classList.remove('hidden');
                } else {
                    emptyEl.classList.add('hidden');
                }
            }

            const isAtBottom = scrollContainer.scrollHeight - scrollContainer.scrollTop - scrollContainer.clientHeight < 80;
            const token = localStorage.getItem('auth_token');
            const authParam = token ? `?auth_token=${encodeURIComponent(token)}` : '';

            let html = '';
            messages.forEach(m => {
                const isMine = m.is_mine;
                const canDelete = m.can_delete || m.is_mine || this.currentUser?.is_admin || this.currentUser?.role === 'teacher';
                const timeStr = m.created_at ? m.created_at.replace('T', ' ').slice(11, 16) : '';
                const attachmentHtml = this.renderMessageAttachmentHtml(m, isMine, authParam);
                const hasContent = m.content && m.content.trim().length > 0;

                if (isMine) {
                    html += `
                        <div class="flex flex-col items-end group mb-2">
                            <div class="max-w-[88%] sm:max-w-md bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-xs px-4 py-2.5 shadow-sm relative">
                                <div class="flex items-start justify-between gap-3">
                                    <div class="flex-1 min-w-0">
                                        ${hasContent ? `<div class="text-xs sm:text-sm whitespace-pre-wrap leading-relaxed">${this.escapeHtml(m.content)}</div>` : ''}
                                        ${attachmentHtml}
                                    </div>
                                    <button type="button" onclick="event.stopPropagation(); app.deleteMessage(${m.id})" 
                                            class="shrink-0 p-1 -mr-1 -mt-1 rounded-lg text-white/70 hover:text-white hover:bg-red-500/40 transition-colors cursor-pointer" 
                                            title="Supprimer ce message">
                                        <span class="text-xs">🗑️</span>
                                    </button>
                                </div>
                                <div class="flex items-center justify-between gap-3 mt-2 pt-1.5 border-t border-white/20 text-[10px] text-blue-200 font-mono">
                                    <button type="button" onclick="event.stopPropagation(); app.deleteMessage(${m.id})" 
                                            class="px-2 py-0.5 rounded-lg bg-red-500/30 hover:bg-red-500 text-white font-medium flex items-center gap-1 transition-all cursor-pointer shadow-xs border border-white/20" 
                                            title="Supprimer ce message">
                                        <span>🗑️</span> <span>Supprimer</span>
                                    </button>
                                    <span class="text-blue-100 font-mono text-[10px] ml-auto">${timeStr} ✓</span>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    const isBroadcast = m.message_type === 'class_broadcast';
                    const isTeacher = m.sender_role === 'teacher';
                    html += `
                        <div class="flex flex-col items-start group mb-2">
                            <div class="text-[11px] font-bold text-slate-600 ml-1 mb-0.5 flex items-center gap-1.5">
                                <span>${m.sender_name}</span>
                                <span class="text-[9px] px-1.5 py-0.2 rounded-md ${isTeacher ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'}">${isTeacher ? '👨‍🏫 Professeur' : '🎓 Élève'}</span>
                                ${isBroadcast ? '<span class="text-[9px] px-1.5 py-0.2 rounded-md bg-indigo-100 text-indigo-700 font-bold">📢 Annonce</span>' : ''}
                            </div>
                            <div class="max-w-[88%] sm:max-w-md bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-xs px-4 py-2.5 shadow-xs relative">
                                <div class="flex items-start justify-between gap-3">
                                    <div class="flex-1 min-w-0">
                                        ${hasContent ? `<div class="text-xs sm:text-sm whitespace-pre-wrap leading-relaxed">${this.escapeHtml(m.content)}</div>` : ''}
                                        ${attachmentHtml}
                                    </div>
                                    ${canDelete ? `
                                        <button type="button" onclick="event.stopPropagation(); app.deleteMessage(${m.id})" 
                                                class="shrink-0 p-1 -mr-1 -mt-1 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer" 
                                                title="Supprimer ce message">
                                            <span class="text-xs">🗑️</span>
                                        </button>
                                    ` : ''}
                                </div>
                                <div class="flex items-center justify-between gap-3 mt-2 pt-1.5 border-t border-slate-100 text-[10px] text-slate-400 font-mono">
                                    ${canDelete ? `
                                        <button type="button" onclick="event.stopPropagation(); app.deleteMessage(${m.id})" 
                                                class="px-2 py-0.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 font-medium flex items-center gap-1 transition-all cursor-pointer border border-red-200 shadow-xs" 
                                                title="Supprimer ce message">
                                            <span>🗑️</span> <span>Supprimer</span>
                                        </button>
                                    ` : '<span></span>'}
                                    <span class="text-slate-400 font-mono text-[10px] ml-auto">${timeStr}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }
            });

            const existingMessagesContainer = document.getElementById('chatMessagesContent');
            if (existingMessagesContainer) {
                existingMessagesContainer.innerHTML = html;
            } else {
                const div = document.createElement('div');
                div.id = 'chatMessagesContent';
                div.className = 'space-y-3';
                div.innerHTML = html;
                scrollContainer.appendChild(div);
            }

            if (!isBackground || isAtBottom) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }

            // Met à jour le badge de non-lus
            this.checkUnreadMessages();
        } catch (e) {
            console.warn('Erreur rafraîchissement fil:', e);
        }
    }

    async handleSendMessage() {
        if (!this.activeConversation) return;
        const input = document.getElementById('chatInputText');
        const sendBtn = document.getElementById('chatSendBtn');
        const content = input?.value.trim() || '';
        const attachment = this.chatAttachment;

        if (!content && !attachment) return;

        const formData = new FormData();
        formData.append('target_type', this.activeConversation.type);
        formData.append('content', content);

        if (this.activeConversation.type === 'class_broadcast') {
            formData.append('target_class', this.activeConversation.target_class);
        } else {
            formData.append('receiver_id', this.activeConversation.with_user_id);
        }

        if (attachment) {
            formData.append('file', attachment);
        }

        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = `<span>Envoi...</span> <span class="animate-spin">⏳</span>`;
        }

        try {
            const res = await this.fetchWithAuth('/api/messages/send', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Impossible d'envoyer le message");

            input.value = '';
            input.style.height = 'auto';
            this.removeChatAttachment();

            await this.refreshActiveThread(false);
            await this.loadConversations(true);
        } catch (err) {
            alert('Erreur envoi message : ' + err.message);
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.innerHTML = `<span>Envoyer</span> <span>➤</span>`;
            }
            input?.focus();
        }
    }

    async deleteMessage(messageId) {
        if (!messageId) return;
        if (!confirm("Voulez-vous vraiment supprimer ce message ? Cette action est irréversible.")) {
            return;
        }

        try {
            const res = await this.fetchWithAuth(`/api/messages/${messageId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Impossible de supprimer le message");

            // Rafraîchir immédiatement le fil et les conversations
            await this.refreshActiveThread(false);
            await this.loadConversations(true);
        } catch (err) {
            alert("Erreur lors de la suppression : " + err.message);
        }
    }

    // --- Modal Sélection Contact / Nouvelle Discussion ---
    async openNewChatPickerModal() {
        const modal = document.getElementById('newChatPickerModal');
        if (modal) modal.classList.remove('hidden');

        try {
            const res = await this.fetchWithAuth('/api/messages/contacts');
            if (!res.ok) return;
            const data = await res.json();
            this.cachedContacts = data.contacts || [];
            this.renderContactsPickerList();
        } catch (e) {
            console.warn('Erreur chargement contacts:', e);
        }
    }

    closeNewChatPickerModal() {
        document.getElementById('newChatPickerModal')?.classList.add('hidden');
    }

    renderContactsPickerList(filter = '') {
        const list = document.getElementById('contactsPickerList');
        if (!list) return;

        const q = filter.toLowerCase().trim();
        const contacts = this.cachedContacts.filter(c => !q || c.full_name.toLowerCase().includes(q) || (c.classe || '').toLowerCase().includes(q));

        if (contacts.length === 0) {
            list.innerHTML = '<p class="text-xs text-slate-400 p-3 text-center">Aucun contact trouvé.</p>';
            return;
        }

        let html = '';
        contacts.forEach(c => {
            const isTeacher = c.role === 'teacher';
            html += `
                <button onclick="app.startChatWithContact(${c.id}, '${c.full_name.replace(/'/g, "\\'")}', '${c.classe || 'Général'}')" 
                        class="w-full text-left p-2.5 rounded-xl hover:bg-slate-100 flex items-center justify-between gap-3 transition-colors">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <div class="w-8 h-8 rounded-xl ${isTeacher ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'} font-bold flex items-center justify-center text-xs shrink-0">
                            ${isTeacher ? '👨‍🏫' : '👤'}
                        </div>
                        <div class="min-w-0 flex-1">
                            <div class="text-xs font-bold text-slate-800 truncate">${c.full_name}</div>
                            <div class="text-[11px] text-slate-500">${isTeacher ? 'Professeur' : 'Classe : ' + (c.classe || 'Général')}</div>
                        </div>
                    </div>
                    <span class="text-xs text-blue-600 font-bold shrink-0">Discuter ➔</span>
                </button>
            `;
        });
        list.innerHTML = html;
    }

    filterContactsPicker(q) {
        this.renderContactsPickerList(q);
    }

    startChatWithContact(userId, userName, userClasse) {
        this.closeNewChatPickerModal();
        this.selectConversation('direct', userId, userName, `Classe : ${userClasse}`);
    }

    openBroadcastModal() {
        const channels = this.cachedConversations?.channels || [];
        if (channels.length === 0) {
            alert("Aucune classe disponible pour la diffusion.");
            return;
        }
        if (channels.length === 1) {
            const c = channels[0];
            this.selectConversation('class_broadcast', c.target_class, c.name, "Diffuser une annonce à la classe", c.teacher_id);
            setTimeout(() => {
                document.getElementById('chatInputText')?.focus();
            }, 150);
            return;
        }

        // Si l'enseignant a plusieurs classes, ouvrir la fenêtre de choix
        const modal = document.getElementById('broadcastClassPickerModal');
        const list = document.getElementById('broadcastClassPickerList');
        if (!modal || !list) return;

        list.innerHTML = channels.map(c => `
            <button type="button" onclick="app.selectBroadcastClass('${c.target_class}', '${c.name.replace(/'/g, "\\'")}', ${c.teacher_id || 'null'})" class="w-full text-left p-3.5 rounded-2xl border border-slate-200 hover:bg-indigo-50 hover:border-indigo-200 transition-all flex items-center justify-between group">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">📢</div>
                    <div>
                        <div class="text-xs font-bold text-slate-800 group-hover:text-indigo-800">${c.name}</div>
                        <div class="text-[10px] text-slate-400">Diffusion pour toute la classe ${c.target_class}</div>
                    </div>
                </div>
                <span class="text-xs text-indigo-600 font-bold">Choisir ➔</span>
            </button>
        `).join('');

        modal.classList.remove('hidden');
    }

    selectBroadcastClass(targetClass, name, teacherId) {
        this.closeBroadcastPickerModal();
        this.selectConversation('class_broadcast', targetClass, name, "Diffuser une annonce à la classe", teacherId);
        setTimeout(() => {
            document.getElementById('chatInputText')?.focus();
        }, 150);
    }

    closeBroadcastPickerModal() {
        document.getElementById('broadcastClassPickerModal')?.classList.add('hidden');
    }

    // --- Admin: Teacher Management & Class Scoping ---
    async openAdminTeachersModal() {
        const modal = document.getElementById('adminTeachersModal');
        const container = document.getElementById('adminTeachersListContainer');
        if (!modal) return;
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');

        // Réinitialise le formulaire d'ajout
        this.toggleAddTeacherForm(false);

        if (container) container.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs">Chargement des enseignants...</div>';

        try {
            const res = await this.fetchWithAuth('/api/admin/teachers');
            if (!res.ok) throw new Error('Impossible de charger la liste des enseignants');
            const data = await res.json();
            const teachers = data.teachers || [];
            const allClasses = data.all_classes || [];

            // Remplit le conteneur des classes pour le formulaire d'ajout
            const newClassesContainer = document.getElementById('newTeacherClassesContainer');
            if (newClassesContainer) {
                newClassesContainer.innerHTML = allClasses.map(cname => `
                    <label class="flex items-center gap-2 p-2 rounded-xl border border-slate-200 bg-white hover:bg-purple-50 cursor-pointer text-xs font-semibold text-slate-700 transition-all select-none">
                        <input type="checkbox" name="new_teacher_classes" value="${cname}" class="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-slate-300">
                        <span>${cname}</span>
                    </label>
                `).join('');
            }

            if (teachers.length === 0) {
                container.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs">Aucun enseignant trouvé.</div>';
                return;
            }

            let html = '';
            teachers.forEach(t => {
                const isAdmin = t.is_admin === 1 || t.username === 'msalbi';
                const assigned = t.assigned_classes || [];
                const icon = (t.username || '').toLowerCase().includes('jamila') ? '👩‍🏫' : '👨‍🏫';

                html += `
                    <div class="p-5 rounded-2xl border border-slate-200 bg-white shadow-xs space-y-3">
                        <div class="flex items-center justify-between gap-3 flex-wrap">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl ${isAdmin ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'} flex items-center justify-center text-lg font-bold">
                                    ${icon}
                                </div>
                                <div>
                                    <div class="text-sm font-bold text-slate-800 flex items-center gap-2">
                                        <span>${this.escapeHtml(t.full_name)}</span>
                                        <span class="text-[10px] px-2 py-0.5 rounded-full font-bold ${isAdmin ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}">
                                            ${isAdmin ? '👑 Administrateur & Professeur' : '👨‍🏫 Professeur'}
                                        </span>
                                    </div>
                                    <div class="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                                        <span>Identifiant : <span class="font-mono text-slate-600 font-semibold">${this.escapeHtml(t.username)}</span></span>
                                        ${t.classe ? `<span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-medium">${this.escapeHtml(t.classe)}</span>` : ''}
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" onclick="app.promptResetTeacherPassword(${t.id}, '${t.full_name.replace(/'/g, "\\'")}')" class="px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold text-xs transition-all flex items-center gap-1" title="Modifier le mot de passe">
                                    <span>🔑</span> Mot de passe
                                </button>
                                ${!isAdmin ? `
                                    <button type="button" onclick="app.deleteTeacher(${t.id}, '${t.full_name.replace(/'/g, "\\'")}')" class="px-3 py-1.5 rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 text-red-700 font-bold text-xs transition-all flex items-center gap-1" title="Supprimer cet enseignant">
                                        <span>🗑️</span> Supprimer
                                    </button>
                                    <button onclick="app.saveTeacherAssignments(${t.id})" id="btnSaveTeacher_${t.id}" class="px-3.5 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs shadow-xs transition-all flex items-center gap-1.5">
                                        <span>💾</span> Enregistrer
                                    </button>
                                ` : ''}
                            </div>
                        </div>

                        ${isAdmin ? `
                            <div class="p-3 rounded-xl bg-purple-50 text-purple-900 text-xs font-medium border border-purple-100 flex items-center gap-2">
                                <span>🌐</span> En tant qu'administrateur principal, le Professeur Msalbi a accès à l'ensemble des classes, cours et messages de la plateforme.
                            </div>
                        ` : `
                            <div class="pt-2 border-t border-slate-100">
                                <div class="text-xs font-bold text-slate-600 mb-2">Classes attribuées à cet enseignant (délimite ses cours et sa messagerie) :</div>
                                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                    ${allClasses.map(cname => {
                                        const isChecked = assigned.includes(cname);
                                        return `
                                            <label class="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer text-xs font-semibold text-slate-700 transition-all select-none">
                                                <input type="checkbox" name="teacher_class_${t.id}" value="${cname}" ${isChecked ? 'checked' : ''} class="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-slate-300">
                                                <span>${cname}</span>
                                            </label>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        `}
                    </div>
                `;
            });

            container.innerHTML = html;
        } catch (err) {
            console.error('Error loading teachers:', err);
            container.innerHTML = `<div class="text-center py-8 text-red-500 text-xs">${err.message}</div>`;
        }
    }

    closeAdminTeachersModal() {
        document.getElementById('adminTeachersModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    toggleAddTeacherForm(show = null) {
        const formContainer = document.getElementById('adminAddTeacherFormContainer');
        if (!formContainer) return;
        const willShow = show === null ? formContainer.classList.contains('hidden') : show;
        if (willShow) {
            formContainer.classList.remove('hidden');
            const fnInput = document.getElementById('newTeacherFullName');
            const unInput = document.getElementById('newTeacherUsername');
            const pwInput = document.getElementById('newTeacherPassword');
            const sbInput = document.getElementById('newTeacherSubject');
            if (fnInput) fnInput.value = '';
            if (unInput) unInput.value = '';
            if (pwInput) pwInput.value = '';
            if (sbInput) sbInput.value = '';
            document.querySelectorAll('input[name="new_teacher_classes"]').forEach(cb => cb.checked = false);
            setTimeout(() => fnInput?.focus(), 100);
        } else {
            formContainer.classList.add('hidden');
        }
    }

    async handleCreateTeacher() {
        const fullName = document.getElementById('newTeacherFullName')?.value.trim();
        const username = document.getElementById('newTeacherUsername')?.value.trim().toLowerCase();
        const password = document.getElementById('newTeacherPassword')?.value.trim();
        const subject = document.getElementById('newTeacherSubject')?.value.trim();
        const checkboxes = document.querySelectorAll('input[name="new_teacher_classes"]:checked');
        const selectedClasses = Array.from(checkboxes).map(cb => cb.value);
        const submitBtn = document.getElementById('btnSubmitNewTeacher');

        if (!fullName || !username || !password) {
            alert("Veuillez renseigner le nom complet, l'identifiant et le mot de passe.");
            return;
        }

        if (password.length < 4) {
            alert("Le mot de passe doit comporter au moins 4 caractères.");
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Enregistrement en cours...';
        }

        try {
            const res = await this.fetchWithAuth('/api/admin/teachers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: fullName,
                    username: username,
                    password: password,
                    subject: subject,
                    classes: selectedClasses
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Erreur lors de la création de l'enseignant");

            alert(data.message || "Enseignant créé avec succès !");
            this.toggleAddTeacherForm(false);
            await this.openAdminTeachersModal();
        } catch (err) {
            alert(err.message);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span>✓</span> Enregistrer l\'enseignant';
            }
        }
    }

    async promptResetTeacherPassword(teacherId, teacherName) {
        const newPassword = prompt(`Définir un nouveau mot de passe pour ${teacherName} (minimum 4 caractères) :`);
        if (newPassword === null) return;
        if (newPassword.trim().length < 4) {
            alert("Le mot de passe doit comporter au moins 4 caractères.");
            return;
        }

        try {
            const res = await this.fetchWithAuth(`/api/admin/teachers/${teacherId}/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_password: newPassword.trim() })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Erreur lors de la modification du mot de passe");
            alert(data.message || `Le mot de passe de ${teacherName} a été mis à jour avec succès !`);
        } catch (err) {
            alert(err.message);
        }
    }

    async deleteTeacher(teacherId, teacherName) {
        if (!confirm(`Êtes-vous sûr de vouloir supprimer l'enseignant(e) "${teacherName}" ? Cette action est irréversible.`)) {
            return;
        }

        try {
            const res = await this.fetchWithAuth(`/api/admin/teachers/${teacherId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Erreur lors de la suppression de l'enseignant");
            alert(data.message || "Enseignant supprimé avec succès !");
            await this.openAdminTeachersModal();
        } catch (err) {
            alert(err.message);
        }
    }

    async saveTeacherAssignments(teacherId) {
        const checkboxes = document.querySelectorAll(`input[name="teacher_class_${teacherId}"]:checked`);
        const selectedClasses = Array.from(checkboxes).map(cb => cb.value);
        const saveBtn = document.getElementById(`btnSaveTeacher_${teacherId}`);

        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Enregistrement...';
        }

        try {
            const res = await this.fetchWithAuth(`/api/admin/teacher-assignments/${teacherId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ classes: selectedClasses })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erreur lors de l\'enregistrement');
            alert(data.message || 'Affectations enregistrées avec succès !');
            await this.openAdminTeachersModal();
        } catch (err) {
            alert(err.message);
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<span>💾</span> Enregistrer';
            }
        }
    }

    escapeHtml(str) {
        return (str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
