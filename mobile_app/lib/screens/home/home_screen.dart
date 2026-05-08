import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/aira_logo.dart';
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
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard, color: AiraColors.primary),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history, color: AiraColors.primary),
            label: 'Reports',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            selectedIcon:
                Icon(Icons.notifications, color: AiraColors.primary),
            label: 'Alerts',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person, color: AiraColors.primary),
            label: 'Profile',
          ),
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
    final firstName = userName.split(' ').first;

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Brand header
          Row(
            children: [
              const AiraLogo(size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hello, $firstName 👋',
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: AiraColors.navy,
                      ),
                    ),
                    Text(
                      'Welcome back to AIRA',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: AiraColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                tooltip: 'Notifications',
                icon: const Icon(Icons.notifications_none,
                    color: AiraColors.navy),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => NotificationsScreen(api: api),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Hero CTA
          _ReportHeroCard(api: api),
          const SizedBox(height: 16),

          // Quick actions
          Row(
            children: [
              Expanded(
                child: _QuickAction(
                  icon: Icons.history,
                  label: 'My reports',
                  color: AiraColors.accent,
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => HistoryScreen(api: api),
                  )),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _QuickAction(
                  icon: Icons.shield_outlined,
                  label: 'Safety tips',
                  color: AiraColors.success,
                  onTap: () => _showTipsSheet(context),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // How AIRA helps
          const _InfoCard(
            icon: Icons.auto_awesome,
            title: 'How AIRA helps',
            body:
                'Snap a photo of any incident and AIRA uses AI to describe '
                'and classify it, then routes it to the nearest officers in '
                'real time.',
          ),
          const SizedBox(height: 24),

          Center(
            child: Text(
              'Powered by AI • Rwanda National Police',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 11.5),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  void _showTipsSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Reporting safely',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AiraColors.navy,
              ),
            ),
            const SizedBox(height: 12),
            _tip('Stay at a safe distance. Do not put yourself at risk to take a photo.'),
            _tip('Turn on your phone’s location so officers can find the scene fast.'),
            _tip('Add a short description if anything important is not visible in the photo.'),
            _tip('For emergencies, call 112 directly while submitting the report.'),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  Widget _tip(String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.check_circle,
                color: AiraColors.success, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(text, style: const TextStyle(height: 1.4))),
          ],
        ),
      );
}

class _ReportHeroCard extends StatelessWidget {
  final ApiService api;
  const _ReportHeroCard({required this.api});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AiraColors.primary, AiraColors.primaryDark],
        ),
        boxShadow: [
          BoxShadow(
            color: AiraColors.primary.withValues(alpha: 0.30),
            offset: const Offset(0, 12),
            blurRadius: 24,
          ),
        ],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.add_a_photo,
                    color: Colors.white, size: 24),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'Report an incident',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Snap a photo. We’ll handle the rest — AI verification, severity, dispatch.',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.85),
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: AiraColors.primary,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              icon: const Icon(Icons.camera_alt_outlined),
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
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _QuickAction({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AiraColors.surface,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AiraColors.navy,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String body;
  const _InfoCard({required this.icon, required this.title, required this.body});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: AiraColors.primary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: AiraColors.primary, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AiraColors.navy,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    body,
                    style: TextStyle(
                      color: Colors.grey.shade700,
                      fontSize: 13,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
