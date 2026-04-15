// Extract all possible Garmin tokens from browser
(function() {
    console.log('=== EXTRACTING ALL GARMIN TOKENS ===\n');
    
    // 1. LocalStorage deep search
    console.log('1. LOCALSTORAGE:');
    const lsKeys = Object.keys(localStorage);
    console.log('All keys:', lsKeys);
    lsKeys.forEach(key => {
        try {
            const value = localStorage.getItem(key);
            if (value && (value.includes('oauth') || value.includes('token') || value.length > 100)) {
                console.log(`  ${key}:`, value.substring(0, 100) + '...');
            }
        } catch(e) {}
    });
    
    // 2. SessionStorage
    console.log('\n2. SESSIONSTORAGE:');
    const ssKeys = Object.keys(sessionStorage);
    console.log('All keys:', ssKeys);
    ssKeys.forEach(key => {
        try {
            const value = sessionStorage.getItem(key);
            if (value) {
                console.log(`  ${key}:`, value.substring(0, 100) + '...');
            }
        } catch(e) {}
    });
    
    // 3. Document cookies
    console.log('\n3. COOKIES:');
    const cookies = document.cookie.split(';');
    cookies.forEach(cookie => {
        const c = cookie.trim();
        if (c) {
            const name = c.split('=')[0];
            const value = c.split('=')[1];
            if (name.toLowerCase().includes('garmin') || 
                name.toLowerCase().includes('session') ||
                name.toLowerCase().includes('token') ||
                name.toLowerCase().includes('oauth') ||
                value.length > 50) {
                console.log(`  ${name}:`, value.substring(0, 50) + '...');
            }
        }
    });
    
    // 4. Window/global objects
    console.log('\n4. WINDOW OBJECTS:');
    ['GARMIN', 'OAUTH', 'TOKEN', 'SESSION', 'user', 'profile'].forEach(key => {
        if (window[key]) {
            console.log(`  window.${key}:`, typeof window[key]);
        }
    });
    
    // 5. IndexedDB check
    console.log('\n5. INDEXEDDB DATABASES:');
    if (window.indexedDB) {
        indexedDB.databases().then(dbs => {
            console.log('  Databases:', dbs.map(db => db.name));
        }).catch(e => console.log('  Cannot list DBs'));
    }
    
    return 'Check console output above';
})();
