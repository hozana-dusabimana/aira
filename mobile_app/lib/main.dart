import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config/theme.dart';
import 'providers/auth_provider.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/home/home_screen.dart';
import 'services/api_service.dart';
import 'services/push_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = await ApiService.create();
  // Push notifications are best-effort; never block app start on them.
  unawaited(PushService.init(api: api).catchError((Object e) {
    debugPrint('[aira] push init failed: $e');
  }));
  runApp(AiraApp(api: api));
}

class AiraApp extends StatelessWidget {
  final ApiService api;
  const AiraApp({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthProvider(api),
      child: Consumer<AuthProvider>(
        builder: (_, auth, __) => MaterialApp(
          title: 'AIRA',
          theme: buildAppTheme(),
          debugShowCheckedModeBanner: false,
          home: auth.loading
              ? const _Splash()
              : auth.isLoggedIn
                  ? HomeScreen(api: api)
                  : LoginScreen(api: api),
          routes: {
            '/login': (_) => LoginScreen(api: api),
            '/register': (_) => RegisterScreen(api: api),
            '/home': (_) => HomeScreen(api: api),
          },
        ),
      ),
    );
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
