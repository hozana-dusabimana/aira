// Firebase Cloud Messaging integration.
//
// On supported platforms (Android/iOS), this:
//   1. Initializes Firebase
//   2. Requests notification permission
//   3. Fetches the FCM device token and forwards it to the AIRA backend
//   4. Listens for token refreshes and re-registers
//   5. Subscribes to foreground/background message handlers and shows the
//      message body via flutter_local_notifications
//
// On platforms where Firebase isn't supported (web in tests, desktop), init
// quietly no-ops so the rest of the app keeps working.
import 'dart:io' show Platform;

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'api_service.dart';

void _log(String msg) => debugPrint('[aira.push] $msg');

class PushService {
  PushService._();

  static final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();

  static const AndroidNotificationChannel _channel = AndroidNotificationChannel(
    'aira_default',
    'AIRA notifications',
    description: 'Incident updates and messages from RNP.',
    importance: Importance.high,
  );

  static bool _initialized = false;

  /// Top-level handler for messages received while the app is in the
  /// background or terminated. Must be a top-level or static function.
  @pragma('vm:entry-point')
  static Future<void> _onBackgroundMessage(RemoteMessage message) async {
    _log('background message: ${message.messageId} data=${message.data}');
  }

  static Future<void> init({required ApiService api}) async {
    if (_initialized) return;
    if (kIsWeb || !(Platform.isAndroid || Platform.isIOS)) {
      _log('Skipping push init (unsupported platform)');
      return;
    }
    try {
      await Firebase.initializeApp();
    } catch (e) {
      _log('Firebase init failed: $e (push disabled)');
      return;
    }

    final messaging = FirebaseMessaging.instance;

    final settings = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    _log('Permission: ${settings.authorizationStatus}');

    // Local notifications (used to render foreground messages)
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosInit = DarwinInitializationSettings();
    await _local.initialize(
      const InitializationSettings(android: androidInit, iOS: iosInit),
    );
    await _local
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_channel);

    FirebaseMessaging.onBackgroundMessage(_onBackgroundMessage);

    FirebaseMessaging.onMessage.listen((RemoteMessage m) {
      _log('foreground message: ${m.messageId}');
      final notif = m.notification;
      if (notif == null) return;
      _local.show(
        m.hashCode,
        notif.title,
        notif.body,
        NotificationDetails(
          android: AndroidNotificationDetails(
            _channel.id,
            _channel.name,
            channelDescription: _channel.description,
            importance: Importance.high,
            priority: Priority.high,
          ),
          iOS: const DarwinNotificationDetails(),
        ),
      );
    });

    final token = await messaging.getToken();
    if (token != null) {
      await _registerWithBackend(api, token);
    }
    messaging.onTokenRefresh.listen((t) => _registerWithBackend(api, t));

    _initialized = true;
  }

  static Future<void> _registerWithBackend(ApiService api, String token) async {
    final platform = Platform.isAndroid ? 'android' : 'ios';
    try {
      await api.registerDeviceToken(token, platform);
      _log('Registered device token (platform=$platform)');
    } catch (e) {
      _log('Failed to register device token: $e');
    }
  }
}
