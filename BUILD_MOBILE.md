# Build Mobile Android - Vitalis

Guía para compilar APK debug de forma reproducible en Windows PowerShell.

## Requisitos

- Node.js >= 18
- Android SDK con JDK 21 (`$env:USERPROFILE\AndroidSDK`)
- `ANDROID_HOME` configurado (el script lo configura automáticamente)

## Comando de Build

```powershell
# Build completo (web + android)
npm run build:android

# O usar script directamente
powershell -ExecutionPolicy Bypass -File .\scripts\build-android.ps1

# Con opciones
.\scripts\build-android.ps1 -Clean        # Limpia build anterior
.\scripts\build-android.ps1 -Install      # Instala APK tras compilar
.\scripts\build-android.ps1 -Clean -Install
```

## Qué hace el script

1. **Aplica fixes automáticos** a `capacitor-health`:
   - Elimina `dataOriginsFilter` (API cambió en Health Connect 1.2.0)
   - Mueve `hasPermission()` dentro de corrutina (suspend function)
   - Actualiza `proguard-android.txt` → `proguard-android-optimize.txt`

2. **Build web**: `npm run build` (Vite)

3. **Sync Capacitor**: `npx cap sync android`

4. **Compila APK**: `./gradlew assembleDebug`

5. **Output**: `android/app/build/outputs/apk/debug/app-debug.apk`

## Solución de problemas

### Error: `dataOriginsFilter`
```
No parameter with name 'dataOriginsFilter' found
```
**Fix**: El script aplica automáticamente. Si falla, ejecutar:
```powershell
git checkout node_modules/capacitor-health
npm run build:android
```

### Error: `hasPermission` suspend function
```
Suspend function can only be called from a coroutine
```
**Fix**: El script aplica automáticamente.

### Error: `proguard-android.txt`
```
getDefaultProguardFile('proguard-android.txt') is no longer supported
```
**Fix**: El script aplica automáticamente.

## Persistencia de fixes

Los fixes se aplican **cada vez que se ejecuta el build script**. No requieren modificar `node_modules` permanentemente.

Si necesitas que los fixes sobrevivan a `npm install`, el script los reaplicará automáticamente.

## Archivos modificados en este flujo

- `android/variables.gradle` - minSdkVersion=26 (requerido por Health Connect)
- `android/app/capacitor.build.gradle` - dependencias
- `android/capacitor.settings.gradle` - includes de plugins

## Rama de trabajo

Trabaja siempre en una rama feature:
```bash
git checkout -b feature/mobile-<descripcion>
```

## Entrega final requiere

- [ ] Archivos modificados listados
- [ ] Causa raíz documentada
- [ ] Comandos con estado reportados
- [ ] Commit hash referenciado
- [ ] PR título y cuerpo preparados
- [ ] Confirmación: fix sobrevive a `npm install`
