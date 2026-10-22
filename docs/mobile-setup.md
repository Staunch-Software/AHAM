# Mobile app (Flutter) — setup, permissions, build

**Status (verified on Flutter 3.47.7 / Dart 3.13.5, Windows):** Drift code generation succeeds; `flutter analyze`
reports no issues; `flutter test` passes 27 tests (schema validation, sync engine against fakes, form widget tests,
local-database upgrade); `flutter build apk --debug` succeeds (168 MB debug APK; first build ~16 min incl. downloads).
`workmanager` had to move to ^0.10 (0.5.x no longer compiles on current Flutter).
**Verified on an Android 15 emulator:** Scenario B (offline end to end) and the review/correction scenario against the
real backend, covering real SQLite, secure-storage session restore offline, Dio sync API, GPS capture, resumable upload,
auto-sync, managed Type of person, feedback, correction and resubmission (see docs/testing.md).

**Look and feel:** the app uses the AHAM branding (logo, navy and gold, Inter font bundled for offline use); see
docs/design-system.md. The redesign was re-checked on the emulator with the offline and correction scenarios; the real
phone needs the new APK to show it.

**Updating a phone that already has the app:** this version changes the on-phone database from version 1 to 2 (review
feedback, corrections, multiple photos). Install the new APK over the old one (do not uninstall): pending reports,
drafts and photos are kept (checked by `test/migration_test.dart`; not yet tried on a real phone). Then open Forms once
while online so form version 4 and the Type of person list download.
```bash
flutter build apk --debug --dart-define=API_BASE_URL=http://<your-pc-ip>:8000
```
**Still not verified:** the system camera UI, real-device GPS, WorkManager background runs, process-kill recovery,
and iOS (never built; needs a Mac).

## One-time setup
Requires Flutter stable **>= 3.35** (uses `RadioGroup` and `DropdownButtonFormField.initialValue`). `pubspec.yaml`
uses caret ranges within each package's current major; `pubspec.lock` fixes the exact versions — commit it.
Android builds need JDK 17 and the Android SDK (`flutter config --android-sdk ... --jdk-dir ...`, accept licences).

```bash
cd mobile
flutter create --platforms=android,ios --org com.fieldsync --project-name fieldsync_mobile .   # generates android/ and ios/
flutter pub get
dart run build_runner build --delete-conflicting-outputs   # generates lib/database/database.g.dart (Drift)
flutter analyze
flutter test        # form_schema, sync_engine (fakes), form_view widget test
```
`flutter create .` keeps the existing `lib/` and `pubspec.yaml`; if it overwrites `lib/main.dart`, restore it from this repo.

## Run against the local backend
```bash
# Android emulator reaches the host as 10.0.2.2 (the default)
flutter run
# Physical device: use your computer's LAN IP, and run the API with --host 0.0.0.0
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000
```
Demo agent: `agent@fieldsync-demo.com` (password printed by `python -m app.seed`).

## Android (`android/app/src/main/AndroidManifest.xml`)
Inside `<manifest>`:
```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
```
Development over plain HTTP only: add `android:usesCleartextTraffic="true"` to `<application>` (remove for
production — use HTTPS). Set `minSdkVersion 23` in `android/app/build.gradle`. Background sync uses WorkManager
(no extra permission); Android batches periodic work, minimum interval 15 minutes, and may defer it (Doze, battery
saver). Foreground triggers are the primary path.

## iOS (`ios/Runner/Info.plist`)
```xml
<key>NSCameraUsageDescription</key>
<string>Take photos as evidence of your field visits.</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>Record where a field visit photo is taken and where a report is submitted.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>Choose an existing photo when the form allows it.</string>
<key>UIBackgroundModes</key>
<array><string>fetch</string><string>processing</string></array>
<key>BGTaskSchedulerPermittedIdentifiers</key>
<array><string>fieldsync.background_sync</string></array>
```
In `ios/Runner/AppDelegate.swift`, inside `didFinishLaunchingWithOptions`, before `return`:
```swift
WorkmanagerPlugin.registerBGProcessingTask(withIdentifier: "fieldsync.background_sync")
```
(plus `import workmanager`). iOS runs background tasks opportunistically — it may run rarely or never; do not
promise agents background delivery on iOS. Set the iOS deployment target to 13.0+ in Xcode.

**iOS build verification requires a Mac with Xcode** (`flutter build ios --no-codesign`, then device test
for camera/location/background). This has not been done.

## Behaviour notes
- Sign-in needs connectivity once; afterwards the cached profile and forms allow fully offline work.
- Signing out keeps unsynced reports on the device, tied to their owner; another user logging in will not
  sync them.
- Drafts autosave (500 ms debounce) and survive restarts. Submit performs one SQLite transaction (submission +
  outbox state + photo attachment + draft removal) before reporting "Saved on this device".
- Photo time/GPS are captured when the camera returns; submission time is taken the instant Submit is pressed
  and the GPS fix (max 8 s, configurable in `core/config.dart`) never blocks saving.
- Photos in app-private storage and the SQLite DB are **not encrypted at rest** (relies on OS sandbox/device
  encryption). Revisit if devices can be lost without a screen lock policy.
