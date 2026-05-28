import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../config/theme.dart';
import '../../models/incident.dart';
import '../../widgets/status_chips.dart';

class IncidentResultScreen extends StatelessWidget {
  final Incident incident;
  const IncidentResultScreen({super.key, required this.incident});

  Future<void> _openInMaps() async {
    final lat = incident.latitude;
    final lng = incident.longitude;
    if (lat == null || lng == null) return;
    final uri = Uri.parse(
      'https://www.google.com/maps/search/?api=1&query=$lat,$lng',
    );
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat.yMMMd().add_jm();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Report submitted'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildSuccessHeader(),
          const SizedBox(height: 20),
          _buildSummaryCard(dateFmt),
          if (incident.aiDescription != null) ...[
            const SizedBox(height: 16),
            _buildDescriptionCard(),
          ],
          if (incident.userDescription != null &&
              incident.userDescription!.trim().isNotEmpty) ...[
            const SizedBox(height: 16),
            _buildCitizenNoteCard(),
          ],
          if (incident.latitude != null && incident.longitude != null) ...[
            const SizedBox(height: 16),
            _buildLocationCard(),
          ],
          const SizedBox(height: 28),
          _buildBackButton(context),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  // ---------- sections ----------

  Widget _buildSuccessHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AiraColors.success.withValues(alpha: 0.10),
        border: Border.all(color: AiraColors.success.withValues(alpha: 0.4)),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              color: AiraColors.success,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.check, color: Colors.white, size: 26),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Report #${incident.id} sent',
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: AiraColors.navy,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Officers have been notified. You can track the status from your reports history.',
                  style: TextStyle(
                    color: Colors.grey.shade700,
                    fontSize: 12.5,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(DateFormat fmt) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusChip(status: incident.status),
                const SizedBox(width: 8),
                SeverityChip(severity: incident.severityLevel),
                const Spacer(),
                Text(
                  fmt.format(incident.createdAt),
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            _row(Icons.label_outline, 'Detected type', incident.typeLabel),
            _row(Icons.fingerprint, 'Report ID', '#${incident.id}'),
            _row(Icons.calendar_today_outlined, 'Updated',
                fmt.format(incident.updatedAt)),
          ],
        ),
      ),
    );
  }

  Widget _buildDescriptionCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.auto_awesome, color: AiraColors.primary, size: 18),
                SizedBox(width: 6),
                Text(
                  'AI incident summary',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: AiraColors.navy,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              incident.aiDescription!,
              style: TextStyle(
                fontSize: 14,
                height: 1.5,
                color: Colors.grey.shade800,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCitizenNoteCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.format_quote, color: AiraColors.accent, size: 18),
                SizedBox(width: 6),
                Text(
                  'Your description',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: AiraColors.navy,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              incident.userDescription!,
              style: TextStyle(
                fontSize: 14,
                height: 1.5,
                color: Colors.grey.shade800,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLocationCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.location_on, color: AiraColors.primary, size: 18),
                SizedBox(width: 6),
                Text(
                  'Scene location',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: AiraColors.navy,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${incident.latitude!.toStringAsFixed(5)}, ${incident.longitude!.toStringAsFixed(5)}',
              style: TextStyle(color: Colors.grey.shade800, fontSize: 13),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              icon: const Icon(Icons.map_outlined, size: 18),
              label: const Text('Open in Maps'),
              onPressed: _openInMaps,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBackButton(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        icon: const Icon(Icons.home_outlined),
        label: const Text('Back to home'),
        onPressed: () => Navigator.of(context).pop(),
      ),
    );
  }

  Widget _row(IconData icon, String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Icon(icon, size: 16, color: Colors.grey.shade600),
            const SizedBox(width: 8),
            SizedBox(
              width: 110,
              child: Text(
                label,
                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              ),
            ),
            Expanded(
              child: Text(
                value,
                style: const TextStyle(fontSize: 14, color: AiraColors.navy),
              ),
            ),
          ],
        ),
      );
}
