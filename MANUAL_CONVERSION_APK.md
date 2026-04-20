# 📱 Manual paso a paso: Conversión de VITALIS a APK

Este manual describe el proceso completo para generar APKs (debug y release) desde este repositorio.

---

## 1) Requisitos previos

Instala y verifica:

1. **Node.js + npm**
2. **Java JDK** (recomendado JDK 21)
3. **Android Studio** con:
   - Android SDK
   - Build Tools
   - Platform Tools
4. Variables de entorno:
   - `JAVA_HOME`
   - `ANDROID_HOME` o `ANDROID_SDK_ROOT`
   - `PATH` con `platform-tools` y `cmdline-tools`

---

## 2) Instalar dependencias del proyecto

Desde la raíz del repositorio:

```bash
npm install
```

---

## 3) Compilar frontend (assets web)

```bash
npm run build
```

Esto genera la carpeta `dist/` que luego se empaqueta dentro del proyecto Android.

---

## 4) Sincronizar Capacitor con Android

```bash
npx cap sync android
```

Este comando:
- Copia los assets web (`dist`) al proyecto Android
- Actualiza plugins nativos de Capacitor

> Atajo equivalente definido en scripts: `npm run cap:sync`.

---

## 5) Generar APK DEBUG

```bash
cd android
./gradlew assembleDebug
```

APK generado en:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 6) Abrir en Android Studio (opcional)

```bash
npx cap open android
```

Luego en Android Studio:

- **Build > Build Bundle(s) / APK(s) > Build APK(s)**

---

## 7) Generar APK RELEASE (firmado)

### 7.1 Crear keystore (solo la primera vez)

```bash
keytool -genkey -v -keystore vitalis-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias vitalis
```

### 7.2 Configurar firma en Gradle

Editar `android/app/build.gradle` y añadir:

- `signingConfigs { release { ... } }`
- `buildTypes { release { signingConfig signingConfigs.release ... } }`

### 7.3 Compilar release

```bash
cd android
./gradlew assembleRelease
```

APK generado en:

```text
android/app/build/outputs/apk/release/app-release.apk
```

---

## 8) Flujo recomendado (rápido)

```bash
npm install
npm run build
npx cap sync android
cd android
./gradlew assembleDebug
```

---

## 9) Solución de problemas

### Error descargando Gradle/plugin (proxy/red)

Si falla el build con errores de descarga (Gradle Wrapper o plugins):

1. Revisar proxy en `~/.gradle/gradle.properties`:

```properties
systemProp.http.proxyHost=...
systemProp.http.proxyPort=...
systemProp.https.proxyHost=...
systemProp.https.proxyPort=...
```

2. Verificar conectividad a:
   - `https://services.gradle.org/`
   - Gradle Plugin Portal / Maven Central

3. Si estás en red corporativa, probar una red sin restricciones.

### Comando `./gradlew` sin permisos

```bash
chmod +x android/gradlew
```

---

## 10) Verificación final antes de distribuir

- La app abre correctamente en dispositivo/emulador
- No hay errores de consola críticos
- Login/chat/sync básicos funcionan
- El backend configurado para entorno productivo
- APK firmado si se va a publicar

---

**Listo.** Con estos pasos deberías poder convertir VITALIS a APK de forma repetible.
