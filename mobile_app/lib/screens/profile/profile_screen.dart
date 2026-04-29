import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';

class ProfileScreen extends StatelessWidget {
  final ApiService api;
  const ProfileScreen({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 28,
                        backgroundColor: Theme.of(context).colorScheme.primary,
                        child: Text(
                          (user?.fullName ?? 'U')
                              .trim()
                              .substring(0, 1)
                              .toUpperCase(),
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(user?.fullName ?? '—',
                                style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold)),
                            Text(user?.email ?? '—',
                                style: const TextStyle(color: Colors.grey)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 32),
                  _row('Phone', user?.phone ?? '—'),
                  _row('Role', user?.role ?? '—'),
                  _row('Verified', (user?.isVerified ?? false) ? 'Yes' : 'No'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.lock_outline),
                  title: const Text('Change password'),
                  onTap: () =>
                      _showChangePasswordDialog(context, api),
                ),
                const Divider(height: 0),
                ListTile(
                  leading: const Icon(Icons.logout, color: Colors.red),
                  title: const Text('Logout',
                      style: TextStyle(color: Colors.red)),
                  onTap: () async {
                    await context.read<AuthProvider>().logout();
                    if (context.mounted) {
                      Navigator.of(context).pushNamedAndRemoveUntil(
                          '/login', (_) => false);
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            SizedBox(
                width: 100,
                child:
                    Text(k, style: const TextStyle(color: Colors.grey))),
            Expanded(child: Text(v)),
          ],
        ),
      );

  void _showChangePasswordDialog(BuildContext context, ApiService api) {
    final cur = TextEditingController();
    final newP = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Change password'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: cur,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Current'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: newP,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'New (8+ chars)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              try {
                await api.changePassword(cur.text, newP.text);
                if (ctx.mounted) {
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Password updated')),
                  );
                }
              } catch (e) {
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    SnackBar(content: Text('Error: $e')),
                  );
                }
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
