import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/theme.dart';
import '../../models/incident.dart';
import '../../services/api_service.dart';
import '../../widgets/loaders.dart';
import '../../widgets/status_chips.dart';
import '../report/incident_result_screen.dart';

class HistoryScreen extends StatefulWidget {
  final ApiService api;
  const HistoryScreen({super.key, required this.api});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<List<Incident>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.myIncidents();
  }

  Future<void> _refresh() async {
    setState(() => _future = widget.api.myIncidents());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My reports'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AiraColors.primary,
        onRefresh: _refresh,
        child: FutureBuilder<List<Incident>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const AiraInlineLoader(label: 'Loading your reports...');
            }
            if (snap.hasError) {
              return AiraEmptyState(
                icon: Icons.error_outline,
                title: 'Could not load reports',
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
                    icon: Icons.inbox_outlined,
                    title: 'No reports yet',
                    subtitle: 'Your submitted incidents will appear here.',
                  ),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _IncidentTile(incident: list[i]),
            );
          },
        ),
      ),
    );
  }
}

class _IncidentTile extends StatelessWidget {
  final Incident incident;
  const _IncidentTile({required this.incident});

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat.yMMMd().add_jm();
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => IncidentResultScreen(incident: incident),
        )),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: severityColor(incident.severityLevel)
                      .withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.flag_outlined,
                  color: severityColor(incident.severityLevel),
                  size: 22,
                ),
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
                            incident.incidentType ?? 'Incident',
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              color: AiraColors.navy,
                              fontSize: 15,
                            ),
                          ),
                        ),
                        Text(
                          '#${incident.id}',
                          style: TextStyle(
                            color: Colors.grey.shade500,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        StatusChip(status: incident.status, dense: true),
                        SeverityChip(severity: incident.severityLevel, dense: true),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      fmt.format(incident.createdAt),
                      style: TextStyle(
                        fontSize: 11.5,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AiraColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}
