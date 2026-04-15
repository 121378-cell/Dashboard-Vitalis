/**
 * EXTRACTOR DE COOKIES GARMIN
 * Ejecutar en consola de https://connect.garmin.com
 */

console.log('%c🔍 Buscando tokens en cookies...', 'font-size: 18px; font-weight: bold; color: #00a9e0;');

// Obtener todas las cookies
const allCookies = document.cookie.split(';').map(c => {
    const parts = c.trim().split('=');
    return {
        name: parts[0],
        value: decodeURIComponent(parts.slice(1).join('='))
    };
});

console.log(`\nCookies encontradas: ${allCookies.length}`);
console.log('Nombres:', allCookies.map(c => c.name).join(', '));

// Buscar tokens
const oauth1 = allCookies.find(c => 
    c.name.toLowerCase().includes('oauth1') || 
    c.name.toLowerCase().includes('oauth_token')
);

const oauth2 = allCookies.find(c => 
    c.name.toLowerCase().includes('oauth2') || 
    c.name.toLowerCase().includes('access_token') ||
    c.name.toLowerCase().includes('refresh_token')
);

const sessionId = allCookies.find(c => 
    c.name.toLowerCase().includes('session') ||
    c.name.toLowerCase().includes('sid') ||
    c.name.toLowerCase().includes('SESSION')
);

const jwt = allCookies.find(c => 
    c.name.toLowerCase().includes('jwt') ||
    c.name.toLowerCase().includes('token')
);

console.log('\n' + '='.repeat(60));

if (oauth1) {
    console.log('%c✅ OAUTH1 encontrado:', 'color: green; font-weight: bold;');
    console.log('Name:', oauth1.name);
    console.log('Value:', oauth1.value.substring(0, 100) + '...');
    try {
        const parsed = JSON.parse(oauth1.value);
        console.log('Parsed:', JSON.stringify(parsed, null, 2));
    } catch(e) {
        console.log('No es JSON válido');
    }
} else {
    console.log('%c❌ OAUTH1 no encontrado', 'color: red;');
}

console.log('\n' + '-'.repeat(60));

if (oauth2) {
    console.log('%c✅ OAUTH2 encontrado:', 'color: green; font-weight: bold;');
    console.log('Name:', oauth2.name);
    console.log('Value:', oauth2.value.substring(0, 100) + '...');
    try {
        const parsed = JSON.parse(oauth2.value);
        console.log('Parsed:', JSON.stringify(parsed, null, 2));
    } catch(e) {
        console.log('No es JSON válido');
    }
} else {
    console.log('%c❌ OAUTH2 no encontrado', 'color: red;');
}

console.log('\n' + '-'.repeat(60));

if (sessionId) {
    console.log('%c📍 Session ID encontrado:', 'color: orange;');
    console.log('Name:', sessionId.name);
    console.log('Value:', sessionId.value.substring(0, 50) + '...');
}

if (jwt) {
    console.log('%c📍 JWT Token encontrado:', 'color: orange;');
    console.log('Name:', jwt.name);
    console.log('Value:', jwt.value.substring(0, 100) + '...');
}

console.log('\n' + '='.repeat(60));
console.log('%c🔍 INSPECCIÓN COMPLETA DE COOKIES:', 'font-weight: bold;');
console.log('='.repeat(60));

allCookies.forEach(c => {
    const lowerName = c.name.toLowerCase();
    if (lowerName.includes('auth') || 
        lowerName.includes('token') || 
        lowerName.includes('session') ||
        lowerName.includes('oauth') ||
        lowerName.includes('sid') ||
        lowerName.includes('jwt') ||
        lowerName.includes('garmin')) {
        console.log(`\n%c${c.name}:`, 'color: #00a9e0; font-weight: bold;');
        console.log(c.value.substring(0, 200));
    }
});

// Método alternativo: Intentar extraer de la API
console.log('\n' + '='.repeat(60));
console.log('%c🔄 Intentando extraer desde API...', 'color: orange;');

fetch('https://connect.garmin.com/user-info', {
    credentials: 'include'
})
.then(r => {
    console.log('Status:', r.status);
    // Intentar leer headers de autorización
    const auth = r.headers.get('authorization');
    if (auth) {
        console.log('%c✅ Authorization header:', 'color: green;', auth);
    }
    return r.text();
})
.then(text => {
    console.log('Response preview:', text.substring(0, 500));
})
.catch(err => {
    console.log('Error:', err);
});

console.log('\n' + '='.repeat(60));
console.log('%c💡 CONCLUSIÓN:', 'font-weight: bold;');
console.log('Si no hay tokens visibles, Garmin usa session cookies para autenticación.');
console.log('Necesitamos usar un método diferente.');
console.log('='.repeat(60));
