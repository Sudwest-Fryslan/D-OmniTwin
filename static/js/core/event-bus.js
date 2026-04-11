/**
 * Simple Event Bus for decoupled communication between components.
 */
class EventBus {
    constructor() {
        this.listeners = {};
    }

    /**
     * Subscribe to an event.
     * @param {string} eventName 
     * @param {function} callback 
     */
    on(eventName, callback) {
        if (!this.listeners[eventName]) {
            this.listeners[eventName] = [];
        }
        this.listeners[eventName].push(callback);
    }

    /**
     * Unsubscribe from an event.
     * @param {string} eventName 
     * @param {function} callback 
     */
    off(eventName, callback) {
        if (!this.listeners[eventName]) return;
        this.listeners[eventName] = this.listeners[eventName].filter(cb => cb !== callback);
    }

    /**
     * Publish an event.
     * @param {string} eventName 
     * @param {any} data 
     */
    emit(eventName, data) {
        if (!this.listeners[eventName]) return;
        this.listeners[eventName].forEach(callback => callback(data));
    }
}

// Global instance
window.EventBus = new EventBus();

// Feature Toggle Default
window.USE_EVENT_BUS = true;

console.log('🚌 EventBus initialized (window.USE_EVENT_BUS = ' + window.USE_EVENT_BUS + ')');
