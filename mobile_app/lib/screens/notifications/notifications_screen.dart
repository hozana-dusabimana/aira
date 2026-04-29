import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../models/notification.dart';
import '../../services/api_service.dart';

class NotificationsScreen extends StatefulWidget {
  final ApiService api;
  const NotificationsScreen({super.key, required this.api});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<List<AppNotification>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.notifications();
  }

  Future<void> _refresh() async {
    setState(() => _future = widget.api.notifications());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat.yMMMd().add_jm();
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<AppNotification>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(child: Text('Error: ${snap.error}'));
            }
            final list = snap.data ?? [];
            if (list.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 200),
                  Center(child: Text('No notifications yet.')),
                ],
              );
            }
            return ListView.separated(
              itemCount: list.length,
              separatorBuilder: (_, __) => const Divider(height: 0),
              itemBuilder: (_, i) {
                final n = list[i];
                return ListTile(
                  leading: Icon(
                    n.isRead
                        ? Icons.notifications_none
                        : Icons.notifications_active,
                    color: n.isRead ? Colors.grey : Colors.blue,
                  ),
                  title: Text(
                    n.title,
                    style: TextStyle(
                      fontWeight:
                          n.isRead ? FontWeight.normal : FontWeight.bold,
                    ),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (n.message != null) Text(n.message!),
                      Text(fmt.format(n.createdAt),
                          style: const TextStyle(
                              fontSize: 12, color: Colors.grey)),
                    ],
                  ),
                  onTap: () async {
                    if (!n.isRead) {
                      await widget.api.markRead(n.id);
                      _refresh();
                    }
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }
}
