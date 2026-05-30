class ApiConfig {
  // Defaults to the production API. Override for local development with:
  //   flutter run --dart-define=AIRA_API_URL=http://10.0.2.2:8000   (Android emulator)
  //   flutter run --dart-define=AIRA_API_URL=http://<LAN-IP>:8000   (real phone on Wi-Fi)
  static const String baseUrl = String.fromEnvironment(
    'AIRA_API_URL',
    defaultValue: 'https://api-aira.isiri.rw',
  );

  static const String apiPrefix = '/api/v1';
  static String get apiBase => '$baseUrl$apiPrefix';
}
