import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/app_constants.dart';
import '../models/disease_prediction_model.dart';

class FarmEasyApiException implements Exception {
  final String message;
  final int? statusCode;

  FarmEasyApiException(this.message, {this.statusCode});

  @override
  String toString() {
    if (statusCode == null) return message;
    return '$message ($statusCode)';
  }
}

class FarmEasyApiService {
  FarmEasyApiService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<Map<String, dynamic>> health() async {
    final response = await _client
        .get(AppConstants.apiUri(AppConstants.healthPath))
        .timeout(AppConstants.requestTimeout);
    return _decodeMap(response);
  }

  Future<Map<String, dynamic>> metadata() async {
    final response = await _client
        .get(AppConstants.apiUri(AppConstants.metadataPath))
        .timeout(AppConstants.requestTimeout);
    return _decodeMap(response);
  }

  Future<DiseasePrediction> predictImage(
    File image, {
    double? gateThreshold,
    double? confThreshold,
    bool? tta,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      AppConstants.apiUri(AppConstants.predictPath, {
        'gate_threshold': gateThreshold?.toString(),
        'conf_threshold': confThreshold?.toString(),
        'tta': tta?.toString(),
      }),
    );
    request.files.add(await http.MultipartFile.fromPath('file', image.path));

    final response = await _sendMultipart(
      request,
      timeout: AppConstants.requestTimeout,
    );
    return DiseasePrediction.fromJson(response);
  }

  Future<VideoPredictionResult> predictVideo(
    File video, {
    int sampleEveryNFrames = 15,
    int maxFrames = 120,
    double? gateThreshold,
    double? confThreshold,
    bool? tta,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      AppConstants.apiUri(AppConstants.predictVideoPath, {
        'sample_every_n_frames': sampleEveryNFrames.toString(),
        'max_frames': maxFrames.toString(),
        'gate_threshold': gateThreshold?.toString(),
        'conf_threshold': confThreshold?.toString(),
        'tta': tta?.toString(),
      }),
    );
    request.files.add(await http.MultipartFile.fromPath('file', video.path));

    final response = await _sendMultipart(
      request,
      timeout: AppConstants.videoRequestTimeout,
    );
    return VideoPredictionResult.fromJson(response);
  }

  Future<DiseasePrediction> predictBase64(
    String imageBase64, {
    String? filename,
  }) async {
    final response = await _client
        .post(
          AppConstants.apiUri(AppConstants.predictBase64Path),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'image_base64': imageBase64,
            if (filename != null) 'filename': filename,
          }),
        )
        .timeout(AppConstants.requestTimeout);
    return DiseasePrediction.fromJson(_decodeMap(response));
  }

  WebSocketChannel connectLiveDetection() {
    return WebSocketChannel.connect(AppConstants.wsUri(AppConstants.livePath));
  }

  String liveFramePayload(Uint8List bytes, {required String frameId}) {
    return jsonEncode({
      'frame_id': frameId,
      'timestamp_ms': DateTime.now().millisecondsSinceEpoch,
      'filename': 'frame_$frameId.jpg',
      'content_type': 'image/jpeg',
      'image_base64': base64Encode(bytes),
    });
  }

  Future<Map<String, dynamic>> _sendMultipart(
    http.MultipartRequest request, {
    required Duration timeout,
  }) async {
    final streamed = await _client.send(request).timeout(timeout);
    final response = await http.Response.fromStream(streamed);
    return _decodeMap(response);
  }

  Map<String, dynamic> _decodeMap(http.Response response) {
    final decoded = response.body.isEmpty ? null : jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FarmEasyApiException(
        _errorMessage(decoded) ?? 'FarmEasy backend request failed',
        statusCode: response.statusCode,
      );
    }
    if (decoded is Map<String, dynamic>) return decoded;
    throw FarmEasyApiException('FarmEasy backend returned an invalid response');
  }

  String? _errorMessage(dynamic decoded) {
    if (decoded is Map && decoded['detail'] != null) {
      return decoded['detail'].toString();
    }
    return null;
  }

  void dispose() {
    _client.close();
  }
}
