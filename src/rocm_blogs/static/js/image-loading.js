document.addEventListener('DOMContentLoaded', function() {

    function handleImageLoading() {
        const lazyImages = document.querySelectorAll('img[loading="lazy"], .sd-card-img-top');

        lazyImages.forEach(img => {
            if (!img.complete) {
                img.classList.add('loading');
            }
        });

        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;

                    const handleLoad = () => {
                        setTimeout(() => {
                            img.classList.remove('loading');
                        }, 50);
                        img.removeEventListener('load', handleLoad);
                    };

                    if (img.complete) {
                        img.classList.remove('loading');
                    } else {
                        img.addEventListener('load', handleLoad);
                    }

                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '200px 0px',
            threshold: 0.01
        });

        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    }

    handleImageLoading();

    setTimeout(handleImageLoading, 500);
});
