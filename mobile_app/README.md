# AIRA mobile app (Flutter)

Citizen-facing mobile app for the AI Incident Reporting Application.

## Setup

```bash
flutter pub get
flutter run
```

## Android permissions

Add the following to `android/app/src/main/AndroidManifest.xml` inside the `<manifest>` tag (above `<application>`):

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
```

For Android 9+ (API 28+) cleartext HTTP, also add the `usesCleartextTraffic` attribute on `<application>` (only for the dev backend; remove in production):

```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

## iOS permissions

Add to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>AIRA needs the camera to capture incident photos.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>AIRA needs access to your photos so you can attach them to reports.</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>AIRA uses your location so police can respond at the right place.</string>
```

## API base URL

Defaults to `http://192.168.1.64:8000` (Android emulator host alias). Override at run time:

```bash
flutter run --dart-define=AIRA_API_URL=http://192.168.1.42:8000
```

## Default test account

| Email                | Password   |
| -------------------- | ---------- |
| citizen@example.com  | Citizen@1  |
