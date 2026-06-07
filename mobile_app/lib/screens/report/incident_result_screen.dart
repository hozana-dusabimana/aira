import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../config/theme.dart';
import '../../models/incident.dart';
import '../../services/api_service.dart';
import '../../widgets/status_chips.dart';

class IncidentResultScreen extends StatefulWidget {
  final Incident incident;
  final ApiService api;
  const IncidentResultScreen({
    super.key,
    required this.incident,
    required this.api,
  });

  @override
  State<IncidentResultScreen> createState() => _IncidentResultScreenState();
}

class _IncidentResultScreenState extends State<IncidentResultScreen> {
  // Poll while the backend runs AI analysis in the background.
  static const _pollInterval = Duration(seconds: 2);
  static const _maxPolls = 30; // ~60s safety cap

  late Incident _incident;
  Timer? _poll;
  int _polls = 0;
  bool _timedOut = false;
  // Set when polling gets a 404: the backend discarded the report as a
  // non-incident (the row is deleted), so we surface it as "not accepted".
  bool _discarded = false;

  @override
  void initState() {
    super.initState();
    _incident = widget.incident;
    if (_isAnalyzing) {
      _startPolling();
    }
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  bool get _isAnalyzing =>
      _incident.status == 'analyzing' || _incident.status == 'pending';

  bool get _isRejected => _incident.status == 'rejected' || _discarded;

  void _startPolling() {
    _poll?.cancel();
    _poll = Timer.periodic(_pollInterval, (_) => _tick());
  }

  Future<void> _tick() async {
    if (!mounted) return;
    if (_polls >= _maxPolls) {
      _poll?.cancel();
      setState(() => _timedOut = true);
      return;
    }
    _polls++;
    try {
      final updated = await widget.api.getIncident(_incident.id);
      if (!mounted) return;
      setState(() => _incident = updated);
      if (!_isAnalyzing) {
        _poll?.cancel();
      }
    } on DioException catch (e) {
      // A 404 means the backend discarded the report as a non-incident (the
      // row is deleted). Surface the rejection instead of polling to timeout.
      if (e.response?.statusCode == 404) {
        _poll?.cancel();
        if (!mounted) return;
        setState(() => _discarded = true);
      }
      // Other errors are transient — keep polling until the safety cap.
    } catch (_) {
      // Transient error — keep polling until the safety cap.
    }
  }

  Future<void> _openInMaps() async {
    final lat = _incident.latitude;
    final lng = _incident.longitude;
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
        title: Text(_isRejected ? 'Report not accepted' : 'Report submitted'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_isRejected)
            _buildRejectedHeader()
          else
            _buildSuccessHeader(),
          const SizedBox(height: 20),
          if (_isRejected) ...[
            _buildRejectedHelp(),
          ] else ...[
            _buildSummaryCard(dateFmt),
            if (_isAnalyzing) ...[
              const SizedBox(height: 16),
              _buildAnalyzingCard(),
            ] else if (_incident.aiDescription != null) ...[
              const SizedBox(height: 16),
              _buildDescriptionCard(),
            ],
            if (_incident.userDescription != null &&
                _incident.userDescription!.trim().isNotEmpty) ...[
              const SizedBox(height: 16),
              _buildCitizenNoteCard(),
            ],
            if (_incident.latitude != null &&
                _incident.longitude != null) ...[
              const SizedBox(height: 16),
              _buildLocationCard(),
            ],
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
                  'Report #${_incident.id} sent',
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

  Widget _buildRejectedHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AiraColors.danger.withValues(alpha: 0.10),
        border: Border.all(color: AiraColors.danger.withValues(alpha: 0.4)),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              color: AiraColors.danger,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.report_gmailerrorred,
                color: Colors.white, size: 26),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Report not accepted',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: AiraColors.navy,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'The photo could not be confirmed as a reportable incident, '
                  'so officers were not notified.',
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

  Widget _buildRejectedHelp() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'What to do',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: AiraColors.navy,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Please capture the accident, fire, or emergency scene clearly '
              'and submit again. Make sure the incident itself is visible in '
              'the photo.',
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

  Widget _buildSummaryCard(DateFormat fmt) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusChip(status: _incident.status),
                const SizedBox(width: 8),
                SeverityChip(severity: _incident.severityLevel),
                const Spacer(),
                Text(
                  fmt.format(_incident.createdAt),
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            _row(Icons.label_outline, 'Detected type', _incident.typeLabel),
            _row(Icons.fingerprint, 'Report ID', '#${_incident.id}'),
            _row(Icons.calendar_today_outlined, 'Updated',
                fmt.format(_incident.updatedAt)),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalyzingCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Analyzing your report…',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AiraColors.navy,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _timedOut
                        ? 'This is taking longer than usual. The AI summary will '
                            'appear in your reports history once ready.'
                        : 'The AI is reviewing your photo. The incident summary '
                            'will appear here shortly.',
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
              _incident.aiDescription!,
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
              _incident.userDescription!,
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
              '${_incident.latitude!.toStringAsFixed(5)}, ${_incident.longitude!.toStringAsFixed(5)}',
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
