import 'package:flutter/material.dart';

import '../../config/api_config.dart';
import '../../models/incident.dart';

class IncidentResultScreen extends StatelessWidget {
  final Incident incident;
  const IncidentResultScreen({super.key, required this.incident});

  @override
  Widget build(BuildContext context) {
    final imageFullUrl = incident.imageUrl != null
        ? '${ApiConfig.baseUrl}${incident.imageUrl}'
        : null;
    return Scaffold(
      appBar: AppBar(title: const Text('Report submitted')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.green, size: 28),
              const SizedBox(width: 8),
              Text('Report #${incident.id} sent',
                  style: Theme.of(context).textTheme.titleLarge),
            ],
          ),
          const SizedBox(height: 16),
          if (imageFullUrl != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.network(imageFullUrl, fit: BoxFit.cover),
            ),
          const SizedBox(height: 16),
          _row('Status', incident.status),
          _row('Severity', incident.severityLevel),
          if (incident.incidentType != null)
            _row('Detected type', incident.incidentType!),
          const SizedBox(height: 16),
          if (incident.aiDescription != null) ...[
            const Text('AI description',
                style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(incident.aiDescription!,
                  style: const TextStyle(fontSize: 14)),
            ),
          ],
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Back to home'),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            SizedBox(
              width: 120,
              child: Text(label,
                  style: const TextStyle(color: Colors.grey, fontSize: 13)),
            ),
            Expanded(child: Text(value, style: const TextStyle(fontSize: 14))),
          ],
        ),
      );
}
