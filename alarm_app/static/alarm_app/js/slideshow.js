/**
 * Slideshow functionality for news images
 * 
 * Displays images in fullscreen mode with automatic cycling
 */

class Slideshow {
    constructor(images, interval = 5000) {
        this.images = images; // Array of image URLs
        this.interval = interval; // Milliseconds between slides
        this.currentIndex = 0;
        this.intervalId = null;
        this.container = null;
        this.isFullscreen = false;
    }
    
    /**
     * Create and show the slideshow container
     */
    start() {
        // Create container
        this.container = document.createElement('div');
        this.container.id = 'slideshow-container';
        this.container.className = 'slideshow-fullscreen';
        
        // Create image element
        this.imageElement = document.createElement('img');
        this.imageElement.className = 'slideshow-image';
        this.container.appendChild(this.imageElement);
        
        // Create controls
        const controls = this.createControls();
        this.container.appendChild(controls);
        
        // Add to body
        document.body.appendChild(this.container);
        
        // Show first image
        this.showImage(0);
        
        // Start auto-advance
        this.startAutoAdvance();
        
        // Enter fullscreen
        this.enterFullscreen();
        
        // Setup keyboard controls
        this.setupKeyboardControls();
    }
    
    /**
     * Create control buttons
     */
    createControls() {
        const controls = document.createElement('div');
        controls.className = 'slideshow-controls';
        
        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.innerHTML = '&#10094;';
        prevBtn.className = 'slideshow-btn prev';
        prevBtn.onclick = () => this.previous();
        controls.appendChild(prevBtn);
        
        // Counter
        this.counter = document.createElement('div');
        this.counter.className = 'slideshow-counter';
        controls.appendChild(this.counter);
        
        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.innerHTML = '&#10095;';
        nextBtn.className = 'slideshow-btn next';
        nextBtn.onclick = () => this.next();
        controls.appendChild(nextBtn);
        
        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&times;';
        closeBtn.className = 'slideshow-btn close';
        closeBtn.onclick = () => this.stop();
        controls.appendChild(closeBtn);
        
        return controls;
    }
    
    /**
     * Show image at specific index
     */
    showImage(index) {
        if (index < 0) {
            index = this.images.length - 1;
        } else if (index >= this.images.length) {
            index = 0;
        }
        
        this.currentIndex = index;
        this.imageElement.src = this.images[index];
        
        // Update counter
        if (this.counter) {
            this.counter.textContent = `${index + 1} / ${this.images.length}`;
        }
    }
    
    /**
     * Show next image
     */
    next() {
        this.showImage(this.currentIndex + 1);
        this.resetAutoAdvance();
    }
    
    /**
     * Show previous image
     */
    previous() {
        this.showImage(this.currentIndex - 1);
        this.resetAutoAdvance();
    }
    
    /**
     * Start automatic advancement
     */
    startAutoAdvance() {
        this.intervalId = setInterval(() => {
            this.next();
        }, this.interval);
    }
    
    /**
     * Reset auto-advance timer (when user manually navigates)
     */
    resetAutoAdvance() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
        this.startAutoAdvance();
    }
    
    /**
     * Enter fullscreen mode
     */
    enterFullscreen() {
        const elem = this.container;
        
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        }
        
        this.isFullscreen = true;
    }
    
    /**
     * Exit fullscreen mode
     */
    exitFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        
        this.isFullscreen = false;
    }
    
    /**
     * Setup keyboard controls
     */
    setupKeyboardControls() {
        this.keyHandler = (e) => {
            switch(e.key) {
                case 'ArrowLeft':
                    this.previous();
                    break;
                case 'ArrowRight':
                    this.next();
                    break;
                case 'Escape':
                    this.stop();
                    break;
                case ' ':
                    // Space bar toggles auto-advance
                    if (this.intervalId) {
                        clearInterval(this.intervalId);
                        this.intervalId = null;
                    } else {
                        this.startAutoAdvance();
                    }
                    e.preventDefault();
                    break;
            }
        };
        
        document.addEventListener('keydown', this.keyHandler);
    }
    
    /**
     * Stop and clean up the slideshow
     */
    stop() {
        // Clear interval
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
        
        // Remove keyboard handler
        if (this.keyHandler) {
            document.removeEventListener('keydown', this.keyHandler);
        }
        
        // Exit fullscreen
        if (this.isFullscreen) {
            this.exitFullscreen();
        }
        
        // Remove container
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
    }
}


/**
 * Utility function to start a slideshow
 * 
 * @param {Array} images - Array of image URLs
 * @param {Number} interval - Milliseconds between slides (default: 5000)
 * @returns {Slideshow} The slideshow instance
 */
function startSlideshow(images, interval = 5000) {
    const slideshow = new Slideshow(images, interval);
    slideshow.start();
    return slideshow;
}


/**
 * Auto-start slideshow if images are present on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page that should auto-start slideshow
    const autoStartElement = document.getElementById('slideshow-data');
    
    if (autoStartElement) {
        const images = JSON.parse(autoStartElement.dataset.images || '[]');
        const interval = parseInt(autoStartElement.dataset.interval || '5000');
        
        if (images.length > 0) {
            startSlideshow(images, interval);
        }
    }
});
