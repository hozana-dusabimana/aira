import 'package:flutter/foundation.dart';

import '../models/user.dart';
import '../services/api_service.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService api;
  User? _user;
  bool _loading = true;

  AuthProvider(this.api) {
    _restore();
  }

  User? get user => _user;
  bool get loading => _loading;
  bool get isLoggedIn => _user != null;

  Future<void> _restore() async {
    final has = await api.hasValidSession();
    if (has) {
      try {
        _user = await api.getMe();
      } catch (_) {
        await api.logout();
      }
    }
    _loading = false;
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    await api.login(email, password);
    _user = await api.getMe();
    notifyListeners();
  }

  Future<void> register({
    required String fullName,
    required String email,
    required String password,
    String? phone,
  }) async {
    await api.register(
        fullName: fullName, email: email, password: password, phone: phone);
    _user = await api.getMe();
    notifyListeners();
  }

  Future<void> logout() async {
    await api.logout();
    _user = null;
    notifyListeners();
  }
}
