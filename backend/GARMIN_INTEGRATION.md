# Integración con Garmin

## Configuración inicial

1. Copia el archivo `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edita el archivo `.env` y agrega tus credenciales de Garmin:
   ```
   GARMIN_EMAIL=tu_email@example.com
   GARMIN_PASSWORD=tu_contraseña
   ```

## Scripts disponibles

### Probar conexión con Garmin
```bash
cd backend
python run_garmin_test.py
```

### Probar conexión con delay (para evitar rate limiting)
```bash
cd backend
python run_garmin_test_with_delay.py
```

### Limpiar sesiones de Garmin
```bash
cd backend
python clear_garmin_sessions.py
```

## Errores comunes y soluciones

### Error 429 - Too Many Requests
Este error ocurre cuando se han realizado demasiadas solicitudes de inicio de sesión en poco tiempo.

**Soluciones:**
1. Espera 15-30 minutos antes de intentar conectarte nuevamente
2. Usa el script `clear_garmin_sessions.py` para eliminar sesiones antiguas
3. Considera usar OAuth en lugar de credenciales directas

### FileNotFoundError: oauth1_token.json
Este error ocurre cuando los archivos de token no existen o están corruptos.

**Solución:**
Ejecuta el script `clear_garmin_sessions.py` para eliminar sesiones antiguas e intenta conectarte nuevamente.

## Mejores prácticas

1. **Evita solicitudes frecuentes** a la API de Garmin
2. **Reutiliza las sesiones** cuando sea posible
3. **Implementa manejo de errores** apropiado para rate limiting
4. **Guarda tokens de sesión** para evitar iniciar sesión en cada solicitud
5. **Usa OAuth** para una integración más estable y segura

## Estructura del directorio de sesiones

Las sesiones de Garmin se almacenan en el directorio `.garth` dentro del backend:
```
backend/
├── .garth/
│   ├── oauth1_token.json
│   ├── oauth2_token.json
│   └── ...
```

## Documentación oficial

- [Garmin Connect API](https://developer.garmin.com/)
- [garminconnect-python](https://github.com/cyqsimon/garminconnect-python)