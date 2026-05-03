// Citizen-side WebSocket client.
//
// Subscribes to `/ws/citizen?token=...` so the home / history / details
// screens can react to incident updates the moment the backend pushes them,
// without polling. Reconnects with exponential backoff. Streams parsed
// events via a broadcast stream other widgets can listen to.
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

import '../config/api_config.dart';

class RealtimeEvent {
  final String event;
  final String topic;
  final Map<String, dynamic> data;
  RealtimeEvent(this.event, this.topic, this.data);
}

class RealtimeService {
  static const _kAccessToken = 'aira_access_token';

  final _controller = StreamController<RealtimeEvent>.broadcast();
  WebSocketChannel? _channel;
  Timer? _reconnect;
  int _retry = 0;
  bool _closed = false;

  Stream<RealtimeEvent> get events => _controller.stream;

  Future<void> connect() async {
    if (_closed) return;
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_kAccessToken);
    if (token == null) return;

    final wsBase = ApiConfig.baseUrl
        .replaceFirst('http://', 'ws://')
        .replaceFirst('https://', 'wss://');
    final uri = Uri.parse('$wsBase/ws/citizen?token=$token');
    debugPrint('[aira.ws] connect $uri');

    try {
      final channel = WebSocketChannel.connect(uri);
      _channel = channel;
      channel.stream.listen(
        (raw) {
          try {
            final m = jsonDecode(raw as String) as Map<String, dynamic>;
            _controller.add(RealtimeEvent(
              m['event'] as String? ?? 'unknown',
              m['topic'] as String? ?? '',
              (m['data'] as Map?)?.cast<String, dynamic>() ?? {},
            ));
          } catch (e) {
            debugPrint('[aira.ws] parse error: $e');
          }
        },
        onDone: () {
          debugPrint('[aira.ws] closed (code=${channel.closeCode})');
          _scheduleReconnect();
        },
        onError: (e) {
          debugPrint('[aira.ws] error: $e');
          _scheduleReconnect();
        },
        cancelOnError: true,
      );
      _retry = 0;
    } catch (e) {
      debugPrint('[aira.ws] connect failed: $e');
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_closed) return;
    final delayMs = (500 * (1 << (_retry < 6 ? _retry : 6))).clamp(500, 30000);
    _retry++;
    _reconnect?.cancel();
    _reconnect = Timer(Duration(milliseconds: delayMs), connect);
  }

  Future<void> dispose() async {
    _closed = true;
    _reconnect?.cancel();
    await _channel?.sink.close(ws_status.normalClosure);
    await _controller.close();
  }
}
