import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../config/theme.dart';
import '../../models/incident.dart';
import '../../services/api_service.dart';
import '../../widgets/loaders.dart';
import '../../widgets/location_prompt.dart';
import 'incident_result_screen.dart';

class CaptureScreen extends StatefulWidget {
  final ApiService api;
  const CaptureScreen({super.key, required this.api});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  File? _image;
  // Manual severity + description are commented out: the AI generates both
  // from the photo, so reporters no longer enter them. Restore to re-enable.
  // String _severity = 'medium';
  // final _descCtl = TextEditingController();
  bool _busy = false;
  bool _resolvingLocation = false;
  String? _error;
  LocationStatus _locStatus = const LocationStatus(issue: LocationIssue.serviceOff);

  @override
  void initState() {
    super.initState();
    _refreshLocation();
  }

  @override
  void dispose() {
    // _descCtl.dispose();
    super.dispose();
  }

  Future<void> _pick(ImageSource src) async {
    try {
      final picker = ImagePicker();
      final x = await picker.pickImage(source: src, imageQuality: 85);
      if (x != null) {
        setState(() => _image = File(x.path));
      }
    } catch (e) {
      setState(() => _error = 'Could not load image: $e');
    }
  }

  Future<void> _refreshLocation() async {
    setState(() => _resolvingLocation = true);
    final status = await resolveLocationStatus(fetch: true);
    if (!mounted) return;
    setState(() {
      _locStatus = status;
      _resolvingLocation = false;
    });
  }

  Future<void> _submit() async {
    if (_image == null) {
      setState(() => _error = 'Please attach a photo first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final pos = _locStatus.position;
      final Incident incident = await widget.api.submitIncident(
        image: _image!,
        // Manual description + severity removed; AI generates both.
        // userDescription:
        //     _descCtl.text.trim().isEmpty ? null : _descCtl.text.trim(),
        latitude: pos?.latitude,
        longitude: pos?.longitude,
        // severity: _severity,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) =>
              IncidentResultScreen(incident: incident, api: widget.api),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() => _error = apiErrorMessage(e, fallback: 'Submission failed. Please try again.'));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('New incident report'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
        ),
      ),
      body: Stack(
        children: [
          AbsorbPointer(
            absorbing: _busy,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                _buildPhotoCard(),
                const SizedBox(height: 12),
                _buildPickerButtons(),
                const SizedBox(height: 20),
                _buildLocationSection(),
                // Manual description + severity inputs are disabled; the AI
                // generates both from the photo. Restore to re-enable.
                // const SizedBox(height: 20),
                // _buildDescriptionField(),
                // const SizedBox(height: 16),
                // _buildSeveritySelector(),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  _buildErrorBanner(),
                ],
                const SizedBox(height: 24),
                _buildSubmitButton(),
                const SizedBox(height: 20),
                _buildSubmitHelper(),
              ],
            ),
          ),
          if (_busy) _buildSubmittingOverlay(),
        ],
      ),
    );
  }

  // ---------------- Sections ----------------

  Widget _buildPhotoCard() {
    return AspectRatio(
      aspectRatio: 4 / 3,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: AiraColors.surfaceMuted,
          border: Border.all(color: Colors.grey.shade300, width: 1),
        ),
        clipBehavior: Clip.antiAlias,
        child: _image != null
            ? Stack(
                fit: StackFit.expand,
                children: [
                  Image.file(_image!, fit: BoxFit.cover),
                  Positioned(
                    top: 8,
                    right: 8,
                    child: Material(
                      color: Colors.black54,
                      shape: const CircleBorder(),
                      child: IconButton(
                        icon: const Icon(Icons.close, color: Colors.white),
                        onPressed: () => setState(() => _image = null),
                      ),
                    ),
                  ),
                ],
              )
            : Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        color: AiraColors.primary.withValues(alpha: 0.10),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.add_a_photo_outlined,
                        size: 30,
                        color: AiraColors.primary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Attach a photo of the scene',
                      style: TextStyle(
                        color: AiraColors.navy,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'AI will describe and classify it automatically',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildPickerButtons() {
    // Two sources: live Camera, or an existing photo from the Gallery. The
    // gallery option lets reporters attach a photo that was already taken (and
    // lets the app be tested with downloaded sample incident images) — the app
    // no longer forces a freshly-captured camera shot.
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Camera'),
            onPressed: () => _pick(ImageSource.camera),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: OutlinedButton.icon(
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('Gallery'),
            onPressed: () => _pick(ImageSource.gallery),
          ),
        ),
      ],
    );
  }

  Widget _buildLocationSection() {
    if (_locStatus.isOk && _locStatus.position != null) {
      final p = _locStatus.position!;
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AiraColors.success.withValues(alpha: 0.08),
          border: Border.all(color: AiraColors.success.withValues(alpha: 0.4)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: AiraColors.success.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.location_on,
                  color: AiraColors.success, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Scene location captured',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AiraColors.navy,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${p.latitude.toStringAsFixed(5)}, ${p.longitude.toStringAsFixed(5)}'
                    '   ±${p.accuracy.toStringAsFixed(0)}m',
                    style: TextStyle(
                      color: Colors.grey.shade700,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: 'Refresh',
              icon: _resolvingLocation
                  ? const AiraButtonSpinner(color: AiraColors.primary)
                  : const Icon(Icons.refresh, color: AiraColors.primary),
              onPressed: _resolvingLocation ? null : _refreshLocation,
            ),
          ],
        ),
      );
    }

    if (_resolvingLocation) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AiraColors.surfaceMuted,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: const Row(
          children: [
            AiraButtonSpinner(color: AiraColors.primary),
            SizedBox(width: 12),
            Text('Locating you...',
                style: TextStyle(color: AiraColors.navy)),
          ],
        ),
      );
    }

    return LocationDisabledBanner(
      issue: _locStatus.issue,
      onResolved: _refreshLocation,
    );
  }

  // Disabled: AI now generates the description and severity from the photo.
  /*
  Widget _buildDescriptionField() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Tell us what happened',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: AiraColors.navy,
            fontSize: 14,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _descCtl,
          maxLines: 4,
          decoration: const InputDecoration(
            hintText:
                'Briefly describe the incident — anything the AI may not see in the photo (optional).',
          ),
        ),
      ],
    );
  }

  Widget _buildSeveritySelector() {
    const levels = [
      ('low', 'Low'),
      ('medium', 'Medium'),
      ('high', 'High'),
      ('critical', 'Critical'),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'How serious is it?',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: AiraColors.navy,
            fontSize: 14,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: levels.map((entry) {
            final value = entry.$1;
            final label = entry.$2;
            final selected = _severity == value;
            final color = severityColor(value);
            return ChoiceChip(
              selected: selected,
              showCheckmark: false,
              label: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(label),
                ],
              ),
              selectedColor: color.withValues(alpha: 0.15),
              labelStyle: TextStyle(
                color: selected ? color : Colors.grey.shade800,
                fontWeight: FontWeight.w600,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(999),
                side: BorderSide(
                  color: selected ? color : Colors.grey.shade300,
                ),
              ),
              onSelected: (_) => setState(() => _severity = value),
            );
          }).toList(),
        ),
      ],
    );
  }
  */

  Widget _buildErrorBanner() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AiraColors.danger.withValues(alpha: 0.08),
        border: Border.all(color: AiraColors.danger.withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline, color: AiraColors.danger, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _error!,
              style: const TextStyle(color: AiraColors.danger, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSubmitButton() {
    final disabled = _image == null;
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: disabled || _busy ? null : _submit,
        icon: _busy
            ? const AiraButtonSpinner()
            : const Icon(Icons.send),
        label: Text(_busy ? 'Submitting...' : 'Submit incident report'),
      ),
    );
  }

  Widget _buildSubmitHelper() {
    if (_image == null) {
      return Center(
        child: Text(
          'Add a photo to enable submission.',
          style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
        ),
      );
    }
    if (!_locStatus.isOk) {
      return Center(
        child: Text(
          'You can still submit without location, but officers may not be able '
          'to find the exact scene.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
        ),
      );
    }
    return const SizedBox.shrink();
  }

  Widget _buildSubmittingOverlay() {
    return Positioned.fill(
      child: Container(
        color: Colors.black.withValues(alpha: 0.45),
        child: const Center(
          child: AiraInlineLoader(label: 'Sending report and analysing image...'),
        ),
      ),
    );
  }
}
