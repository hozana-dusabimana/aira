class ApiConfig {
  // For Android emulator: 10.0.2.2 maps to host machine.
  // For iOS simulator / web / desktop: 127.0.0.1 works.
  // For a real phone on the same Wi-Fi: use the dev machine's LAN IP.
  static const String baseUrl = String.fromEnvironment(
    'AIRA_API_URL',
    defaultValue: 'http://192.168.1.67:8000',
  );

  static const String apiPrefix = '/api/v1';
  static String get apiBase => '$baseUrl$apiPrefix';
}
