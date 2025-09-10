/**
 * 并发数配置管理模块
 * 
 * 提供并发工作线程数的查看和设置功能
 */

class ConcurrentConfigManager {
    constructor() {
        this.apiBaseUrl = '/config/concurrent-workers';
        this.currentConfig = null;
        this.systemInfo = null;
        this.init();
    }

    /**
     * 初始化配置管理器
     */
    init() {
        this.createConfigModal();
        this.setupEventListeners();
    }

    /**
     * 创建配置模态框
     */
    createConfigModal() {
        const modalHtml = `
            <div id="concurrentConfigModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
                <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-semibold">并发数配置</h3>
                        <button id="closeConcurrentConfigModal" class="text-gray-500 hover:text-gray-700">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    </div>
                    
                    <div id="configContent">
                        <div class="text-center py-4">
                            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                            <p class="mt-2 text-gray-600">加载配置中...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 设置模态框关闭事件
        document.getElementById('closeConcurrentConfigModal').addEventListener('click', () => {
            this.hideConfigModal();
        });
        
        // 点击模态框外部关闭
        document.getElementById('concurrentConfigModal').addEventListener('click', (e) => {
            if (e.target.id === 'concurrentConfigModal') {
                this.hideConfigModal();
            }
        });
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 可以在这里添加其他事件监听器
    }

    /**
     * 显示配置模态框
     */
    async showConfigModal() {
        const modal = document.getElementById('concurrentConfigModal');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        
        // 加载当前配置
        await this.loadCurrentConfig();
    }

    /**
     * 隐藏配置模态框
     */
    hideConfigModal() {
        const modal = document.getElementById('concurrentConfigModal');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    /**
     * 加载当前配置
     */
    async loadCurrentConfig() {
        try {
            const response = await fetch(this.apiBaseUrl, {
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
            this.currentConfig = data.current_config;
            this.systemInfo = data.system_info;
            
            this.renderConfigContent(data);
        } catch (error) {
            console.error('加载配置失败:', error);
            this.renderError('加载配置失败，请稍后重试');
        }
    }

    /**
     * 渲染配置内容
     */
    renderConfigContent(data) {
        const { current_config, system_info, recommendations } = data;
        
        const contentHtml = `
            <div class="space-y-4">
                <!-- 当前配置 -->
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-medium mb-2">当前配置</h4>
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        <div>最大并发数: <span class="font-medium">${current_config.max_parallel_workers}</span></div>
                        <div>并发场景数: <span class="font-medium">${current_config.concurrent_scenes}</span></div>
                        <div>启用并行: <span class="font-medium">${current_config.enable_parallel ? '是' : '否'}</span></div>
                        <div>自动调整: <span class="font-medium">${current_config.auto_adjust_workers ? '是' : '否'}</span></div>
                    </div>
                </div>

                <!-- 系统信息 -->
                ${system_info.error ? '' : `
                <div class="bg-blue-50 p-4 rounded-lg">
                    <h4 class="font-medium mb-2">系统资源</h4>
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        <div>CPU核心数: <span class="font-medium">${system_info.cpu_count}</span></div>
                        <div>CPU使用率: <span class="font-medium">${system_info.cpu_usage.toFixed(1)}%</span></div>
                        <div>内存总量: <span class="font-medium">${(system_info.memory_total_mb / 1024).toFixed(1)}GB</span></div>
                        <div>内存使用率: <span class="font-medium">${system_info.memory_usage_percent.toFixed(1)}%</span></div>
                    </div>
                </div>
                `}

                <!-- 设置并发数 -->
                <div class="bg-white border border-gray-200 p-4 rounded-lg">
                    <h4 class="font-medium mb-2">设置并发数</h4>
                    <div class="space-y-3">
                        <div>
                            <label for="workersSlider" class="block text-sm text-gray-600 mb-1">
                                并发工作线程数: <span id="workersValue" class="font-medium">${current_config.max_parallel_workers}</span>
                            </label>
                            <input 
                                type="range" 
                                id="workersSlider" 
                                min="1" 
                                max="10" 
                                value="${current_config.max_parallel_workers}"
                                class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                            >
                            <div class="flex justify-between text-xs text-gray-500 mt-1">
                                <span>1</span>
                                <span>推荐: ${recommendations.auto_adjusted_workers}</span>
                                <span>10</span>
                            </div>
                        </div>
                        
                        <div class="flex space-x-2">
                            <button 
                                id="applyConfigBtn" 
                                class="flex-1 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition-colors"
                            >
                                应用设置
                            </button>
                            <button 
                                id="resetConfigBtn" 
                                class="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
                            >
                                重置为推荐值
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 说明 -->
                <div class="bg-yellow-50 p-3 rounded-lg text-sm">
                    <p class="text-yellow-800">
                        <strong>提示:</strong> 
                        并发数过高可能导致系统资源紧张，过低则影响生成速度。
                        建议根据系统资源调整，或启用自动调整功能。
                    </p>
                </div>
            </div>
        `;

        document.getElementById('configContent').innerHTML = contentHtml;
        
        // 设置事件监听器
        this.setupConfigEventListeners();
    }

    /**
     * 设置配置页面的事件监听器
     */
    setupConfigEventListeners() {
        const slider = document.getElementById('workersSlider');
        const valueDisplay = document.getElementById('workersValue');
        const applyBtn = document.getElementById('applyConfigBtn');
        const resetBtn = document.getElementById('resetConfigBtn');

        // 滑块值变化
        slider.addEventListener('input', (e) => {
            valueDisplay.textContent = e.target.value;
        });

        // 应用设置
        applyBtn.addEventListener('click', () => {
            const workers = parseInt(slider.value);
            this.updateConcurrentWorkers(workers);
        });

        // 重置为推荐值
        resetBtn.addEventListener('click', async () => {
            await this.loadCurrentConfig();
            const data = await this.getCurrentConfig();
            const recommendedWorkers = data.recommendations.auto_adjusted_workers;
            slider.value = recommendedWorkers;
            valueDisplay.textContent = recommendedWorkers;
        });
    }

    /**
     * 更新并发工作线程数
     */
    async updateConcurrentWorkers(workers) {
        try {
            const applyBtn = document.getElementById('applyConfigBtn');
            applyBtn.disabled = true;
            applyBtn.textContent = '应用中...';

            const response = await fetch(this.apiBaseUrl, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ workers })
            });

            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccessMessage(`并发数已设置为 ${workers}`);
                // 重新加载配置
                await this.loadCurrentConfig();
            } else {
                throw new Error(data.error || '设置失败');
            }
        } catch (error) {
            console.error('设置并发数失败:', error);
            this.showErrorMessage('设置失败: ' + error.message);
        } finally {
            const applyBtn = document.getElementById('applyConfigBtn');
            if (applyBtn) {
                applyBtn.disabled = false;
                applyBtn.textContent = '应用设置';
            }
        }
    }

    /**
     * updateConfig函数的别名，用于兼容性
     */
    async updateConfig(config) {
        if (typeof config === 'number') {
            return await this.updateConcurrentWorkers(config);
        } else if (config && config.workers) {
            return await this.updateConcurrentWorkers(config.workers);
        } else {
            throw new Error('无效的配置参数');
        }
    }

    /**
     * 获取当前配置
     */
    async getCurrentConfig() {
        const response = await fetch(this.apiBaseUrl, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * 渲染错误信息
     */
    renderError(message) {
        const contentHtml = `
            <div class="text-center py-8">
                <div class="text-red-500 mb-2">
                    <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <p class="text-gray-600">${message}</p>
                <button 
                    onclick="concurrentConfigManager.loadCurrentConfig()" 
                    class="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
                >
                    重试
                </button>
            </div>
        `;

        document.getElementById('configContent').innerHTML = contentHtml;
    }

    /**
     * 显示成功消息
     */
    showSuccessMessage(message) {
        if (typeof showNotification === 'function') {
            showNotification('设置成功', message, 'success');
        } else {
            alert(message);
        }
    }

    /**
     * 显示错误消息
     */
    showErrorMessage(message) {
        if (typeof showNotification === 'function') {
            showNotification('设置失败', message, 'error');
        } else {
            alert(message);
        }
    }
}

// 创建全局实例
window.concurrentConfigManager = new ConcurrentConfigManager();

// 便捷函数
window.showConcurrentConfig = () => {
    window.concurrentConfigManager.showConfigModal();
};

// 兼容性别名
window.ConcurrentConfig = ConcurrentConfigManager;
window.concurrentConfig = window.concurrentConfigManager;