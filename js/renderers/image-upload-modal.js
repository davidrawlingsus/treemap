/**
 * Image Upload Modal Module
 * Handles media upload modal with drag-and-drop and progress indication.
 */

import { uploadAdImage } from '/js/services/api-ad-images.js';
import { addImageToCache } from '/js/state/images-state.js';

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Show image upload modal
 * @param {Function} onImageAdded - Callback when an image is successfully uploaded
 */
export function showImageUploadModal(onImageAdded) {
    const clientId = window.appStateGet?.('currentClientId') || 
                     document.getElementById('clientSelect')?.value;
    
    if (!clientId) {
        alert('Please select a client first');
        return;
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'images-upload-overlay';
    overlay.innerHTML = `
        <div class="images-upload-modal">
            <div class="images-upload-modal__header">
                <h2>Upload Media</h2>
                <button class="images-upload-modal__close" onclick="this.closest('.images-upload-overlay').remove()">×</button>
            </div>
            <div class="images-upload-modal__body">
                <input type="file" id="imageUploadInput" accept="image/*,video/*" multiple style="display: none;">
                <div class="images-upload-dropzone" id="imageUploadDropzone">
                    <div class="images-upload-dropzone__content">
                        <div class="images-upload-dropzone__icon">📤</div>
                        <p>Click to select or drag and drop</p>
                        <p class="images-upload-dropzone__hint">Supports images and videos up to 50MB</p>
                    </div>
                </div>
                <div class="images-upload-progress" id="imageUploadProgress" style="display: none;">
                    <div class="images-upload-progress__bar" id="imageUploadProgressBar"></div>
                    <p class="images-upload-progress__text">Uploading...</p>
                </div>
            </div>
            <div class="images-upload-modal__footer">
                <button class="images-upload-modal__cancel" onclick="this.closest('.images-upload-overlay').remove()">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    const fileInput = overlay.querySelector('#imageUploadInput');
    const dropzone = overlay.querySelector('#imageUploadDropzone');
    const progress = overlay.querySelector('#imageUploadProgress');
    const progressBar = overlay.querySelector('#imageUploadProgressBar');
    
    // Click to select file
    dropzone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files || []);
        if (files.length > 0) {
            if (files.length === 1) {
                await handleMediaUpload(files[0], clientId, overlay, progress, progressBar, onImageAdded);
            } else {
                await handleBulkMediaUpload(files, clientId, overlay, progress, progressBar, onImageAdded);
            }
        }
    });
    
    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('is-dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('is-dragover');
    });
    
    dropzone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropzone.classList.remove('is-dragover');
        const files = Array.from(e.dataTransfer.files).filter(f => 
            f.type.startsWith('image/') || f.type.startsWith('video/')
        );
        if (files.length > 0) {
            if (files.length === 1) {
                await handleMediaUpload(files[0], clientId, overlay, progress, progressBar, onImageAdded);
            } else {
                await handleBulkMediaUpload(files, clientId, overlay, progress, progressBar, onImageAdded);
            }
        }
    });
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

/**
 * Handle single media upload (image or video)
 */
async function handleMediaUpload(file, clientId, overlay, progress, progressBar, onImageAdded) {
    if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
        alert('Please select an image or video file');
        return;
    }
    
    // Check file size (50MB limit for server uploads)
    const MAX_SIZE = 50 * 1024 * 1024; // 50MB
    if (file.size > MAX_SIZE) {
        alert(`File is too large. Maximum size is 50MB. Your file is ${formatFileSize(file.size)}.`);
        return;
    }
    
    progress.style.display = 'block';
    progressBar.style.width = '0%';
    
    try {
        // Simulate progress (actual upload happens in service)
        let progressValue = 0;
        const progressInterval = setInterval(() => {
            progressValue += 10;
            if (progressValue < 90) {
                progressBar.style.width = progressValue + '%';
            }
        }, 100);
        
        const image = await uploadAdImage(clientId, file);
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        
        addImageToCache(image);
        
        // Notify caller that image was added
        if (onImageAdded) {
            onImageAdded(image);
        }
        
        // Close modal after short delay
        setTimeout(() => {
            overlay.remove();
        }, 500);
    } catch (error) {
        console.error('[ImageUploadModal] Upload failed:', error);
        alert('Failed to upload image: ' + error.message);
        progress.style.display = 'none';
    }
}

/**
 * Handle bulk media upload (images and videos)
 */
async function handleBulkMediaUpload(files, clientId, overlay, progress, progressBar, onImageAdded) {
    progress.style.display = 'block';
    progressBar.style.width = '0%';
    
    // Check file sizes (50MB limit)
    const MAX_SIZE = 50 * 1024 * 1024; // 50MB
    const oversizedFiles = files.filter(f => f.size > MAX_SIZE);
    if (oversizedFiles.length > 0) {
        const names = oversizedFiles.map(f => `${f.name} (${formatFileSize(f.size)})`).join(', ');
        alert(`Some files are too large (max 50MB): ${names}`);
        // Filter out oversized files
        files = files.filter(f => f.size <= MAX_SIZE);
        if (files.length === 0) {
            progress.style.display = 'none';
            return;
        }
    }
    
    const totalFiles = files.length;
    let successCount = 0;
    let failCount = 0;
    const errors = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const progressPercent = Math.round((i / totalFiles) * 100);
        progressBar.style.width = progressPercent + '%';
        progress.querySelector('.images-upload-progress__text').textContent = `Uploading ${i + 1} of ${totalFiles}...`;
        
        try {
            const image = await uploadAdImage(clientId, file);
            addImageToCache(image);
            
            // Notify caller that image was added
            if (onImageAdded) {
                onImageAdded(image);
            }
            
            successCount++;
        } catch (error) {
            failCount++;
            errors.push(`${file.name}: ${error.message}`);
        }
    }
    
    progressBar.style.width = '100%';
    
    // Show results
    if (failCount === 0) {
        progress.querySelector('.images-upload-progress__text').textContent = `Successfully uploaded ${successCount} image(s)`;
        setTimeout(() => {
            overlay.remove();
        }, 1500);
    } else {
        progress.querySelector('.images-upload-progress__text').textContent = `Uploaded ${successCount}, failed ${failCount}`;
        alert(`Upload complete:\n\nSuccess: ${successCount}\nFailed: ${failCount}\n\nErrors:\n${errors.join('\n')}`);
        progress.style.display = 'none';
    }
}
