/**
 * EXTRACTOR DE TOKENS GARMIN - Ejecutar en consola del navegador
 * 
 * Instrucciones:
 * 1. Abre https://connect.garmin.com (debes estar logueado)
 * 2. Presiona F12 para abrir DevTools
 * 3. Ve a la pestaña "Console"
 * 4. Pega TODO este código y presiona Enter
 * 5. Copia los JSON que aparecen
 * 6. Guarda en los archivos correspondientes
 */

(function() {
    console.log('%c🔍 EXTRACTOR DE TOKENS GARMIN', 'font-size: 20px; font-weight: bold; color: #00a9e0;');
    console.log('%cBuscando tokens en localStorage y cookies...', 'font-size: 14px; color: #666;');
    
    const results = {
        oauth1: null,
        oauth2: null,
        source: null
    };
    
    // 1. Buscar en localStorage
    const lsKeys = Object.keys(localStorage);
    const oauth1Key = lsKeys.find(k => k.includes('oauth1') || k.includes('OAUTH1'));
    const oauth2Key = lsKeys.find(k => k.includes('oauth2') || k.includes('OAUTH2') || k.includes('access_token'));
    
    if (oauth1Key) {
        try {
            results.oauth1 = JSON.parse(localStorage.getItem(oauth1Key));
            results.source = 'localStorage';
            console.log('✅ OAuth1 encontrado en localStorage:', oauth1Key);
        } catch(e) {
            results.oauth1 = localStorage.getItem(oauth1Key);
            results.source = 'localStorage';
        }
    }
    
    if (oauth2Key) {
        try {
            results.oauth2 = JSON.parse(localStorage.getItem(oauth2Key));
            console.log('✅ OAuth2 encontrado en localStorage:', oauth2Key);
        } catch(e) {
            results.oauth2 = localStorage.getItem(oauth2Key);
        }
    }
    
    // 2. Buscar en sessionStorage
    const ssKeys = Object.keys(sessionStorage);
    if (!results.oauth1) {
        const ssOauth1 = ssKeys.find(k => k.includes('oauth1') || k.includes('OAUTH1'));
        if (ssOauth1) {
            try {
                results.oauth1 = JSON.parse(sessionStorage.getItem(ssOauth1));
                results.source = 'sessionStorage';
            } catch(e) {
                results.oauth1 = sessionStorage.getItem(ssOauth1);
                results.source = 'sessionStorage';
            }
        }
    }
    
    if (!results.oauth2) {
        const ssOauth2 = ssKeys.find(k => k.includes('oauth2') || k.includes('OAUTH2') || k.includes('access_token'));
        if (ssOauth2) {
            try {
                results.oauth2 = JSON.parse(sessionStorage.getItem(ssOauth2));
            } catch(e) {
                results.oauth2 = sessionStorage.getItem(ssOauth2);
            }
        }
    }
    
    // 3. Buscar en cookies
    if (!results.oauth1 || !results.oauth2) {
        const cookies = document.cookie.split(';');
        console.log('🔍 Buscando en cookies...');
        
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            
            if (!results.oauth1 && (name.includes('oauth1') || name.includes('OAUTH1'))) {
                try {
                    results.oauth1 = JSON.parse(decodeURIComponent(value));
                    results.source = 'cookies';
                } catch(e) {
                    results.oauth1 = decodeURIComponent(value);
                    results.source = 'cookies';
                }
            }
            
            if (!results.oauth2 && (name.includes('oauth2') || name.includes('access_token'))) {
                try {
                    results.oauth2 = JSON.parse(decodeURIComponent(value));
                } catch(e) {
                    results.oauth2 = decodeURIComponent(value);
                }
            }
        }
    }
    
    // 4. Intentar extraer de la API de Garmin si hay sesión activa
    if (!results.oauth1 || !results.oauth2) {
        console.log('%c⚠️ No se encontraron tokens en storage. Intentando extraer de la sesión activa...', 'color: orange;');
        console.log('%cEspera un momento...', 'color: orange;');
        
        // Hacer una petición para obtener info del usuario (si hay sesión activa)
        fetch('https://connect.garmin.com/modern/proxy/userprofile-service/userprofile/personal-information', {
            credentials: 'include'
        })
        .then(r => {
            if (r.ok) {
                console.log('%c✅ Sesión activa confirmada', 'color: green; font-weight: bold;');
                return r.json();
            }
            throw new Error('No session');
        })
        .then(data => {
            console.log('%c👤 Usuario:', 'color: #00a9e0;', data.displayName || data.username || 'Unknown');
            console.log('%c💡 Para extraer los tokens necesitas usar el método de cookies manual.', 'color: orange;');
            console.log('%cInstrucciones abajo...', 'color: orange;');
        })
        .catch(() => {
            console.log('%c❌ No hay sesión activa detectada', 'color: red;');
        });
    }
    
    // Mostrar resultados
    console.log('\n' + '='.repeat(60));
    console.log('%c📋 RESULTADOS:', 'font-size: 16px; font-weight: bold; color: #00a9e0;');
    console.log('='.repeat(60));
    
    if (results.oauth1) {
        console.log('%c✅ OAUTH1_TOKEN:', 'font-weight: bold; color: green;');
        console.log(JSON.stringify(results.oauth1, null, 2));
        console.log('\n%cArchivo: oauth1_token.json', 'color: gray;');
    } else {
        console.log('%c❌ OAUTH1_TOKEN no encontrado', 'color: red;');
    }
    
    console.log('\n' + '-'.repeat(60));
    
    if (results.oauth2) {
        console.log('%c✅ OAUTH2_TOKEN:', 'font-weight: bold; color: green;');
        console.log(JSON.stringify(results.oauth2, null, 2));
        console.log('\n%cArchivo: oauth2_token.json', 'color: gray;');
    } else {
        console.log('%c❌ OAUTH2_TOKEN no encontrado', 'color: red;');
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('%c📁 PASOS PARA GUARDAR:', 'font-size: 14px; font-weight: bold;');
    console.log('1. Crea la carpeta: .garth/');
    console.log('2. Guarda el contenido de OAuth1 en: .garth/oauth1_token.json');
    console.log('3. Guarda el contenido de OAuth2 en: .garth/oauth2_token.json');
    console.log('='.repeat(60));
    
    return results;
})();
