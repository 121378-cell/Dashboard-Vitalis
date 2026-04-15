// Extract Garmin tokens from browser after login
// Run this in browser console at https://connect.garmin.com

(function() {
    const oauth1 = localStorage.getItem('oauth1_token') || localStorage.getItem('oauth1');
    const oauth2 = localStorage.getItem('oauth2_token') || localStorage.getItem('oauth2') || localStorage.getItem('oauth_token');
    
    // Try sessionStorage too
    const oauth1s = sessionStorage.getItem('oauth1_token') || sessionStorage.getItem('oauth1');
    const oauth2s = sessionStorage.getItem('oauth2_token') || sessionStorage.getItem('oauth2') || sessionStorage.getItem('oauth_token');
    
    const result = {
        oauth1: oauth1 || oauth1s,
        oauth2: oauth2 || oauth2s,
        localStorage: Object.keys(localStorage).filter(k => k.includes('oauth') || k.includes('token')),
        sessionStorage: Object.keys(sessionStorage).filter(k => k.includes('oauth') || k.includes('token'))
    };
    
    console.log('=== GARMIN TOKENS ===');
    console.log(JSON.stringify(result, null, 2));
    
    // Also check cookies
    const cookies = document.cookie.split(';').filter(c => c.includes('GARMIN') || c.includes('SESSION') || c.includes('token'));
    console.log('=== RELEVANT COOKIES ===');
    cookies.forEach(c => console.log(c.trim()));
    
    return result;
})();
