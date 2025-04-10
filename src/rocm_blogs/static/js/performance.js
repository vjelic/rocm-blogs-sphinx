/**
 * Simplified performance optimization script for ROCm Blogs
 * 
 * This script handles:
 * 1. Optimizing script loading
 * 2. Minimizing main thread work
 * 3. Performance metrics logging
 */

document.addEventListener('DOMContentLoaded', function() {

  // Performance metrics logging
  if (window.performance) {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    console.log('Page load time:', pageLoadTime + 'ms');
  }

  // Optimize script loading
  function loadScriptsAsync() {

    const scripts = document.querySelectorAll('script[defer-load]');
    
    scripts.forEach(function(script) {
      const newScript = document.createElement('script');
      
      if (script.src) {
        newScript.src = script.src;
      } else {
        newScript.textContent = script.textContent;
      }
      
      // Copy all attributes except 'defer-load'
      Array.from(script.attributes).forEach(attr => {
        if (attr.name !== 'defer-load') {
          newScript.setAttribute(attr.name, attr.value);
        }
      });
      
      // Replace the original script with the new one
      script.parentNode.replaceChild(newScript, script);
    });
  }
  
  // Load non-critical scripts after page load
  if (window.requestIdleCallback) {
    requestIdleCallback(loadScriptsAsync);
  } else {
    setTimeout(loadScriptsAsync, 1000);
  }

  window.addEventListener('scroll', function() {
  }, { passive: true });
});
