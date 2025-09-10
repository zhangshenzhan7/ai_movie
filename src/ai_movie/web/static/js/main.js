/**
 * Main page interactions and video generation logic
 */

(function() {
    'use strict';

    // Video generation class
    class VideoGenerator {
        constructor() {
            this.currentMode = 'text'; // 'text' or 'image'
            this.uploadedImage = null;
            this.generationInProgress = false;
            this.init();
        }

        init() {
            this.bindEvents();
            this.setupImageUpload();
            this.loadSavedApiKey();
        }

        bindEvents() {
            // Tab switching
            const tabText = document.getElementById('tabText');
            const tabImage = document.getElementById('tabImage');
            
            if (tabText) {
                tabText.addEventListener('click', () => this.switchMode('text'));
            }
            if (tabImage) {
                tabImage.addEventListener('click', () => this.switchMode('image'));
            }

            // Try now buttons
            const tryNowBtn = document.getElementById('tryNowBtn');
            const textToVideoBtn = document.getElementById('textToVideoBtn');
            const imageToVideoBtn = document.getElementById('imageToVideoBtn');

            if (tryNowBtn) {
                tryNowBtn.addEventListener('click', () => this.showGenerator('text'));
            }
            if (textToVideoBtn) {
                textToVideoBtn.addEventListener('click', () => this.showGenerator('text'));
            }
            if (imageToVideoBtn) {
                imageToVideoBtn.addEventListener('click', () => this.showGenerator('image'));
            }

            // Form submission
            const generatorForm = document.getElementById('generatorForm');
            if (generatorForm) {
                generatorForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handleGeneration();
                });
            }

            // Smooth scrolling for anchor links
            document.addEventListener('click', (e) => {
                const link = e.target.closest('a[href^="#"]');
                if (link) {
                    e.preventDefault();
                    const targetId = link.getAttribute('href').slice(1);
                    const targetElement = document.getElementById(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });

            // API Key auto-save
            const apiKeyInput = document.getElementById('apiKey');
            if (apiKeyInput) {
                apiKeyInput.addEventListener('input', 
                    this.debounce(() => this.saveApiKey(), 1000)
                );
            }
        }

        switchMode(mode) {
            this.currentMode = mode;
            
            const tabText = document.getElementById('tabText');
            const tabImage = document.getElementById('tabImage');
            const imageUploadContainer = document.getElementById('imageUploadContainer');
            const generatorTitle = document.getElementById('generatorTitle');

            // Update tab states
            if (mode === 'text') {
                tabText?.classList.add('text-primary', 'border-b-2', 'border-primary');
                tabText?.classList.remove('text-gray-medium');
                tabImage?.classList.remove('text-primary', 'border-b-2', 'border-primary');
                tabImage?.classList.add('text-gray-medium');
                imageUploadContainer?.classList.add('hidden');
                if (generatorTitle) generatorTitle.textContent = '文本生成视频';
            } else {
                tabImage?.classList.add('text-primary', 'border-b-2', 'border-primary');
                tabImage?.classList.remove('text-gray-medium');
                tabText?.classList.remove('text-primary', 'border-b-2', 'border-primary');
                tabText?.classList.add('text-gray-medium');
                imageUploadContainer?.classList.remove('hidden');
                if (generatorTitle) generatorTitle.textContent = '图片生成视频';
            }
        }

        showGenerator(mode = 'text') {
            this.switchMode(mode);
            
            // Scroll to generator section
            const generatorSection = document.getElementById('generator');
            if (generatorSection) {
                generatorSection.classList.remove('hidden');
                setTimeout(() => {
                    generatorSection.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }, 100);
            }
        }

        setupImageUpload() {
            const imageUpload = document.getElementById('imageUpload');
            const uploadContainer = document.querySelector('[data-upload-container]') || 
                document.getElementById('imageUploadContainer')?.querySelector('.border-dashed');
            const previewImage = document.getElementById('previewImage');

            if (imageUpload && uploadContainer) {
                // Click to upload
                uploadContainer.addEventListener('click', () => {
                    imageUpload.click();
                });

                // Drag and drop
                uploadContainer.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadContainer.classList.add('border-primary', 'bg-primary/5');
                });

                uploadContainer.addEventListener('dragleave', (e) => {
                    e.preventDefault();
                    uploadContainer.classList.remove('border-primary', 'bg-primary/5');
                });

                uploadContainer.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadContainer.classList.remove('border-primary', 'bg-primary/5');
                    
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        this.handleImageFile(files[0]);
                    }
                });

                // File input change
                imageUpload.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        this.handleImageFile(e.target.files[0]);
                    }
                });
            }
        }

        handleImageFile(file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                showNotification('文件错误', '请选择图片文件', 'error');
                return;
            }

            // Validate file size (10MB)
            if (file.size > 10 * 1024 * 1024) {
                showNotification('文件过大', '图片文件不能超过10MB', 'error');
                return;
            }

            this.uploadedImage = file;

            // Preview image
            const reader = new FileReader();
            reader.onload = (e) => {
                const previewImage = document.getElementById('previewImage');
                if (previewImage) {
                    previewImage.src = e.target.result;
                    previewImage.classList.remove('hidden');
                }
            };
            reader.readAsDataURL(file);

            showNotification('图片已上传', '图片预览已更新', 'success');
        }

        async handleGeneration() {
            if (this.generationInProgress) return;

            const description = document.getElementById('videoDescription')?.value.trim();
            const apiKey = document.getElementById('apiKey')?.value.trim();

            // Validate inputs
            if (!description) {
                showNotification('输入错误', '请输入视频描述', 'warning');
                document.getElementById('videoDescription')?.focus();
                return;
            }

            if (!apiKey) {
                showNotification('配置错误', '请输入DashScope API Key', 'warning');
                document.getElementById('apiKey')?.focus();
                return;
            }

            if (this.currentMode === 'image' && !this.uploadedImage) {
                showNotification('输入错误', '请上传参考图片', 'warning');
                return;
            }

            try {
                this.generationInProgress = true;
                this.updateGenerationUI(true);

                // Prepare request data
                const formData = new FormData();
                formData.append('description', description);
                formData.append('api_key', apiKey);
                formData.append('generation_type', this.currentMode);
                
                if (this.uploadedImage) {
                    formData.append('image', this.uploadedImage);
                }

                // Start generation
                showLoading('正在生成视频，请稍等...');
                
                const response = await fetch('/api/generate-video', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    showNotification('生成成功', '视频生成请求已提交', 'success');
                    
                    // Redirect to dashboard or show progress
                    if (data.video_id) {
                        this.showGenerationProgress(data.video_id);
                    } else if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1000);
                    }
                } else {
                    throw new Error(data.message || '生成失败');
                }

            } catch (error) {
                console.error('Video generation error:', error);
                showNotification('生成失败', error.message || '请稍后重试', 'error');
            } finally {
                this.generationInProgress = false;
                this.updateGenerationUI(false);
                hideLoading();
            }
        }

        updateGenerationUI(isGenerating) {
            const generateBtn = document.getElementById('generateBtn');
            if (generateBtn) {
                if (isGenerating) {
                    generateBtn.disabled = true;
                    generateBtn.innerHTML = '<div class="spinner mr-2"></div> 生成中...';
                } else {
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fa fa-magic mr-2"></i> 生成视频';
                }
            }
        }

        showGenerationProgress(videoId) {
            // Create or show progress modal
            let progressModal = document.getElementById('progressModal');
            
            if (!progressModal) {
                progressModal = this.createProgressModal();
                document.body.appendChild(progressModal);
            }

            progressModal.classList.remove('hidden');
            progressModal.classList.add('flex');

            // Start polling for progress
            this.pollGenerationProgress(videoId);
        }

        createProgressModal() {
            const modal = document.createElement('div');
            modal.id = 'progressModal';
            modal.className = 'fixed inset-0 bg-black/50 z-50 hidden items-center justify-center p-4';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');

            modal.innerHTML = `
                <div class="bg-white rounded-2xl shadow-card w-full max-w-md p-6">
                    <h3 class="text-xl font-bold mb-4">视频生成中</h3>
                    <div class="space-y-4">
                        <div class="w-full bg-gray-200 rounded-full h-2">
                            <div id="progressBar" class="bg-primary h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                        </div>
                        <p id="progressText" class="text-gray-medium text-center">正在初始化...</p>
                        <div class="flex justify-center">
                            <div class="spinner"></div>
                        </div>
                    </div>
                    <div class="mt-6 flex justify-end">
                        <button id="progressModalClose" class="px-4 py-2 text-gray-medium hover:text-dark">
                            后台运行
                        </button>
                    </div>
                </div>
            `;

            // Close button event
            modal.querySelector('#progressModalClose').addEventListener('click', () => {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
            });

            return modal;
        }

        async pollGenerationProgress(videoId) {
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            const progressModal = document.getElementById('progressModal');

            const poll = async () => {
                try {
                    const response = await fetch(`/api/video-status/${videoId}`);
                    const data = await response.json();

                    if (data.success) {
                        const { status, progress, message } = data;
                        
                        // Update UI
                        if (progressBar) {
                            progressBar.style.width = `${progress}%`;
                        }
                        if (progressText) {
                            progressText.textContent = message || status;
                        }

                        // Check if completed
                        if (status === 'completed') {
                            showNotification('生成完成', '您的视频已生成完成！', 'success');
                            if (progressModal) {
                                progressModal.classList.add('hidden');
                                progressModal.classList.remove('flex');
                            }
                            
                            // Redirect to dashboard
                            setTimeout(() => {
                                window.location.href = '/dashboard';
                            }, 1000);
                            
                            return; // Stop polling
                        } else if (status === 'failed') {
                            showNotification('生成失败', message || '视频生成失败', 'error');
                            if (progressModal) {
                                progressModal.classList.add('hidden');
                                progressModal.classList.remove('flex');
                            }
                            return; // Stop polling
                        }
                    }
                } catch (error) {
                    console.error('Progress polling error:', error);
                }

                // Continue polling if not completed
                setTimeout(poll, 2000);
            };

            poll();
        }

        saveApiKey() {
            const apiKey = document.getElementById('apiKey')?.value.trim();
            if (apiKey) {
                localStorage.setItem('dashscope_api_key', apiKey);
            }
        }

        loadSavedApiKey() {
            const savedKey = localStorage.getItem('dashscope_api_key');
            const apiKeyInput = document.getElementById('apiKey');
            if (savedKey && apiKeyInput) {
                apiKeyInput.value = savedKey;
            }
        }

        // Utility function for debouncing
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    }

    // Smooth scroll to top button
    function setupScrollToTop() {
        const scrollBtn = document.createElement('button');
        scrollBtn.id = 'scrollToTop';
        scrollBtn.className = 'fixed bottom-6 right-6 w-12 h-12 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 transition-all duration-300 z-40 opacity-0 invisible focus-visible:focus';
        scrollBtn.innerHTML = '<i class="fa fa-chevron-up" aria-hidden="true"></i>';
        scrollBtn.setAttribute('aria-label', '返回顶部');
        
        document.body.appendChild(scrollBtn);

        // Show/hide based on scroll position
        let ticking = false;
        function updateScrollButton() {
            const scrollY = window.scrollY;
            if (scrollY > 300) {
                scrollBtn.classList.remove('opacity-0', 'invisible');
                scrollBtn.classList.add('opacity-100', 'visible');
            } else {
                scrollBtn.classList.add('opacity-0', 'invisible');
                scrollBtn.classList.remove('opacity-100', 'visible');
            }
            ticking = false;
        }

        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateScrollButton);
                ticking = true;
            }
        });

        // Scroll to top functionality
        scrollBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // Lazy loading for images
    function setupLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // Enhanced navbar scroll effect
    function setupNavbarScrollEffect() {
        const navbar = document.getElementById('navbar');
        if (!navbar) return;

        let lastScrollY = window.scrollY;
        let ticking = false;

        function updateNavbar() {
            const scrollY = window.scrollY;
            
            if (scrollY > 100) {
                navbar.classList.add('shadow-lg');
                navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
            } else {
                navbar.classList.remove('shadow-lg');
                navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
            }

            // Auto-hide navbar on scroll down, show on scroll up
            if (scrollY > lastScrollY && scrollY > 200) {
                navbar.style.transform = 'translateY(-100%)';
            } else {
                navbar.style.transform = 'translateY(0)';
            }

            lastScrollY = scrollY;
            ticking = false;
        }

        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateNavbar);
                ticking = true;
            }
        });
    }

    // Initialize everything
    function init() {
        new VideoGenerator();
        setupScrollToTop();
        setupLazyLoading();
        setupNavbarScrollEffect();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();