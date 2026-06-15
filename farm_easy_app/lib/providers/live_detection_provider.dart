import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/app_constants.dart';
import '../models/disease_prediction_model.dart';
import '../services/farmeasy_api_service.dart';

class LiveDetectionProvider extends ChangeNotifier {
  LiveDetectionProvider({FarmEasyApiService? apiService})
    : _api = apiService ?? FarmEasyApiService();

  final FarmEasyApiService _api;

  CameraController? _cameraController;
  WebSocketChannel? _channel;
  StreamSubscription? _socketSubscription;
  Timer? _timer;
  DiseasePrediction? _latestPrediction;
  String? _error;
  bool _isInitializing = true;
  bool _isLive = false;
  bool _isCapturing = false;
  bool _disposed = false;
  int _frameCounter = 0;

  CameraController? get cameraController => _cameraController;
  DiseasePrediction? get latestPrediction => _latestPrediction;
  String? get error => _error;
  bool get isInitializing => _isInitializing;
  bool get isLive => _isLive;
  Uri get liveUri => AppConstants.wsUri(AppConstants.livePath);

  Future<void> initializeCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw StateError('No camera found on this device.');
      }

      final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );

      final controller = CameraController(
        backCamera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();

      _cameraController = controller;
      _error = null;
    } catch (error) {
      _error = error.toString();
    } finally {
      _isInitializing = false;
      _safeNotify();
    }
  }

  Future<void> startLive() async {
    final controller = _cameraController;
    if (controller == null || !controller.value.isInitialized || _isLive) {
      return;
    }

    try {
      final channel = _api.connectLiveDetection();
      _socketSubscription = channel.stream.listen(
        _handleSocketMessage,
        onError: (error) {
          _error = error.toString();
          _safeNotify();
        },
        onDone: () {
          if (_isLive) {
            _isLive = false;
            _error = 'Live connection closed.';
            _safeNotify();
          }
        },
      );

      _channel = channel;
      _isLive = true;
      _error = null;
      _latestPrediction = null;
      _safeNotify();

      await _sendFrame();
      _timer = Timer.periodic(
        AppConstants.liveFrameInterval,
        (_) => _sendFrame(),
      );
    } catch (error) {
      _error = error.toString();
      _safeNotify();
    }
  }

  Future<void> stopLive() async {
    _timer?.cancel();
    _timer = null;
    await _socketSubscription?.cancel();
    _socketSubscription = null;
    await _channel?.sink.close();
    _channel = null;
    _isLive = false;
    _safeNotify();
  }

  Future<void> _sendFrame() async {
    final controller = _cameraController;
    final channel = _channel;
    if (!_isLive ||
        _isCapturing ||
        controller == null ||
        channel == null ||
        !controller.value.isInitialized) {
      return;
    }

    _isCapturing = true;
    XFile? frame;
    try {
      frame = await controller.takePicture();
      final bytes = await frame.readAsBytes();
      _frameCounter += 1;
      channel.sink.add(
        _api.liveFramePayload(bytes, frameId: _frameCounter.toString()),
      );
    } catch (error) {
      _error = error.toString();
      _safeNotify();
    } finally {
      if (frame != null) {
        final file = File(frame.path);
        if (await file.exists()) {
          await file.delete();
        }
      }
      _isCapturing = false;
    }
  }

  void _handleSocketMessage(dynamic message) {
    try {
      final decoded = jsonDecode(message.toString());
      if (decoded is Map<String, dynamic>) {
        if (decoded['error'] != null) {
          _error = decoded['error'].toString();
          _safeNotify();
          return;
        }
        _latestPrediction = DiseasePrediction.fromJson(decoded);
        _error = null;
        _safeNotify();
      }
    } catch (error) {
      _error = error.toString();
      _safeNotify();
    }
  }

  void _safeNotify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _socketSubscription?.cancel();
    _channel?.sink.close();
    _cameraController?.dispose();
    _api.dispose();
    super.dispose();
  }
}
