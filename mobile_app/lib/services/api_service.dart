import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/api_config.dart';
import '../models/incident.dart';
import '../models/notification.dart';
import '../models/user.dart';

void _log(String msg) => debugPrint('[aira.api] $msg');

class ApiService {
  final Dio _dio;
  static const _kAccessToken = 'aira_access_token';
  static const _kRefreshToken = 'aira_refresh_token';

  ApiService._(this._dio);

  static Future<ApiService> create() async {
    _log('init: baseUrl=${ApiConfig.baseUrl}  apiBase=${ApiConfig.apiBase}');
    final dio = Dio(BaseOptions(
      baseUrl: ApiConfig.apiBase,
      connectTimeout: const Duration(seconds: 15),
      sendTimeout: const Duration(seconds: 90),
      receiveTimeout: const Duration(seconds: 90),
    ));

    final prefs = await SharedPreferences.getInstance();
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = prefs.getString(_kAccessToken);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        _log('-> ${options.method} ${options.uri}');
        handler.next(options);
      },
      onResponse: (res, handler) {
        _log('<- ${res.statusCode} ${res.requestOptions.uri}');
        handler.next(res);
      },
      onError: (e, handler) async {
        _log(
          'xx ${e.requestOptions.method} ${e.requestOptions.uri} '
          'type=${e.type} status=${e.response?.statusCode} '
          'msg=${e.message} body=${e.response?.data}',
        );
        if (e.response?.statusCode == 401) {
          final refreshed = await _tryRefresh(dio, prefs);
          if (refreshed) {
            final clone = await dio.fetch(e.requestOptions);
            return handler.resolve(clone);
          }
        }
        handler.next(e);
      },
    ));

    return ApiService._(dio);
  }

  static Future<bool> _tryRefresh(Dio dio, SharedPreferences prefs) async {
    final rt = prefs.getString(_kRefreshToken);
    if (rt == null) return false;
    try {
      final res = await Dio(BaseOptions(baseUrl: ApiConfig.apiBase))
          .post('/auth/refresh', data: {'refresh_token': rt});
      await prefs.setString(_kAccessToken, res.data['access_token']);
      await prefs.setString(_kRefreshToken, res.data['refresh_token']);
      return true;
    } catch (_) {
      await prefs.remove(_kAccessToken);
      await prefs.remove(_kRefreshToken);
      return false;
    }
  }

  // ---------- Auth ----------
  Future<Map<String, dynamic>> login(String email, String password) async {
    _log('login start email=$email url=${ApiConfig.apiBase}/auth/login');
    final stopwatch = Stopwatch()..start();
    try {
      final res = await _dio.post('/auth/login',
          data: {'email': email, 'password': password});
      _log('login ok in ${stopwatch.elapsedMilliseconds}ms');
      await _saveTokens(res.data);
      return res.data as Map<String, dynamic>;
    } on DioException catch (e) {
      _log(
        'login fail in ${stopwatch.elapsedMilliseconds}ms '
        'type=${e.type} status=${e.response?.statusCode} '
        'msg=${e.message} body=${e.response?.data} '
        'url=${e.requestOptions.uri}',
      );
      rethrow;
    } catch (e, st) {
      _log('login crash in ${stopwatch.elapsedMilliseconds}ms err=$e\n$st');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> register({
    required String fullName,
    required String email,
    required String password,
    String? phone,
    String? nationalId,
  }) async {
    final res = await _dio.post('/auth/register', data: {
      'full_name': fullName,
      'email': email,
      'password': password,
      if (phone != null) 'phone': phone,
      if (nationalId != null) 'national_id': nationalId,
    });
    await _saveTokens(res.data);
    return res.data as Map<String, dynamic>;
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kAccessToken);
    await prefs.remove(_kRefreshToken);
  }

  Future<bool> hasValidSession() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kAccessToken) != null;
  }

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kAccessToken, data['access_token'] as String);
    await prefs.setString(_kRefreshToken, data['refresh_token'] as String);
  }

  // ---------- Profile ----------
  Future<User> getMe() async {
    final res = await _dio.get('/users/me');
    return User.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> changePassword(String current, String newPwd) async {
    await _dio.post('/users/me/change-password',
        data: {'current_password': current, 'new_password': newPwd});
  }

  // ---------- Incidents ----------
  Future<Incident> submitIncident({
    required File image,
    String? userDescription,
    double? latitude,
    double? longitude,
    String severity = 'medium',
  }) async {
    final form = FormData.fromMap({
      'image': await MultipartFile.fromFile(image.path,
          filename: image.uri.pathSegments.last),
      if (userDescription != null) 'user_description': userDescription,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      'severity_level': severity,
      'run_ai': true,
    });
    final res = await _dio.post('/incidents/', data: form);
    return Incident.fromJson(res.data as Map<String, dynamic>);
  }

  Future<List<Incident>> myIncidents() async {
    final res = await _dio.get('/users/me/incidents');
    return (res.data as List)
        .map((e) => Incident.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Incident> getIncident(int id) async {
    final res = await _dio.get('/incidents/$id');
    return Incident.fromJson(res.data as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> getMessages(int id) async {
    final res = await _dio.get('/incidents/$id/messages');
    return (res.data as List).cast<Map<String, dynamic>>();
  }

  Future<void> sendMessage(int id, String text) async {
    await _dio.post('/incidents/$id/messages', data: {'message': text});
  }

  // ---------- Notifications ----------
  Future<List<AppNotification>> notifications() async {
    final res = await _dio.get('/users/me/notifications');
    return (res.data as List)
        .map((e) => AppNotification.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> markRead(int id) async {
    await _dio.put('/notifications/$id/read');
  }

  Future<void> registerDeviceToken(String token, String platform) async {
    await _dio.post('/notifications/register-device',
        data: {'token': token, 'platform': platform});
  }
}
