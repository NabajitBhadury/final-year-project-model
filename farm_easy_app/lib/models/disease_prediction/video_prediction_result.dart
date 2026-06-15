import 'disease_prediction.dart';
import 'model_parsing.dart';

class VideoPredictionResult {
  final String requestId;
  final String? filename;
  final String? contentType;
  final int? totalFrames;
  final double? fps;
  final double? durationSec;
  final int sampleEveryNFrames;
  final int maxFrames;
  final int sampledFrames;
  final Map<String, int> statusCounts;
  final Map<String, int> labelCounts;
  final List<VideoFramePrediction> frames;
  final double? processingMs;

  VideoPredictionResult({
    required this.requestId,
    required this.filename,
    required this.contentType,
    required this.totalFrames,
    required this.fps,
    required this.durationSec,
    required this.sampleEveryNFrames,
    required this.maxFrames,
    required this.sampledFrames,
    required this.statusCounts,
    required this.labelCounts,
    required this.frames,
    required this.processingMs,
  });

  factory VideoPredictionResult.fromJson(Map<String, dynamic> json) {
    return VideoPredictionResult(
      requestId: json['request_id']?.toString() ?? '',
      filename: json['filename']?.toString(),
      contentType: json['content_type']?.toString(),
      totalFrames: json['total_frames'] is num
          ? (json['total_frames'] as num).toInt()
          : null,
      fps: asDouble(json['fps']),
      durationSec: asDouble(json['duration_sec']),
      sampleEveryNFrames: json['sample_every_n_frames'] is num
          ? (json['sample_every_n_frames'] as num).toInt()
          : 15,
      maxFrames: json['max_frames'] is num
          ? (json['max_frames'] as num).toInt()
          : 120,
      sampledFrames: json['sampled_frames'] is num
          ? (json['sampled_frames'] as num).toInt()
          : 0,
      statusCounts: intMap(json['status_counts']),
      labelCounts: intMap(json['label_counts']),
      frames: json['frames'] is List
          ? (json['frames'] as List)
                .whereType<Map<String, dynamic>>()
                .map(VideoFramePrediction.fromJson)
                .toList()
          : const [],
      processingMs: asDouble(json['processing_ms']),
    );
  }

  DiseasePrediction? get bestPrediction {
    final okFrames = frames.where((frame) => frame.prediction.status == 'ok');
    if (okFrames.isEmpty) {
      return frames.isEmpty ? null : frames.first.prediction;
    }
    return okFrames
        .reduce(
          (best, frame) =>
              (frame.prediction.confidence ?? 0) >
                  (best.prediction.confidence ?? 0)
              ? frame
              : best,
        )
        .prediction;
  }
}

class VideoFramePrediction {
  final int frameIndex;
  final double timestampMs;
  final DiseasePrediction prediction;

  VideoFramePrediction({
    required this.frameIndex,
    required this.timestampMs,
    required this.prediction,
  });

  factory VideoFramePrediction.fromJson(Map<String, dynamic> json) {
    return VideoFramePrediction(
      frameIndex: json['frame_index'] is num
          ? (json['frame_index'] as num).toInt()
          : 0,
      timestampMs: asDouble(json['timestamp_ms']) ?? 0,
      prediction: DiseasePrediction.fromJson(
        json['prediction'] as Map<String, dynamic>,
      ),
    );
  }
}
