document.addEventListener('DOMContentLoaded', function() {
  if (window.performance) {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    console.log('Page load time:', pageLoadTime + 'ms');
  }

  function loadScriptsAsync() {
    const scripts = document.querySelectorAll('script[defer-load]');
    
    scripts.forEach(function(script) {
      const newScript = document.createElement('script');
      
      if (script.src) {
        newScript.src = script.src;
      } else {
        newScript.textContent = script.textContent;
      }

      Array.from(script.attributes).forEach(attr => {
        if (attr.name !== 'defer-load') {
          newScript.setAttribute(attr.name, attr.value);
        }
      });

      script.parentNode.replaceChild(newScript, script);
    });
  }

  if (window.requestIdleCallback) {
    requestIdleCallback(loadScriptsAsync);
  } else {
    setTimeout(loadScriptsAsync, 1000);
  }

  window.addEventListener('scroll', function() {
  }, { passive: true });
});
