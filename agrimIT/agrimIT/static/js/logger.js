/**
 * AgrimIT Frontend Logger
 * Replaces console.log with structured logging to backend
 */

// Get CSRF token for Django
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    // Fallback: try to get from meta tag
    const meta = document.querySelector('meta[name=csrf-token]');
    return meta ? meta.getAttribute('content') : '';
}

// Log levels
const LogLevel = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error',
    DEBUG: 'debug'
};

/**
 * Send log to Django backend
 */
function logToBackend(level, message, context = {}) {
    // Only log important events in production
    if (level === LogLevel.DEBUG && window.location.hostname !== 'localhost') {
        return;
    }

    const logData = {
        level: level,
        message: message,
        context: context,
        url: window.location.href,
        timestamp: new Date().toISOString()
    };

    fetch('/api/log-error/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(logData)
    }).catch(error => {
        // Silent fail - don't create infinite loops
        console.error('Failed to log to backend:', error);
    });
}

/**
 * Replacement functions for console.log
 */
window.Logger = {
    info: function(message, context = {}) {
        logToBackend(LogLevel.INFO, message, context);
    },
    
    warning: function(message, context = {}) {
        logToBackend(LogLevel.WARNING, message, context);
    },
    
    error: function(message, context = {}) {
        logToBackend(LogLevel.ERROR, message, context);
    },
    
    debug: function(message, context = {}) {
        logToBackend(LogLevel.DEBUG, message, context);
    },

    // User action logging
    userAction: function(action, details = {}) {
        logToBackend(LogLevel.INFO, `User action: ${action}`, {
            action: action,
            ...details
        });
    },

    // Form validation logging
    formValidation: function(formName, isValid, errors = {}) {
        const level = isValid ? LogLevel.INFO : LogLevel.WARNING;
        logToBackend(level, `Form validation: ${formName}`, {
            form: formName,
            valid: isValid,
            errors: errors
        });
    },

    // File upload logging
    fileUpload: function(fileName, fileSize, success = true, error = null) {
        const level = success ? LogLevel.INFO : LogLevel.ERROR;
        logToBackend(level, `File upload: ${fileName}`, {
            fileName: fileName,
            fileSize: fileSize,
            success: success,
            error: error
        });
    }
};

// Global error handler
window.addEventListener('error', function(e) {
    Logger.error('Uncaught JavaScript error', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno,
        stack: e.error ? e.error.stack : 'No stack trace'
    });
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(e) {
    Logger.error('Unhandled promise rejection', {
        reason: e.reason,
        promise: e.promise
    });
});