import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/theme.dart';
import '../../models/notification.dart';
import '../../services/api_service.dart';
import '../../widgets/loaders.dart';

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

  IconData _iconFor(String type) {
    final t = type.toLowerCase();
    if (t.contains('approved')) return Icons.verified_outlined;
    if (t.contains('reported')) return Icons.report_gmailerrorred_outlined;
    if (t.contains('assigned')) return Icons.local_police;
    if (t.contains('resolved')) return Icons.check_circle_outline;
    if (t.contains('rejected')) return Icons.cancel_outlined;
    if (t.contains('message')) return Icons.message_outlined;
    if (t.contains('critical') || t.contains('emergency')) {
      return Icons.warning_amber_rounded;
    }
    return Icons.notifications_active_outlined;
  }

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat.yMMMd().add_jm();
    return Scaffold(
      appBar: AppBar(title: const Text('Alerts & updates')),
      body: RefreshIndicator(
        color: AiraColors.primary,
        onRefresh: _refresh,
        child: FutureBuilder<List<AppNotification>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const AiraInlineLoader(label: 'Checking for updates...');
            }
            if (snap.hasError) {
              return AiraEmptyState(
                icon: Icons.error_outline,
                title: 'Could not load notifications',
                subtitle: '${snap.error}',
                action: ElevatedButton.icon(
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try again'),
                ),
              );
            }
            final list = snap.data ?? [];
            if (list.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 80),
                  AiraEmptyState(
                    icon: Icons.notifications_off_outlined,
                    title: 'You’re all caught up',
                    subtitle:
                        'New alerts about your reports will show up here.',
                  ),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final n = list[i];
                final color = n.isRead ? AiraColors.textMuted : AiraColors.primary;
                return Card(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () async {
                      if (!n.isRead) {
                        await widget.api.markRead(n.id);
                        _refresh();
                      }
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 38,
                            height: 38,
                            decoration: BoxDecoration(
                              color: color.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(_iconFor(n.type), color: color, size: 20),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        n.title,
                                        style: TextStyle(
                                          fontWeight: n.isRead
                                              ? FontWeight.w500
                                              : FontWeight.w700,
                                          color: AiraColors.navy,
                                        ),
                                      ),
                                    ),
                                    if (!n.isRead)
                                      Container(
                                        width: 8,
                                        height: 8,
                                        decoration: const BoxDecoration(
                                          color: AiraColors.primary,
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                  ],
                                ),
                                if (n.message != null) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    n.message!,
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: Colors.grey.shade700,
                                      height: 1.35,
                                    ),
                                  ),
                                ],
                                const SizedBox(height: 6),
                                Text(
                                  fmt.format(n.createdAt),
                                  style: TextStyle(
                                    fontSize: 11.5,
                                    color: Colors.grey.shade500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
