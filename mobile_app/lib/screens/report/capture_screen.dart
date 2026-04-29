import 'dart:io';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

import '../../models/incident.dart';
import '../../services/api_service.dart';
import 'incident_result_screen.dart';

class CaptureScreen extends StatefulWidget {
  final ApiService api;
  const CaptureScreen({super.key, required this.api});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  File? _image;
  String _severity = 'medium';
  final _descCtl = TextEditingController();
  bool _busy = false;
  String? _error;
  Position? _position;

  Future<void> _pick(ImageSource src) async {
    final picker = ImagePicker();
    final x = await picker.pickImage(source: src, imageQuality: 85);
    if (x != null) {
      setState(() => _image = File(x.path));
    }
  }

  Future<void> _resolveLocation() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return;
      LocationPermission p = await Geolocator.checkPermission();
      if (p == LocationPermission.denied) {
        p = await Geolocator.requestPermission();
      }
      if (p == LocationPermission.denied || p == LocationPermission.deniedForever) {
        return;
      }
      _position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      if (mounted) setState(() {});
    } catch (_) {
      // Submit will work without location.
    }
  }

  @override
  void initState() {
    super.initState();
    _resolveLocation();
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
      final Incident incident = await widget.api.submitIncident(
        image: _image!,
        userDescription: _descCtl.text.trim().isEmpty ? null : _descCtl.text.trim(),
        latitude: _position?.latitude,
        longitude: _position?.longitude,
        severity: _severity,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => IncidentResultScreen(incident: incident),
        ),
      );
    } catch (e) {
      setState(() => _error = 'Submission failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New report')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: ListView(
          children: [
            if (_image == null)
              AspectRatio(
                aspectRatio: 4 / 3,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.grey[200],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Center(
                    child: Icon(Icons.image_outlined, size: 60, color: Colors.grey),
                  ),
                ),
              )
            else
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(_image!, fit: BoxFit.cover),
              ),
            const SizedBox(height: 12),
            Row(
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
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.photo_library_outlined),
                    label: const Text('Gallery'),
                    onPressed: () => _pick(ImageSource.gallery),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _descCtl,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Optional description',
                hintText: 'Anything the AI may not see in the photo…',
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _severity,
              decoration: const InputDecoration(labelText: 'Severity'),
              items: const [
                DropdownMenuItem(value: 'low', child: Text('Low')),
                DropdownMenuItem(value: 'medium', child: Text('Medium')),
                DropdownMenuItem(value: 'high', child: Text('High')),
                DropdownMenuItem(value: 'critical', child: Text('Critical')),
              ],
              onChanged: (v) => setState(() => _severity = v ?? 'medium'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.location_on_outlined, size: 16),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    _position == null
                        ? 'Location: not available'
                        : 'Location: '
                            '${_position!.latitude.toStringAsFixed(5)}, '
                            '${_position!.longitude.toStringAsFixed(5)}',
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
                TextButton(
                  onPressed: _resolveLocation,
                  child: const Text('Refresh'),
                ),
              ],
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _busy ? null : _submit,
              icon: _busy
                  ? const SizedBox(
                      width: 18, height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.send),
              label: Text(_busy ? 'Submitting…' : 'Submit report'),
            ),
          ],
        ),
      ),
    );
  }
}
