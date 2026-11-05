# Mobile app (React Native, Expo) — setup, build, behaviour

The Sales Officer app lives in `mobile/` (Expo SDK 58, React Native 0.88, TypeScript, Expo Router). The previous Flutter
app is kept in `archive/mobile-flutter/` for reference only; it is not built or tested any more.

**App name / id:** "AHAM Sankalp", Android package `com.aham.sankalp`. It installs **beside** the old FieldSync app.
Before uninstalling the old app on a phone, open it once online so anything still waiting there is sent.

## Tools
Node 22, JDK 17 and the Android SDK (the same as for Flutter: set `JAVA_HOME` and `ANDROID_HOME`). No Expo account and no
EAS cloud build are needed: everything builds on the PC. iOS needs a Mac and has not been built.

```bash
cd mobile
npm ci
npm test            # Jest: phone rules, Entry ID, sync engine
npx tsc --noEmit    # type check
npx expo-doctor     # dependency and config check
```

## Build an APK
The API address is **baked in at build time** through `EXPO_PUBLIC_API_BASE_URL` (default `http://10.0.2.2:8000`, which is
the PC as seen from the Android emulator). For a phone on the same Wi-Fi, use the PC's IPv4 address (`ipconfig`).

```bash
cd mobile
npx expo prebuild --platform android --clean     # generates android/ from app.json (never edit android/ by hand)
cd android
# PowerShell:  $env:EXPO_PUBLIC_API_BASE_URL="http://192.168.1.20:8000"; .\gradlew.bat assembleRelease
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.20:8000 ./gradlew assembleRelease
```
**Changing the address later.** A Wi-Fi gives the PC a new address from time to time. An APK built for plain `http`
lets the user type the PC's current address under "Server" → **Change**, on the sign-in screen or the Me tab
(`src/components/ServerSetting.tsx`). The app checks `/health` at that address before using it and remembers it on the
phone; leaving the box blank goes back to the built-in address. An APK built for `https` (production) always uses its
own server and shows no Change link (`SERVER_EDITABLE` in `src/lib/config.ts`).

The APK is `mobile/android/app/build/outputs/apk/release/app-release.apk`. It contains the JavaScript, so it runs without a
dev server; it is signed with the development key (fine for testing, not for the Play Store). The first build downloads
Gradle and its dependencies and takes 15–30 minutes. Install on a connected phone with `adb install -r <apk>`.

For day-to-day development with fast refresh: `npx expo run:android` (builds a debug app and starts Metro).

**Windows: path too long.** Native C++ builds fail with `ninja: error: mkdir(...): No such file or directory`, because
the code generated for native modules (e.g. safe-area-context) sits deeper than 260 characters, and the SDK's default
CMake 3.22 ships Ninja 1.10, which ignores Windows long-path support. The fix: turn on Windows long paths (an
administrator setting: `LongPathsEnabled` = 1; it was already on here), install a newer CMake
(`sdkmanager "cmake;3.31.6"`, which brings Ninja 1.12) and point the build at it in `mobile/android/local.properties`:
```
cmake.dir=C\:\\dev\\android-sdk\\cmake\\3.31.6
```
(`local.properties` is machine-specific and never committed; write it again after `expo prebuild --clean`.) Also:
- `react-native-gesture-handler` and `react-native-reanimated` (installed only as peers of Expo Router; this app uses
  neither: it has no drawer and uses the native stack) are left out of autolinking in `package.json` (`expo.autolinking.exclude`).
  Their native code had the longest paths. If a future screen needs them, remove them from that list.
- The build runs from a short folder: copy `mobile/` without `node_modules` and `android` to `C:\sb`, run `npm ci` there
  and build as above (that is what we do). Adding `-PreactNativeArchitectures=arm64-v8a,x86_64` to the Gradle command builds
only for phones and the emulator, which is faster. Turning on Windows long-path support (an administrator setting) is
the other way out.

## Permissions (app.json)
Camera (evidence photos; no gallery access), precise location in the foreground only (Submit and photo positions; no
background location), internet. Microphone and media-library permissions are blocked. Plain HTTP is allowed
(`usesCleartextTraffic`) so development builds reach a PC; remove it for a production build that uses HTTPS.

## How it works
- **Sign in** with the Emp ID (or email) and password at the *mobile* portal; other roles are told which web portal to
  use. A temporary password must be replaced first. The refresh token is kept in the phone's secure storage; once signed
  in, the app opens offline with the cached profile.
- **New entry** (one per person met): category (6 fixed), CP sub-type for a Contact Point (list cached for offline use),
  name, mobile (validated live exactly like the server: 10 digits starting 6–9; Submit is blocked until valid),
  description, optional Keka photo time, up to 5 camera photos.
- **Submit**: the time is stamped the instant Submit is pressed, then a GPS fix is taken (at most 8 s; without a fix the
  entry is still saved, with the reason). The **Entry ID** (`<EmpID>-<YYYYMMDD>-<HHMMSS>`, IST) is shown at once. The entry,
  its photos and the cleared draft are saved in **one SQLite transaction**. The request body is stored as it will be
  sent, so syncing hours later never changes the time or place.
- **Each photo** keeps its own capture time and GPS (taken when the camera returns), separate from the entry's.
- **Sync** (`src/lib/syncEngine.ts`, tested with fakes): photos first (resumable upload, SHA-256 checked by the server),
  then the entry with the same idempotency key and byte-identical body on every retry. Backoff from 10 s up to 15 min.
  An entry is "Sent" only after the server's receipt. Triggers: app start, after Submit, network back, app returned to
  the front, every minute while open, and a background task (Android WorkManager, at most every 15 min).
- **Draft**: the form is saved on the phone as you type, so closing the app does not lose it.
- **My entries** merges what is on the phone with the server's view: call-centre status, RAG and the next action.
  **Today** shows the day's count against the targets (10 entries, 5 Lead/Prospect) and the numbers the call centre
  could not reach (to give to the BM).
- **Sign out** keeps unsent entries on the phone, tied to their owner; another person signing in never sends them.

## Not verified yet
The real phone (camera, GPS, background runs), iOS, and very large photo sets on a slow connection. Photo and database
files on the phone are protected by the OS sandbox, not encrypted by the app.
