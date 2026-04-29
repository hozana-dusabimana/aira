import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../models/incident.dart';
import '../../services/api_service.dart';
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
      appBar: AppBar(title: const Text('My reports')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Incident>>(
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
                  Center(child: Text('You have no reports yet.')),
                ],
              );
            }
            return ListView.builder(
              itemCount: list.length,
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

  Color _statusColor(String s) {
    switch (s) {
      case 'pending':
      case 'analyzing':
        return Colors.orange;
      case 'verified':
      case 'assigned':
      case 'in_progress':
        return Colors.blue;
      case 'resolved':
        return Colors.green;
      case 'rejected':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat.yMMMd().add_jm();
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _statusColor(incident.status).withValues(alpha: 0.18),
          child: Icon(Icons.flag_outlined,
              color: _statusColor(incident.status)),
        ),
        title: Text('Report #${incident.id}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${incident.incidentType ?? 'Type unknown'} • ${incident.severityLevel}'),
            Text(fmt.format(incident.createdAt),
                style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
        trailing: Text(
          incident.status,
          style: TextStyle(
            color: _statusColor(incident.status),
            fontWeight: FontWeight.bold,
          ),
        ),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => IncidentResultScreen(incident: incident),
        )),
      ),
    );
  }
}
