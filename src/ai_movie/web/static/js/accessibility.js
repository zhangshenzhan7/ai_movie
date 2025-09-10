/**
 * Accessibility Enhancement Module
 * Provides keyboard navigation, screen reader support, and other accessibility features
 */

(function() {
    'use strict';

    // Accessibility manager class
    class AccessibilityManager {
        constructor() {
            this.focusableElements = 'a, button, input, textarea, select, details, [tabindex]:not([tabindex="-1"])';
            this.init();
        }

        init() {
            this.setupKeyboardNavigation();
            this.setupFocusManagement();
            this.setupSkipLinks();
            this.setupLiveRegions();
            this.setupReducedMotion();
            this.setupHighContrast();
            this.announcePageChanges();
        }

        // Enhanced keyboard navigation
        setupKeyboardNavigation() {
            document.addEventListener('keydown', (e) => {
                // ESC key handling
                if (e.key === 'Escape') {
                    this.handleEscapeKey();
                }

                // Tab trapping in modals
                if (e.key === 'Tab') {
                    this.handleTabKey(e);
                }

                // Arrow key navigation for grouped elements
                if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                    this.handleArrowKeys(e);
                }

                // Enter and Space for button-like elements
                if (e.key === 'Enter' || e.key === ' ') {
                    this.handleActivation(e);
                }
            });
        }

        // Focus management
        setupFocusManagement() {
            // Track focus for better visual feedback
            let focusedByKeyboard = false;

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    focusedByKeyboard = true;
                }
            });

            document.addEventListener('mousedown', () => {
                focusedByKeyboard = false;
            });

            document.addEventListener('focusin', (e) => {
                if (focusedByKeyboard) {
                    e.target.classList.add('keyboard-focus');
                }
            });

            document.addEventListener('focusout', (e) => {
                e.target.classList.remove('keyboard-focus');
            });

            // Focus restoration for SPAs
            this.previouslyFocusedElement = null;
        }

        // Skip links for screen readers
        setupSkipLinks() {
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.textContent = '跳转到主内容';
            skipLink.className = 'skip-link sr-only focus:not-sr-only fixed top-4 left-4 z-50 bg-primary text-white px-4 py-2 rounded-md';
            skipLink.setAttribute('aria-label', '跳过导航，直接到主内容');

            document.body.insertBefore(skipLink, document.body.firstChild);

            // Ensure main content has proper ID
            const main = document.querySelector('main');
            if (main && !main.id) {
                main.id = 'main-content';
                main.setAttribute('tabindex', '-1');
            }
        }

        // Live regions for dynamic content updates
        setupLiveRegions() {
            // Create screen reader announcements container
            const liveRegion = document.createElement('div');
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            liveRegion.id = 'live-region';
            document.body.appendChild(liveRegion);

            // Create urgent announcements container
            const urgentRegion = document.createElement('div');
            urgentRegion.setAttribute('aria-live', 'assertive');
            urgentRegion.setAttribute('aria-atomic', 'true');
            urgentRegion.className = 'sr-only';
            urgentRegion.id = 'urgent-region';
            document.body.appendChild(urgentRegion);
        }

        // Reduced motion preference handling
        setupReducedMotion() {
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
            
            const handleReducedMotion = (mediaQuery) => {
                if (mediaQuery.matches) {
                    document.documentElement.classList.add('reduce-motion');
                } else {
                    document.documentElement.classList.remove('reduce-motion');
                }
            };

            handleReducedMotion(prefersReducedMotion);
            prefersReducedMotion.addListener(handleReducedMotion);
        }

        // High contrast mode handling
        setupHighContrast() {
            const prefersHighContrast = window.matchMedia('(prefers-contrast: high)');
            
            const handleHighContrast = (mediaQuery) => {
                if (mediaQuery.matches) {
                    document.documentElement.classList.add('high-contrast');
                } else {
                    document.documentElement.classList.remove('high-contrast');
                }
            };

            handleHighContrast(prefersHighContrast);
            prefersHighContrast.addListener(handleHighContrast);
        }

        // Handle escape key
        handleEscapeKey() {
            // Close any open modals
            const openModals = document.querySelectorAll('[role="dialog"]:not(.hidden)');
            openModals.forEach(modal => {
                const closeBtn = modal.querySelector('[aria-label*="关闭"]');
                if (closeBtn) {
                    closeBtn.click();
                }
            });

            // Close dropdown menus
            const openDropdowns = document.querySelectorAll('[aria-expanded="true"]');
            openDropdowns.forEach(dropdown => {
                dropdown.click();
            });
        }

        // Handle tab key for modal focus trapping
        handleTabKey(e) {
            const modal = document.querySelector('[role="dialog"]:not(.hidden)');
            if (!modal) return;

            const focusableElements = modal.querySelectorAll(this.focusableElements);
            const firstFocusable = focusableElements[0];
            const lastFocusable = focusableElements[focusableElements.length - 1];

            if (e.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }

        // Handle arrow keys for navigation
        handleArrowKeys(e) {
            const currentElement = e.target;
            
            // Handle menu navigation
            if (currentElement.getAttribute('role') === 'menuitem') {
                e.preventDefault();
                const menu = currentElement.closest('[role="menu"], [role="menubar"]');
                const menuItems = menu.querySelectorAll('[role="menuitem"]');
                const currentIndex = Array.from(menuItems).indexOf(currentElement);
                
                let nextIndex;
                if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                    nextIndex = (currentIndex + 1) % menuItems.length;
                } else {
                    nextIndex = (currentIndex - 1 + menuItems.length) % menuItems.length;
                }
                
                menuItems[nextIndex].focus();
            }

            // Handle tab navigation
            if (currentElement.getAttribute('role') === 'tab') {
                e.preventDefault();
                const tabList = currentElement.closest('[role="tablist"]');
                const tabs = tabList.querySelectorAll('[role="tab"]');
                const currentIndex = Array.from(tabs).indexOf(currentElement);
                
                let nextIndex;
                if (e.key === 'ArrowRight') {
                    nextIndex = (currentIndex + 1) % tabs.length;
                } else if (e.key === 'ArrowLeft') {
                    nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
                }
                
                if (nextIndex !== undefined) {
                    tabs[nextIndex].focus();
                    tabs[nextIndex].click(); // Activate the tab
                }
            }
        }

        // Handle enter and space activation
        handleActivation(e) {
            const element = e.target;
            
            // Handle button-like elements
            if (element.getAttribute('role') === 'button' || 
                element.classList.contains('btn') ||
                element.hasAttribute('data-clickable')) {
                
                e.preventDefault();
                element.click();
            }

            // Handle links that look like buttons
            if (element.tagName === 'A' && element.classList.contains('btn')) {
                // Let the default behavior happen for links
            }
        }

        // Announce page changes for SPAs
        announcePageChanges() {
            // Monitor for dynamic content changes
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                this.announceNewContent(node);
                            }
                        });
                    }
                });
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }

        // Announce new content to screen readers
        announceNewContent(element) {
            // Announce form errors
            if (element.getAttribute('role') === 'alert' || 
                element.classList.contains('error-message')) {
                this.announce(element.textContent, 'assertive');
            }

            // Announce successful actions
            if (element.classList.contains('success-message')) {
                this.announce(element.textContent, 'polite');
            }

            // Announce loading states
            if (element.textContent.includes('加载中') || 
                element.textContent.includes('正在处理')) {
                this.announce(element.textContent, 'polite');
            }
        }

        // Announce messages to screen readers
        announce(message, priority = 'polite') {
            const regionId = priority === 'assertive' ? 'urgent-region' : 'live-region';
            const region = document.getElementById(regionId);
            
            if (region) {
                region.textContent = message;
                
                // Clear after announcement
                setTimeout(() => {
                    region.textContent = '';
                }, 1000);
            }
        }

        // Form accessibility enhancements
        enhanceFormAccessibility() {
            document.querySelectorAll('form').forEach(form => {
                // Add form validation announcements
                form.addEventListener('submit', (e) => {
                    const invalidFields = form.querySelectorAll(':invalid');
                    if (invalidFields.length > 0) {
                        this.announce(`表单有 ${invalidFields.length} 个错误需要修正`, 'assertive');
                        invalidFields[0].focus();
                    }
                });

                // Enhance field validation feedback
                form.querySelectorAll('input, textarea, select').forEach(field => {
                    field.addEventListener('invalid', () => {
                        this.announce(`${field.labels[0]?.textContent || '字段'} 输入有误`, 'assertive');
                    });
                });
            });
        }

        // Color contrast checking (development helper)
        checkColorContrast() {
            if (process.env.NODE_ENV === 'development') {
                // This would be implemented in development to check contrast ratios
                console.log('Color contrast checking would run in development mode');
            }
        }

        // Initialize ARIA attributes for dynamic content
        initializeARIA() {
            // Add ARIA labels to unlabeled interactive elements
            document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])').forEach(button => {
                if (!button.textContent.trim()) {
                    console.warn('Button without accessible name found:', button);
                }
            });

            // Add ARIA expanded to collapsible elements
            document.querySelectorAll('[data-toggle]').forEach(toggle => {
                if (!toggle.hasAttribute('aria-expanded')) {
                    toggle.setAttribute('aria-expanded', 'false');
                }
            });

            // Add ARIA describedby for form fields with help text
            document.querySelectorAll('.form-help').forEach(helpText => {
                const fieldId = helpText.getAttribute('data-field');
                const field = document.getElementById(fieldId);
                if (field) {
                    helpText.id = helpText.id || `${fieldId}-help`;
                    field.setAttribute('aria-describedby', helpText.id);
                }
            });
        }
    }

    // Keyboard shortcuts manager
    class KeyboardShortcuts {
        constructor() {
            this.shortcuts = new Map();
            this.init();
        }

        init() {
            document.addEventListener('keydown', (e) => {
                const key = this.getShortcutKey(e);
                const action = this.shortcuts.get(key);
                
                if (action && !this.isInputFocused()) {
                    e.preventDefault();
                    action();
                }
            });

            this.registerDefaultShortcuts();
        }

        getShortcutKey(e) {
            const modifiers = [];
            if (e.ctrlKey || e.metaKey) modifiers.push('ctrl');
            if (e.shiftKey) modifiers.push('shift');
            if (e.altKey) modifiers.push('alt');
            modifiers.push(e.key.toLowerCase());
            return modifiers.join('+');
        }

        isInputFocused() {
            const activeElement = document.activeElement;
            return activeElement && 
                   (activeElement.tagName === 'INPUT' || 
                    activeElement.tagName === 'TEXTAREA' || 
                    activeElement.contentEditable === 'true');
        }

        register(key, action, description) {
            this.shortcuts.set(key, action);
        }

        registerDefaultShortcuts() {
            // Home page
            this.register('h', () => {
                window.location.href = '/';
            }, '回到首页');

            // Dashboard
            this.register('d', () => {
                window.location.href = '/dashboard';
            }, '打开仪表板');

            // Search
            this.register('ctrl+k', () => {
                const searchInput = document.querySelector('input[type="search"], input[placeholder*="搜索"]');
                if (searchInput) {
                    searchInput.focus();
                }
            }, '聚焦搜索');

            // Help
            this.register('?', () => {
                this.showKeyboardShortcuts();
            }, '显示快捷键帮助');
        }

        showKeyboardShortcuts() {
            // Create and show keyboard shortcuts modal
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-labelledby', 'shortcuts-title');
            modal.setAttribute('aria-modal', 'true');

            modal.innerHTML = `
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                    <h3 id="shortcuts-title" class="text-xl font-bold mb-4">键盘快捷键</h3>
                    <div class="space-y-2 mb-6">
                        <div class="flex justify-between">
                            <span>首页</span>
                            <kbd class="px-2 py-1 bg-gray-100 rounded text-sm">H</kbd>
                        </div>
                        <div class="flex justify-between">
                            <span>仪表板</span>
                            <kbd class="px-2 py-1 bg-gray-100 rounded text-sm">D</kbd>
                        </div>
                        <div class="flex justify-between">
                            <span>搜索</span>
                            <kbd class="px-2 py-1 bg-gray-100 rounded text-sm">Ctrl+K</kbd>
                        </div>
                        <div class="flex justify-between">
                            <span>帮助</span>
                            <kbd class="px-2 py-1 bg-gray-100 rounded text-sm">?</kbd>
                        </div>
                    </div>
                    <button class="w-full py-2 bg-primary text-white rounded-lg" onclick="this.closest('[role=dialog]').remove()">
                        关闭
                    </button>
                </div>
            `;

            document.body.appendChild(modal);
            modal.querySelector('button').focus();

            // Close on ESC
            const closeHandler = (e) => {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.removeEventListener('keydown', closeHandler);
                }
            };
            document.addEventListener('keydown', closeHandler);
        }
    }

    // Initialize accessibility features
    function init() {
        new AccessibilityManager();
        new KeyboardShortcuts();
    }

    // Initialize when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for testing
    window.AccessibilityManager = AccessibilityManager;

})();