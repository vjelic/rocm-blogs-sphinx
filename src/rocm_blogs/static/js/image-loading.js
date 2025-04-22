/**
 * Image loading handler for ROCm Blogs
 * 
 * This script improves the lazy loading of images by adding a smooth transition
 * when images are loaded, preventing the white flash effect when scrolling.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Function to handle image loading
    function handleImageLoading() {
        // Get all lazy-loaded images
        const lazyImages = document.querySelectorAll('img[loading="lazy"], .sd-card-img-top');
        
        // Add loading class to all images initially
        lazyImages.forEach(img => {
            // Only add the class if the image is not already loaded
            if (!img.complete) {
                img.classList.add('loading');
            }
        });
        
        // Set up intersection observer for lazy loading
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // When the image loads, remove the loading class
                    const handleLoad = () => {
                        // Use setTimeout to create a smoother transition
                        setTimeout(() => {
                            img.classList.remove('loading');
                        }, 50);
                        img.removeEventListener('load', handleLoad);
                    };
                    
                    // If the image is already loaded, remove the loading class immediately
                    if (img.complete) {
                        img.classList.remove('loading');
                    } else {
                        img.addEventListener('load', handleLoad);
                    }
                    
                    // Stop observing the image
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '200px 0px', // Start loading images before they enter the viewport
            threshold: 0.01
        });
        
        // Observe all lazy-loaded images
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Run the image loading handler
    handleImageLoading();
    
    // Also run it after a short delay to catch any images added dynamically
    setTimeout(handleImageLoading, 500);
});
