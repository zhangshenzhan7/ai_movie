/**
 * Form Validation and Interaction Logic
 * Handles login, register forms with real-time validation and accessibility
 */

(function() {
    'use strict';

    // Validation rules
    const ValidationRules = {
        email: {
            required: true,
            pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: '请输入有效的邮箱地址'
        },
        username: {
            required: true,
            minLength: 3,
            maxLength: 20,
            pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/,
            message: '用户名应为3-20个字符，仅支持字母、数字、下划线和中文'
        },
        password: {
            required: true,
            minLength: 8,
            message: '密码至少需要8个字符'
        }
    };

    // Form validation class
    class FormValidator {
        constructor(formElement) {
            this.form = formElement;
            this.fields = new Map();
            this.isValid = false;
            this.init();
        }

        init() {
            this.bindEvents();
            this.setupFields();
        }

        setupFields() {
            const inputs = this.form.querySelectorAll('input[required]');
            inputs.forEach(input => {
                this.fields.set(input.name || input.id, {
                    element: input,
                    isValid: false,
                    errorElement: document.getElementById(input.getAttribute('aria-describedby')?.split(' ')[0])
                });
            });
        }

        bindEvents() {
            // Real-time validation on input
            this.form.addEventListener('input', (e) => {
                if (e.target.tagName === 'INPUT') {
                    this.validateField(e.target);
                    this.updateSubmitButton();
                }
            });

            // Validation on blur
            this.form.addEventListener('blur', (e) => {
                if (e.target.tagName === 'INPUT') {
                    this.validateField(e.target);
                }
            }, true);

            // Form submission
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubmit();
            });
        }

        validateField(input) {
            const fieldName = input.name || input.id;
            const value = input.value.trim();
            const field = this.fields.get(fieldName);
            
            if (!field) return;

            let isValid = true;
            let message = '';

            // Get validation rules for this field type
            const rules = this.getValidationRules(input);

            // Required validation
            if (rules.required && !value) {
                isValid = false;
                message = '此字段为必填项';
            }
            // Length validation
            else if (value && rules.minLength && value.length < rules.minLength) {
                isValid = false;
                message = `至少需要${rules.minLength}个字符`;
            }
            else if (value && rules.maxLength && value.length > rules.maxLength) {
                isValid = false;
                message = `不能超过${rules.maxLength}个字符`;
            }
            // Pattern validation
            else if (value && rules.pattern && !rules.pattern.test(value)) {
                isValid = false;
                message = rules.message || '格式不正确';
            }
            // Password confirmation
            else if (fieldName === 'confirm_password') {
                const passwordField = this.form.querySelector('input[name="password"]');
                if (passwordField && value !== passwordField.value) {
                    isValid = false;
                    message = '密码确认不匹配';
                }
            }
            // Terms agreement
            else if (fieldName === 'agree_terms' && input.type === 'checkbox' && !input.checked) {
                isValid = false;
                message = '请阅读并同意用户协议';
            }

            // Update field state
            field.isValid = isValid;
            this.updateFieldUI(input, field.errorElement, isValid, message);

            // Update password strength for password fields
            if (input.type === 'password' && input.name === 'password') {
                this.updatePasswordStrength(value);
            }

            return isValid;
        }

        getValidationRules(input) {
            const type = input.type;
            const name = input.name || input.id;
            
            if (name.includes('email') || type === 'email') {
                return ValidationRules.email;
            } else if (name.includes('username')) {
                return ValidationRules.username;
            } else if (name.includes('password')) {
                return ValidationRules.password;
            }
            
            return { required: input.hasAttribute('required') };
        }

        updateFieldUI(input, errorElement, isValid, message) {
            // Update input styles
            if (isValid) {
                input.classList.remove('border-red-500', 'focus:ring-red-500');
                input.classList.add('border-green-500', 'focus:ring-green-500');
                input.setAttribute('aria-invalid', 'false');
            } else {
                input.classList.remove('border-green-500', 'focus:ring-green-500');
                input.classList.add('border-red-500', 'focus:ring-red-500');
                input.setAttribute('aria-invalid', 'true');
            }

            // Update error message
            if (errorElement) {
                if (isValid) {
                    errorElement.classList.add('hidden');
                    errorElement.textContent = '';
                } else {
                    errorElement.classList.remove('hidden');
                    errorElement.textContent = message;
                }
            }
        }

        updatePasswordStrength(password) {
            const strengthElement = document.getElementById('passwordStrength');
            const strengthText = document.getElementById('strengthText');
            
            if (!strengthElement || !strengthText) return;

            if (!password) {
                strengthElement.classList.add('hidden');
                return;
            }

            strengthElement.classList.remove('hidden');

            let score = 0;
            const checks = {
                length: password.length >= 8,
                lowercase: /[a-z]/.test(password),
                uppercase: /[A-Z]/.test(password),
                numbers: /\d/.test(password),
                special: /[^a-zA-Z\d]/.test(password)
            };

            score = Object.values(checks).filter(Boolean).length;

            const levels = ['很弱', '弱', '中等', '强', '很强'];
            const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];

            // Update strength bars
            for (let i = 1; i <= 4; i++) {
                const bar = document.getElementById(`strength${i}`);
                if (bar) {
                    bar.className = 'h-1 flex-1 rounded transition-colors';
                    if (i <= score) {
                        bar.classList.add(colors[Math.min(score - 1, 4)]);
                    } else {
                        bar.classList.add('bg-gray-200');
                    }
                }
            }

            strengthText.textContent = `密码强度: ${levels[Math.min(score - 1, 4)] || '很弱'}`;
        }

        updateSubmitButton() {
            const submitBtn = this.form.querySelector('button[type="submit"]');
            if (!submitBtn) return;

            // Check if all required fields are valid
            let allValid = true;
            this.fields.forEach(field => {
                if (field.element.hasAttribute('required') && !field.isValid) {
                    allValid = false;
                }
            });

            this.isValid = allValid;
            submitBtn.disabled = !allValid;
            
            if (allValid) {
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }

        async handleSubmit() {
            // Validate all fields before submission
            let isFormValid = true;
            this.fields.forEach((field, fieldName) => {
                const fieldValid = this.validateField(field.element);
                if (!fieldValid) isFormValid = false;
            });

            if (!isFormValid) {
                const firstInvalidField = Array.from(this.fields.values())
                    .find(field => !field.isValid);
                if (firstInvalidField) {
                    firstInvalidField.element.focus();
                }
                return;
            }

            // Handle form submission based on form type
            const formId = this.form.id;
            if (formId === 'loginForm') {
                await this.handleLogin();
            } else if (formId === 'registerForm') {
                await this.handleRegister();
            }
        }

        async handleLogin() {
            const formData = new FormData(this.form);
            const submitBtn = this.form.querySelector('button[type="submit"]');
            const btnText = submitBtn.querySelector('.login-btn-text');
            const spinner = submitBtn.querySelector('.login-spinner');

            try {
                // Show loading state
                submitBtn.disabled = true;
                btnText.textContent = '登录中...';
                spinner.classList.remove('hidden');

                const response = await apiRequest('/login', {
                    method: 'POST',
                    body: JSON.stringify({
                        email: formData.get('email'),
                        password: formData.get('password'),
                        remember_me: formData.get('remember_me') === 'on'
                    })
                });

                if (response.status === 'success') {
                    // 立即更新UI状态
                    this.updateUIAfterLogin(response.user, response.username);
                    
                    // 显示成功通知
                    showNotification('登录成功', `欢迎回来，${response.username}`, 'success');
                    
                    // 关闭登录模态框
                    closeModal('loginModal');
                    
                } else {
                    throw new Error(response.error || response.message || '登录失败');
                }
            } catch (error) {
                this.showFormError('loginFormError', error.message || '登录失败，请稍后重试');
            } finally {
                // Reset button state
                submitBtn.disabled = false;
                btnText.textContent = '登录';
                spinner.classList.add('hidden');
            }
        }
        
        /**
         * 登录成功后立即更新UI状态
         */
        updateUIAfterLogin(user, username) {
            // 等待认证管理器加载并调用
            const updateAuthState = () => {
                if (window.authManager) {
                    window.authManager.onLoginSuccess(user || {}, username);
                } else {
                    // 如果认证管理器未加载，手动更新UI
                    this.manuallyUpdateUI(user, username);
                }
            };
            
            // 立即尝试更新
            updateAuthState();
            
            // 如果认证管理器还没加载，等待一下再试
            if (!window.authManager) {
                setTimeout(updateAuthState, 100);
                setTimeout(updateAuthState, 500); // 备用重试
            }
        }
        
        /**
         * 手动更新UI状态（备用方案）
         */
        manuallyUpdateUI(user, username) {
            // 隐藏登录/注册按钮
            const elementsToHide = ['loginBtn', 'registerBtn', 'mobileLoginBtn', 'mobileRegisterBtn'];
            elementsToHide.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.classList.add('hidden');
                }
            });
            
            // 显示用户菜单
            const userMenu = document.getElementById('userMenu');
            const mobileUserMenu = document.getElementById('mobileUserMenu');
            
            if (userMenu) {
                userMenu.classList.remove('hidden');
                userMenu.classList.add('flex');
            }
            
            if (mobileUserMenu) {
                mobileUserMenu.classList.remove('hidden');
            }
            
            // 更新用户信息显示
            this.updateUserDisplay(user, username);
        }
        
        /**
         * 更新用户信息显示
         */
        updateUserDisplay(user, username) {
            const displayName = username || user?.username || user?.email || '用户';
            const avatarUrl = `https://picsum.photos/id/${user?.id % 100 || 64}/200/200`;
            const altText = `${displayName} 的头像`;
            
            // 更新桌面端用户信息
            const usernameDisplay = document.getElementById('usernameDisplay');
            const userAvatar = document.getElementById('userAvatar');
            
            if (usernameDisplay) {
                usernameDisplay.textContent = displayName;
            }
            
            if (userAvatar) {
                userAvatar.src = avatarUrl;
                userAvatar.alt = altText;
            }
            
            // 更新移动端用户信息
            const mobileUsernameDisplay = document.getElementById('mobileUsernameDisplay');
            const mobileUserAvatar = document.getElementById('mobileUserAvatar');
            
            if (mobileUsernameDisplay) {
                mobileUsernameDisplay.textContent = displayName;
            }
            
            if (mobileUserAvatar) {
                mobileUserAvatar.src = avatarUrl;
                mobileUserAvatar.alt = altText;
            }
        }

        async handleRegister() {
            const formData = new FormData(this.form);
            const submitBtn = this.form.querySelector('button[type="submit"]');
            const btnText = submitBtn.querySelector('.register-btn-text');
            const spinner = submitBtn.querySelector('.register-spinner');

            try {
                // Show loading state
                submitBtn.disabled = true;
                btnText.textContent = '注册中...';
                spinner.classList.remove('hidden');

                const response = await apiRequest('/register', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: formData.get('username'),
                        email: formData.get('email'),
                        password: formData.get('password'),
                        confirm_password: formData.get('confirm_password')
                    })
                });

                if (response.success) {
                    showNotification('注册成功', '请查看邮箱验证链接', 'success');
                    closeModal('registerModal');
                    // Auto-open login modal
                    setTimeout(() => {
                        openModal('loginModal');
                    }, 1000);
                } else {
                    throw new Error(response.message || '注册失败');
                }
            } catch (error) {
                this.showFormError('registerFormError', error.message || '注册失败，请稍后重试');
            } finally {
                // Reset button state
                submitBtn.disabled = false;
                btnText.textContent = '注册';
                spinner.classList.add('hidden');
            }
        }

        showFormError(errorId, message) {
            const errorElement = document.getElementById(errorId);
            if (errorElement) {
                errorElement.textContent = message;
                errorElement.classList.remove('hidden');
                errorElement.focus();
            }
        }

        clearFormError(errorId) {
            const errorElement = document.getElementById(errorId);
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.classList.add('hidden');
            }
        }
    }

    // Modal management
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            
            // Focus on first input
            const firstInput = modal.querySelector('input');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
            
            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        }
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            
            // Restore body scroll
            document.body.style.overflow = '';
            
            // Clear form errors
            const form = modal.querySelector('form');
            if (form) {
                const errorElements = form.querySelectorAll('[role="alert"]');
                errorElements.forEach(el => {
                    el.classList.add('hidden');
                    el.textContent = '';
                });
            }
        }
    }

    // Password visibility toggle
    function setupPasswordToggle() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('#toggleLoginPassword, #toggleRegisterPassword')) {
                const button = e.target.closest('button');
                const input = button.parentElement.querySelector('input');
                const icon = button.querySelector('i');
                
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.className = 'fa fa-eye-slash';
                    button.setAttribute('aria-label', '隐藏密码');
                } else {
                    input.type = 'password';
                    icon.className = 'fa fa-eye';
                    button.setAttribute('aria-label', '显示密码');
                }
            }
        });
    }

    // Initialize when DOM is loaded
    function init() {
        // Setup modal controls
        document.addEventListener('click', (e) => {
            const target = e.target;
            
            // Modal triggers
            if (target.id === 'loginBtn' || target.id === 'mobileLoginBtn') {
                openModal('loginModal');
            } else if (target.id === 'registerBtn' || target.id === 'mobileRegisterBtn') {
                openModal('registerModal');
            }
            // Modal close buttons
            else if (target.id === 'closeLoginModal') {
                closeModal('loginModal');
            } else if (target.id === 'closeRegisterModal') {
                closeModal('registerModal');
            }
            // Switch between modals
            else if (target.id === 'switchToRegister') {
                closeModal('loginModal');
                openModal('registerModal');
            } else if (target.id === 'switchToLogin') {
                closeModal('registerModal');
                openModal('loginModal');
            }
        });

        // Close modal on backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('fixed') && 
                e.target.classList.contains('inset-0') &&
                e.target.getAttribute('role') === 'dialog') {
                const modalId = e.target.id;
                closeModal(modalId);
            }
        });

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('[role="dialog"]:not(.hidden)');
                if (openModal) {
                    closeModal(openModal.id);
                }
            }
        });

        // Initialize form validators
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            new FormValidator(loginForm);
        }

        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            new FormValidator(registerForm);
        }

        // Setup password toggle
        setupPasswordToggle();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export utilities for global use
    window.FormUtils = {
        openModal,
        closeModal,
        FormValidator
    };

})();