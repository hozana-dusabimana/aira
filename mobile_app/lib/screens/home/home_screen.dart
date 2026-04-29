import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../notifications/notifications_screen.dart';
import '../profile/profile_screen.dart';
import '../report/capture_screen.dart';
import '../reports_history/history_screen.dart';

class HomeScreen extends StatefulWidget {
  final ApiService api;
  const HomeScreen({super.key, required this.api});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final tabs = [
      _HomeTab(api: widget.api, userName: auth.user?.fullName ?? 'Citizen'),
      HistoryScreen(api: widget.api),
      NotificationsScreen(api: widget.api),
      ProfileScreen(api: widget.api),
    ];
    return Scaffold(
      body: tabs[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.history), label: 'History'),
          NavigationDestination(icon: Icon(Icons.notifications_outlined), label: 'Alerts'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}

class _HomeTab extends StatelessWidget {
  final ApiService api;
  final String userName;
  const _HomeTab({required this.api, required this.userName});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 12),
            Text('Hello, $userName 👋',
                style: theme.textTheme.headlineSmall),
            const SizedBox(height: 4),
            Text(
              'Spotted something that needs the police? Take a photo and submit it — '
              'AI will describe and classify the incident automatically.',
              style: theme.textTheme.bodyMedium?.copyWith(color: Colors.grey[700]),
            ),
            const SizedBox(height: 32),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.camera_alt_outlined,
                            size: 32,
                            color: theme.colorScheme.primary),
                        const SizedBox(width: 12),
                        Text('Report an incident',
                            style: theme.textTheme.titleLarge),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      "Snap a photo. We'll handle the rest.",
                      style: theme.textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.add_a_photo_outlined),
                        label: const Text('Report now'),
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => CaptureScreen(api: api),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const Spacer(),
            Center(
              child: Text(
                'Powered by AI • Rwanda National Police',
                style: TextStyle(color: Colors.grey[600], fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
