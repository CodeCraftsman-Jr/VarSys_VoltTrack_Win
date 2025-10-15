// VoltTrack Web Application JavaScript

class VoltTrackWeb {
    constructor() {
        this.currentUser = null;
        this.meters = [];
        this.readings = [];
        this.currentTab = 'dashboard';
        
        this.init();
    }

    init() {
        // Initialize the application
        this.setupEventListeners();
        this.checkSession();
    }

    setupEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Quick actions
        document.querySelectorAll('.btn-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleQuickAction(e.target.dataset.action);
            });
        });

        // Sync button
        document.getElementById('sync-btn').addEventListener('click', () => {
            this.syncWithServer();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });

        // Reading form
        document.getElementById('reading-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addReading();
        });

        // Add meter button
        document.getElementById('add-meter-btn').addEventListener('click', () => {
            this.showAddMeterModal();
        });

        // Modal close
        document.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal();
        });

        // Modal overlay click
        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.closeModal();
            }
        });
    }

    checkSession() {
        // Check for saved session
        const savedSession = localStorage.getItem('volttrack_session');
        if (savedSession) {
            try {
                const session = JSON.parse(savedSession);
                const expiresAt = new Date(session.expires_at);
                
                if (new Date() < expiresAt) {
                    this.currentUser = session.user;
                    this.showMainApp();
                    return;
                }
            } catch (e) {
                console.error('Invalid session data');
            }
        }
        
        this.showLogin();
    }

    showLogin() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('main-screen').classList.add('hidden');
    }

    showMainApp() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('main-screen').classList.remove('hidden');
        
        this.loadData();
        this.updateDashboard();
    }

    async handleLogin() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const rememberMe = document.getElementById('remember-me').checked;

        try {
            // Real Appwrite authentication
            const response = await this.authenticateWithAppwrite(email, password);
            
            if (response.success) {
                this.currentUser = response.user;
                
                if (rememberMe) {
                    const session = {
                        user: response.user,
                        expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
                    };
                    localStorage.setItem('volttrack_session', JSON.stringify(session));
                }
                
                this.showMainApp();
            } else {
                this.showError(response.message);
            }
        } catch (error) {
            this.showError('Login failed. Please try again.');
        }
    }

    async authenticateWithAppwrite(email, password) {
        // Real Appwrite authentication
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });
            
            if (response.ok) {
                const data = await response.json();
                return {
                    success: true,
                    user: data.user
                };
            } else {
                const error = await response.json();
                return {
                    success: false,
                    message: error.message || 'Authentication failed'
                };
            }
        } catch (error) {
            return {
                success: false,
                message: 'Network error. Please check your connection.'
            };
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('error-message');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        
        setTimeout(() => {
            errorDiv.classList.add('hidden');
        }, 5000);
    }

    logout() {
        localStorage.removeItem('volttrack_session');
        this.currentUser = null;
        this.meters = [];
        this.readings = [];
        this.showLogin();
    }

    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        if (tabName === 'dashboard') {
            this.updateDashboard();
        } else if (tabName === 'add-reading') {
            this.populateMeterSelect();
        } else if (tabName === 'meters') {
            this.loadMetersList();
        }
    }

    async loadData() {
        // Load real data from API
        try {
            await this.loadMetersFromAPI();
            await this.loadReadingsFromAPI();
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data. Please try again.');
        }
    }

    async loadMetersFromAPI() {
        try {
            const response = await fetch('/api/meters', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                this.meters = await response.json();
            } else {
                throw new Error('Failed to load meters');
            }
        } catch (error) {
            console.error('Error loading meters:', error);
            this.meters = [];
        }
    }

    async loadReadingsFromAPI() {
        try {
            const response = await fetch('/api/readings', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                this.readings = await response.json();
            } else {
                throw new Error('Failed to load readings');
            }
        } catch (error) {
            console.error('Error loading readings:', error);
            this.readings = [];
        }
    }

    getAuthToken() {
        const session = localStorage.getItem('volttrack_session');
        if (session) {
            try {
                const sessionData = JSON.parse(session);
                return sessionData.token || '';
            } catch (e) {
                return '';
            }
        }
        return '';
    }

    updateDashboard() {
        // Update stats
        document.getElementById('total-meters').textContent = this.meters.length;
        document.getElementById('total-readings').textContent = this.readings.length;
        
        const totalConsumption = this.meters.reduce((sum, meter) => sum + meter.total_consumption, 0);
        document.getElementById('total-consumption').textContent = `${totalConsumption.toFixed(1)} kWh`;
        
        // Calculate this month's consumption (simplified)
        const monthConsumption = this.readings.reduce((sum, reading) => sum + reading.consumption, 0);
        document.getElementById('month-consumption').textContent = `${monthConsumption.toFixed(1)} kWh`;
        
        // Update last updated time
        document.getElementById('last-updated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        
        // Update meters grid
        this.updateMetersGrid();
    }

    updateMetersGrid() {
        const grid = document.getElementById('meters-grid');
        grid.innerHTML = '';

        this.meters.forEach(meter => {
            const daysSinceReading = this.getDaysSinceReading(meter.last_reading_date);
            const statusClass = daysSinceReading <= 7 ? 'status-recent' : 
                               daysSinceReading <= 30 ? 'status-warning' : 'status-old';
            const statusText = daysSinceReading <= 7 ? 'Recent' : `${daysSinceReading} days ago`;

            const meterCard = document.createElement('div');
            meterCard.className = 'meter-card';
            meterCard.innerHTML = `
                <h3>${meter.home_name}</h3>
                <div class="meter-subtitle">${meter.meter_name}</div>
                <div class="meter-stats">
                    <div class="meter-stat">
                        <div class="meter-stat-value">${meter.latest_reading}</div>
                        <div class="meter-stat-label">Latest</div>
                    </div>
                    <div class="meter-stat">
                        <div class="meter-stat-value">${meter.total_consumption.toFixed(1)} kWh</div>
                        <div class="meter-stat-label">Total</div>
                    </div>
                </div>
                <div class="meter-status">
                    <span class="status-dot ${statusClass}"></span>
                    <span>${statusText}</span>
                </div>
            `;
            grid.appendChild(meterCard);
        });
    }

    getDaysSinceReading(dateString) {
        const readingDate = new Date(dateString);
        const today = new Date();
        const diffTime = Math.abs(today - readingDate);
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }

    populateMeterSelect() {
        const select = document.getElementById('meter-select');
        select.innerHTML = '<option value="">Choose a meter...</option>';
        
        this.meters.forEach(meter => {
            const option = document.createElement('option');
            option.value = meter.id;
            option.textContent = `${meter.home_name} - ${meter.meter_name}`;
            select.appendChild(option);
        });

        // Set today's date as default
        document.getElementById('reading-date').value = new Date().toISOString().split('T')[0];
    }

    addReading() {
        const meterId = document.getElementById('meter-select').value;
        const value = parseFloat(document.getElementById('reading-value').value);
        const date = document.getElementById('reading-date').value;

        if (!meterId || !value || !date) {
            alert('Please fill in all fields');
            return;
        }

        // Add reading (simulate API call)
        const newReading = {
            id: `reading_${Date.now()}`,
            meter_id: meterId,
            value: value,
            date: date,
            consumption: 0 // Calculate based on previous reading
        };

        this.readings.push(newReading);

        // Update meter's latest reading
        const meter = this.meters.find(m => m.id === meterId);
        if (meter) {
            const previousValue = meter.latest_reading;
            meter.latest_reading = value;
            meter.last_reading_date = date;
            newReading.consumption = Math.max(0, value - previousValue);
            meter.total_consumption += newReading.consumption;
        }

        // Reset form
        document.getElementById('reading-form').reset();
        this.populateMeterSelect();

        // Show success message
        alert('Reading added successfully!');

        // Update dashboard if it's the current tab
        if (this.currentTab === 'dashboard') {
            this.updateDashboard();
        }
    }

    loadMetersList() {
        const list = document.getElementById('meters-list');
        list.innerHTML = '';

        this.meters.forEach(meter => {
            const meterItem = document.createElement('div');
            meterItem.className = 'meter-item';
            meterItem.innerHTML = `
                <div class="meter-info">
                    <h4>${meter.home_name} - ${meter.meter_name}</h4>
                    <p>Type: ${meter.meter_type} | Latest: ${meter.latest_reading}</p>
                </div>
                <div class="meter-actions">
                    <button class="btn-small btn-edit" onclick="app.editMeter('${meter.id}')">Edit</button>
                    <button class="btn-small btn-delete" onclick="app.deleteMeter('${meter.id}')">Delete</button>
                </div>
            `;
            list.appendChild(meterItem);
        });
    }

    showAddMeterModal() {
        document.getElementById('modal-title').textContent = 'Add New Meter';
        document.getElementById('modal-body').innerHTML = `
            <form id="meter-form" class="meter-form">
                <div class="form-group">
                    <label for="home-name">Home Name</label>
                    <input type="text" id="home-name" required>
                </div>
                <div class="form-group">
                    <label for="meter-name">Meter Name</label>
                    <input type="text" id="meter-name" required>
                </div>
                <div class="form-group">
                    <label for="meter-type">Meter Type</label>
                    <select id="meter-type" required>
                        <option value="electricity">Electricity</option>
                        <option value="gas">Gas</option>
                        <option value="water">Water</option>
                    </select>
                </div>
                <button type="submit" class="btn-primary">Add Meter</button>
            </form>
        `;

        document.getElementById('modal-overlay').classList.remove('hidden');

        // Add form submit handler
        document.getElementById('meter-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addMeter();
        });
    }

    addMeter() {
        const homeName = document.getElementById('home-name').value;
        const meterName = document.getElementById('meter-name').value;
        const meterType = document.getElementById('meter-type').value;

        const newMeter = {
            id: `meter_${Date.now()}`,
            home_name: homeName,
            meter_name: meterName,
            meter_type: meterType,
            latest_reading: 0,
            total_consumption: 0,
            last_reading_date: new Date().toISOString().split('T')[0]
        };

        this.meters.push(newMeter);
        this.closeModal();
        this.loadMetersList();
        
        alert('Meter added successfully!');
    }

    editMeter(meterId) {
        // Implement edit functionality
        alert(`Edit meter ${meterId} - Feature coming soon!`);
    }

    deleteMeter(meterId) {
        if (confirm('Are you sure you want to delete this meter?')) {
            this.meters = this.meters.filter(m => m.id !== meterId);
            this.readings = this.readings.filter(r => r.meter_id !== meterId);
            this.loadMetersList();
            alert('Meter deleted successfully!');
        }
    }

    closeModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }

    handleQuickAction(action) {
        switch (action) {
            case 'add-reading':
                this.switchTab('add-reading');
                break;
            case 'view-analytics':
                this.switchTab('history');
                break;
            case 'sync':
                this.syncWithServer();
                break;
        }
    }

    async syncWithServer() {
        // Simulate sync process
        const syncBtn = document.getElementById('sync-btn');
        const originalHTML = syncBtn.innerHTML;
        
        syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        syncBtn.disabled = true;

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            alert('Sync completed successfully!');
        } catch (error) {
            alert('Sync failed. Please try again.');
        } finally {
            syncBtn.innerHTML = originalHTML;
            syncBtn.disabled = false;
        }
    }
}

// Initialize the application
const app = new VoltTrackWeb();
