# 📋 Guía para Extraer Tokens de Garmin Connect

## MÉTODO 1: Script Automático (Recomendado)

### Paso 1: Abrir Garmin Connect
1. Abre https://connect.garmin.com en tu navegador
2. **Asegúrate de estar logueado** (debes ver tu dashboard)
3. Presiona `F12` para abrir DevTools
4. Ve a la pestaña **Console** (Consola)

### Paso 2: Ejecutar Script
1. Abre el archivo `extract_garmin_tokens.js`
2. Copia TODO el contenido
3. Pégalo en la consola del navegador
4. Presiona Enter

### Paso 3: Copiar Resultados
- El script mostrará los tokens en formato JSON
- Copia cada token y guárdalo en el archivo correspondiente

---

## MÉTODO 2: Manual desde Cookies (Alternativa)

Si el script no encuentra los tokens, hazlo manual:

### Paso 1: Abrir DevTools
1. Ve a https://connect.garmin.com (logueado)
2. Presiona `F12`
3. Ve a **Application** (o **Aplicación**)

### Paso 2: Buscar Cookies
1. En el panel izquierdo: **Storage** → **Cookies** → https://connect.garmin.com
2. Busca cookies con estos nombres:
   - `OAUTH1_TOKEN` o `oauth1_token`
   - `OAUTH2_TOKEN` o `oauth2_token` o `ACCESS_TOKEN`

### Paso 3: Copiar Valores
1. Haz doble clic en el valor de cada cookie
2. Copia el contenido (es un JSON)
3. Crea los archivos:

```
.garth/
├── oauth1_token.json
└── oauth2_token.json
```

---

## MÉTODO 3: Via Network Requests

### Paso 1: Abrir Network Tab
1. `F12` → pestaña **Network** (Red)
2. Recarga la página (`F5`)

### Paso 2: Buscar Requests
Filtra por "token" o busca requests a:
- `userprofile-service`
- `activity-service`

### Paso 3: Inspeccionar Headers
1. Haz clic en cualquier request
2. Ve a **Headers** → **Request Headers**
3. Busca `Authorization: Bearer ...`
4. El token después de "Bearer" es tu token

---

## 💾 Formato de Archivos

### oauth1_token.json
```json
{
  "oauth_token": "tu_token_aqui",
  "oauth_token_secret": "tu_secret_aqui"
}
```

### oauth2_token.json
```json
{
  "access_token": "tu_access_token",
  "refresh_token": "tu_refresh_token",
  "expires_in": 3600,
  "scope": "..."
}
```

---

## ✅ Verificar que Funciona

Después de guardar los archivos:

```bash
cd backend
python -c "
import garth
from garminconnect import Garmin

garth.resume('.garth')
client = Garmin()
client.garth = garth.client
profile = client.get_user_profile()
print(f'✅ Conectado como: {profile.get(\"displayName\", \"Unknown\")}')
"
```

---

## ⚠️ Notas Importantes

- **No compartas estos tokens** - son como tu contraseña
- **Los tokens expiran** - si dejan de funcionar, repite el proceso
- **Borra los tokens** si dejas de usar la app
