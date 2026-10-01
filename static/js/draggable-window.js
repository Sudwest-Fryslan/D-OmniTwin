/**
 * DraggableWindow - Floating, draggable, resizable window component
 * 
 * Used for the D-Omni Kompas visualization
 * Vanilla JavaScript implementation (no dependencies)
 */

class DraggableWindow {
    constructor(windowId) {
        this.window = document.getElementById(windowId);
        if (!this.window) {
            console.error(`❌ Window element not found: ${windowId}`);
            return;
        }

        this.header = this.window.querySelector('.floating-window-header');
        this.content = this.window.querySelector('.floating-window-content');
        this.resizer = this.window.querySelector('.resize-handle');
        this.btnMinimize = this.window.querySelector('.btn-minimize');
        this.btnClose = this.window.querySelector('.btn-close');

        // State
        this.isDragging = false;
        this.isResizing = false;
        this.isMinimized = false;
        this.isVisible = false;
        this.dragOffset = { x: 0, y: 0 };

        // Storage key for position persistence
        this.storageKey = `window-position-${windowId}`;

        // Initialize
        this.initDrag();
        this.initResize();
        this.initControls();
        this.restorePosition();

        if (!this.header || !this.content) {
            console.error('❌ Missing header or content in DraggableWindow');
        }

        console.log(`✅ DraggableWindow initialized: ${windowId}`);
    }

    // =========================================================================
    // Drag Functionality
    // =========================================================================

    initDrag() {
        if (!this.header) return;

        this.header.addEventListener('mousedown', this.dragStart.bind(this));
        document.addEventListener('mousemove', this.drag.bind(this));
        document.addEventListener('mouseup', this.dragEnd.bind(this));

        // Touch support
        this.header.addEventListener('touchstart', this.dragStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.drag.bind(this), { passive: false });
        document.addEventListener('touchend', this.dragEnd.bind(this));
    }

    dragStart(e) {
        // Ignore clicks on buttons
        if (e.target.closest('.window-controls')) return;

        this.isDragging = true;
        this.window.style.transition = 'none';

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        const rect = this.window.getBoundingClientRect();

        this.dragOffset.x = clientX - rect.left;
        this.dragOffset.y = clientY - rect.top;

        e.preventDefault();
    }

    drag(e) {
        if (!this.isDragging) return;

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;

        let newX = clientX - this.dragOffset.x;
        let newY = clientY - this.dragOffset.y;

        // Keep within viewport
        const rect = this.window.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width;
        const maxY = window.innerHeight - rect.height;

        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));

        this.window.style.left = `${newX}px`;
        this.window.style.top = `${newY}px`;

        e.preventDefault();
    }

    dragEnd() {
        if (this.isDragging) {
            this.isDragging = false;
            this.window.style.transition = '';
            this.savePosition();
        }
    }

    // =========================================================================
    // Resize Functionality
    // =========================================================================

    initResize() {
        if (!this.resizer) return;

        this.resizer.addEventListener('mousedown', this.resizeStart.bind(this));
        document.addEventListener('mousemove', this.resize.bind(this));
        document.addEventListener('mouseup', this.resizeEnd.bind(this));
    }

    resizeStart(e) {
        this.isResizing = true;
        this.window.style.transition = 'none';
        this.window.classList.add('manually-resized');
        e.preventDefault();
        e.stopPropagation();
    }

    resize(e) {
        if (!this.isResizing) return;

        const rect = this.window.getBoundingClientRect();

        let newWidth = e.clientX - rect.left;
        let newHeight = e.clientY - rect.top;

        // Enforce min/max sizes
        newWidth = Math.max(400, Math.min(newWidth, window.innerWidth * 0.9));
        newHeight = Math.max(450, Math.min(newHeight, window.innerHeight * 0.9));

        this.window.style.width = `${newWidth}px`;
        this.window.style.height = `${newHeight}px`;
    }

    resizeEnd() {
        if (this.isResizing) {
            this.isResizing = false;
            this.window.style.transition = '';
            this.savePosition();

            // Trigger resize event for SVG/D3 to recalculate
            window.dispatchEvent(new Event('resize'));
        }
    }

    // =========================================================================
    // Window Controls
    // =========================================================================

    initControls() {
        if (this.btnMinimize) {
            this.btnMinimize.addEventListener('click', () => this.toggleMinimize());
        }
        if (this.btnClose) {
            this.btnClose.addEventListener('click', () => this.close());
        }
    }

    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.window.classList.toggle('minimized', this.isMinimized);

        if (this.btnMinimize) {
            this.btnMinimize.textContent = this.isMinimized ? '□' : '_';
        }
    }

    centerWindow() {
        const rect = this.window.getBoundingClientRect();
        // Fallback dimensions if not yet rendered
        const width = rect.width || 650;
        const height = rect.height || 800;

        const x = Math.max(20, (window.innerWidth - width) / 2);
        const y = Math.max(20, (window.innerHeight - height) / 2);

        this.window.style.left = `${x}px`;
        this.window.style.top = `${y}px`;

        console.log(`📍 Centered window at ${x}, ${y} (size: ${width}x${height})`);
        this.savePosition();
    }

    // =========================================================================
    // Position Persistence
    // =========================================================================

    savePosition() {
        const rect = this.window.getBoundingClientRect();
        const position = {
            left: this.window.style.left,
            top: this.window.style.top,
            width: this.window.style.width,
            height: this.window.style.height
        };
        localStorage.setItem(this.storageKey, JSON.stringify(position));
    }

    restorePosition() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const pos = JSON.parse(saved);

                // Validate and clamp restored position to ensure it's on screen
                const winWidth = window.innerWidth;
                const winHeight = window.innerHeight;

                // Parse values safely
                let left = parseInt(pos.left) || 20;
                let top = parseInt(pos.top) || 100;
                let width = parseInt(pos.width) || 650;
                let height = parseInt(pos.height) || 800;

                // Safety checks: Ensure at least partial visibility
                if (left > winWidth - 100) left = winWidth - width - 20;
                if (top > winHeight - 100) top = winHeight - height - 20;
                if (left < 0) left = 20;
                if (top < 0) top = 20;

                this.window.style.left = `${left}px`;
                this.window.style.top = `${top}px`;
                this.window.style.width = `${width}px`;
                this.window.style.height = `${height}px`;

                console.log('📍 Window position restored and validated');
            } else {
                this.centerWindow();
            }
        } catch (e) {
            console.warn('Could not restore window position:', e);
            this.centerWindow();
        }
    }

    // =========================================================================
    // Public API
    // =========================================================================

    isOpen() {
        return this.window.style.display !== 'none';
    }

    open() {
        this.window.style.display = 'flex';
        this.window.classList.add('opening');
        this.window.classList.remove('closing');
        this.isVisible = true;

        // Force a position check on open
        const rect = this.window.getBoundingClientRect();
        if (rect.left > window.innerWidth || rect.top > window.innerHeight || rect.left < -rect.width + 50) {
            console.warn('⚠️ Window was off-screen, centering...');
            this.centerWindow();
        }

        setTimeout(() => {
            this.window.classList.remove('opening');
        }, 250);

        // Niet-modale dialoog: focus het venster in, Escape sluit, focus terug bij sluiten (#67)
        if (window.A11y && !this.dialog) {
            this.dialog = window.A11y.openDialog(this.window, {
                modal: false,
                onEscape: () => this.close(),
            });
        }

        // Trigger kompas resize
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 300);

        console.log(`🧭 Kompas window opened at ${this.window.style.left}, ${this.window.style.top}`);
    }

    close() {
        this.window.classList.add('closing');
        this.window.classList.remove('opening');
        this.isVisible = false;

        if (this.dialog) {
            this.dialog.close();
            this.dialog = null;
        }

        setTimeout(() => {
            this.window.style.display = 'none';
            this.window.classList.remove('closing');
        }, 200);

        console.log('🧭 Kompas window closed');
    }

    toggle() {
        if (this.isOpen()) {
            this.close();
        } else {
            this.open();
        }
    }
}

// Export for global use
window.DraggableWindow = DraggableWindow;
