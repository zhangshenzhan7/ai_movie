/**
 * 统一认证状态管理模块
 * 用于管理用户登录状态和相关UI显示
 */

class AuthManager {
    constructor() {
        this.isAuthenticated = false;
        this.currentUser = null;
        this.elements = {};
        this.retryCount = 0;
        this.maxRetries = 3;
        
        // 初始化
        this.init();
    }
    
    /**
     * 初始化认证管理器
     */
    init() {
        // 等待DOM完全加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.delayedInit());
        } else {
            this.delayedInit();
        }
    }
    
    /**
     * 延迟初始化，确保DOM元素已加载
     */
    delayedInit() {
        // 缓存DOM元素
        this.cacheElements();
        
        // 设置事件监听器
        this.setupEventListeners();
        
        // 延迟检查认证状态，确保页面元素已渲染
        setTimeout(() => this.checkAuthStatus(), 100);
    }
    
    /**
     * 缓存DOM元素
     */
    cacheElements() {
        this.elements = {
            // 登录/注册按钮
            loginBtn: document.getElementById('loginBtn'),
            registerBtn: document.getElementById('registerBtn'),
            mobileLoginBtn: document.getElementById('mobileLoginBtn'),
            mobileRegisterBtn: document.getElementById('mobileRegisterBtn'),
            
            // 用户菜单
            userMenu: document.getElementById('userMenu'),
            usernameDisplay: document.getElementById('usernameDisplay'),
            userAvatar: document.getElementById('userAvatar'),
            logoutLink: document.getElementById('logoutLink'),
            
            // 移动端用户菜单
            mobileUserMenu: document.getElementById('mobileUserMenu'),
            mobileUsernameDisplay: document.getElementById('mobileUsernameDisplay'),
            mobileUserAvatar: document.getElementById('mobileUserAvatar'),
            mobileLogoutLink: document.getElementById('mobileLogoutLink'),
            
            // 移动端菜单
            mobileMenu: document.getElementById('mobileMenu'),
            mobileMenuBtn: document.getElementById('mobileMenuBtn')
        };
    }
    
    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 登出事件
        if (this.elements.logoutLink) {
            this.elements.logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }
        
        // 移动端登出事件
        if (this.elements.mobileLogoutLink) {
            this.elements.mobileLogoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }
        
        // 用户头像点击事件
        if (this.elements.userAvatar) {
            this.elements.userAvatar.addEventListener('click', () => {
                window.location.href = '/dashboard';
            });
            
            // 键盘导航支持
            this.elements.userAvatar.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    window.location.href = '/dashboard';
                }
            });
        }
        
        // 移动端用户头像点击事件
        if (this.elements.mobileUserAvatar) {
            this.elements.mobileUserAvatar.addEventListener('click', () => {
                window.location.href = '/dashboard';
            });
        }
    }
    
    /**
     * 检查认证状态
     */
    async checkAuthStatus() {
        try {
            console.log('检查认证状态...');
            
            const response = await fetch('/check-auth', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('认证状态检查结果:', data);
            
            if (data.authenticated) {
                this.setAuthenticatedState(data.user);
            } else {
                this.setUnauthenticatedState();
            }
            
            this.retryCount = 0; // 重置重试计数
            return data.authenticated;
        } catch (error) {
            console.error('检查认证状态失败:', error);
            
            // 重试机制
            if (this.retryCount < this.maxRetries) {
                this.retryCount++;
                console.log(`第 ${this.retryCount} 次重试检查认证状态...`);
                setTimeout(() => this.checkAuthStatus(), 1000 * this.retryCount);
                return null; // 重试中，返回null
            }
            
            // 重试失败，设置为未认证状态
            this.setUnauthenticatedState();
            return false;
        }
    }
    
    /**
     * 设置已认证状态
     */
    setAuthenticatedState(user) {
        this.isAuthenticated = true;
        this.currentUser = user;
        
        console.log('设置已认证状态:', user);
        
        // 隐藏登录/注册按钮
        this.hideElement(this.elements.loginBtn);
        this.hideElement(this.elements.registerBtn);
        this.hideElement(this.elements.mobileLoginBtn);
        this.hideElement(this.elements.mobileRegisterBtn);
        
        // 显示用户菜单
        this.showUserMenu(user);
        
        console.log('用户已登录，UI状态已更新');
    }
    
    /**
     * 设置未认证状态
     */
    setUnauthenticatedState() {
        this.isAuthenticated = false;
        this.currentUser = null;
        
        console.log('设置未认证状态');
        
        // 显示登录/注册按钮
        this.showElement(this.elements.loginBtn);
        this.showElement(this.elements.registerBtn);
        this.showElement(this.elements.mobileLoginBtn);
        this.showElement(this.elements.mobileRegisterBtn);
        
        // 隐藏用户菜单
        this.hideUserMenu();
        
        console.log('用户未登录，UI状态已更新');
    }
    
    /**
     * 显示用户菜单
     */
    showUserMenu(user) {
        // 桌面端用户菜单
        if (this.elements.userMenu) {
            this.elements.userMenu.classList.remove('hidden');
            this.elements.userMenu.classList.add('flex');
        }
        
        // 移动端用户菜单
        if (this.elements.mobileUserMenu) {
            this.elements.mobileUserMenu.classList.remove('hidden');
        }
        
        // 更新用户名显示
        if (user && this.elements.usernameDisplay) {
            this.elements.usernameDisplay.textContent = user.username || user.email || '用户';
        }
        
        if (user && this.elements.mobileUsernameDisplay) {
            this.elements.mobileUsernameDisplay.textContent = user.username || user.email || '用户';
        }
        
        // 更新用户头像
        const avatarUrl = `https://picsum.photos/id/${user?.id % 100 || 64}/200/200`;
        const altText = `${user?.username || '用户'} 的头像`;
        
        if (user && this.elements.userAvatar) {
            this.elements.userAvatar.src = avatarUrl;
            this.elements.userAvatar.alt = altText;
        }
        
        if (user && this.elements.mobileUserAvatar) {
            this.elements.mobileUserAvatar.src = avatarUrl;
            this.elements.mobileUserAvatar.alt = altText;
        }
    }
    
    /**
     * 隐藏用户菜单
     */
    hideUserMenu() {
        // 桌面端用户菜单
        if (this.elements.userMenu) {
            this.elements.userMenu.classList.add('hidden');
            this.elements.userMenu.classList.remove('flex');
        }
        
        // 移动端用户菜单
        if (this.elements.mobileUserMenu) {
            this.elements.mobileUserMenu.classList.add('hidden');
        }
    }
    
    /**
     * 用户登录成功后调用
     */
    onLoginSuccess(user, username) {
        console.log('登录成功，更新UI状态:', { user, username });
        
        // 立即设置认证状态
        this.setAuthenticatedState(user);
        
        // 显示成功消息
        if (typeof showNotification === 'function') {
            showNotification('登录成功', `欢迎回来，${username}`, 'success');
        }
        
        // 立即重新检查认证状态以确保一致性
        setTimeout(() => {
            this.checkAuthStatus();
        }, 500);
    }
    
    /**
     * 用户登出
     */
    async logout() {
        try {
            if (typeof showLoading === 'function') {
                showLoading('正在退出...');
            }
            
            const response = await fetch('/logout', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                this.setUnauthenticatedState();
                
                if (typeof showNotification === 'function') {
                    showNotification('退出成功', '您已成功退出登录', 'success');
                }
                
                // 延迟跳转到首页
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                throw new Error('退出失败');
            }
        } catch (error) {
            console.error('退出错误:', error);
            if (typeof showNotification === 'function') {
                showNotification('退出失败', '请稍后重试', 'error');
            }
        } finally {
            if (typeof hideLoading === 'function') {
                hideLoading();
            }
        }
    }
    
    /**
     * 隐藏元素
     */
    hideElement(element) {
        if (element) {
            element.classList.add('hidden');
        }
    }
    
    /**
     * 显示元素
     */
    showElement(element) {
        if (element) {
            element.classList.remove('hidden');
        }
    }
    
    /**
     * 获取当前用户信息
     */
    getCurrentUser() {
        return this.currentUser;
    }
    
    /**
     * 检查是否已认证
     */
    isUserAuthenticated() {
        return this.isAuthenticated;
    }
}

// 创建全局认证管理器实例
window.authManager = new AuthManager();

// 向后兼容的全局函数
window.checkAuthStatus = () => window.authManager.checkAuthStatus();