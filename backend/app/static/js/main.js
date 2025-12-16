// Main JavaScript for OptimaPricer

// Error logging utility (only logs in development)
(function() {
    const isDevelopment = window.location.hostname === 'localhost' || 
                         window.location.hostname === '127.0.0.1' ||
                         window.location.hostname.includes('localhost');
    
    window.logError = function(message, error) {
        if (isDevelopment) {
            console.error(message, error);
        }
        // In production, errors are handled silently with user-friendly UI messages
    };
})();

// API helper function
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };
    
    const response = await fetch(`/api${endpoint}`, { ...defaultOptions, ...options });
    
    if (!response.ok && response.status === 401) {
        window.location.href = '/auth/signin';
        return null;
    }
    
    return response;
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatPercent(value) {
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
}

// Custom Modal Functions
function showCustomModal(title, message, type = 'confirm', onConfirm = null, onCancel = null, autoDismiss = false) {
    const modal = document.getElementById('customModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalIcon = document.getElementById('modalIcon');
    const modalActions = document.getElementById('modalActions');
    
    // Set title and message
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    
    // Set icon based on type
    let iconHTML = '';
    if (type === 'confirm') {
        iconHTML = `
            <div class="p-2 bg-blue-100 rounded-lg">
                <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            </div>
        `;
    } else if (type === 'success') {
        iconHTML = `
            <div class="p-2 bg-emerald-100 rounded-lg">
                <svg class="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            </div>
        `;
    } else if (type === 'error') {
        iconHTML = `
            <div class="p-2 bg-red-100 rounded-lg">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            </div>
        `;
    } else if (type === 'warning') {
        iconHTML = `
            <div class="p-2 bg-amber-100 rounded-lg">
                <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
            </div>
        `;
    }
    modalIcon.innerHTML = iconHTML;
    
    // Set buttons based on type and autoDismiss
    let buttonsHTML = '';
    if (type === 'confirm') {
        buttonsHTML = `
            <button onclick="if (window._modalCancel) { window._modalCancel(); } closeCustomModal();" 
                class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors">
                Cancel
            </button>
            <button onclick="if (window._modalConfirm) { window._modalConfirm(); } closeCustomModal();" 
                class="px-4 py-2 text-sm font-medium text-white bg-emerald-900 rounded-lg hover:bg-emerald-800 transition-colors">
                Confirm
            </button>
        `;
    } else if (autoDismiss) {
        // Hide buttons for auto-dismiss alerts
        buttonsHTML = '';
    } else {
        buttonsHTML = `
            <button onclick="if (window._modalConfirm) { window._modalConfirm(); } closeCustomModal();" 
                class="px-4 py-2 text-sm font-medium text-white bg-emerald-900 rounded-lg hover:bg-emerald-800 transition-colors">
                OK
            </button>
        `;
    }
    modalActions.innerHTML = buttonsHTML;
    
    // Store callbacks
    window._modalConfirm = onConfirm;
    window._modalCancel = onCancel;
    
    // Show modal
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeCustomModal(cancelled = false) {
    const modal = document.getElementById('customModal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';
    
    // If cancelled and we have a cancel callback, call it
    if (cancelled && window._modalCancel) {
        window._modalCancel();
    }
    
    window._modalConfirm = null;
    window._modalCancel = null;
}

// Custom confirm function
function customConfirm(message, title = 'Confirm') {
    return new Promise((resolve) => {
        showCustomModal(title, message, 'confirm', () => resolve(true), () => resolve(false));
    });
}

// Custom alert function
function customAlert(message, title = 'Alert', type = 'info', autoDismiss = false, dismissDelay = 2000) {
    return new Promise((resolve) => {
        showCustomModal(title, message, type, () => resolve(), null, autoDismiss);
        
        // Auto-dismiss if requested
        if (autoDismiss) {
            setTimeout(() => {
                closeCustomModal();
                resolve();
            }, dismissDelay);
        }
    });
}
