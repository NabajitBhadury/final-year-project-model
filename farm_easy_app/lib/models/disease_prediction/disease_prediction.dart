import 'model_parsing.dart';
import 'prediction_image_info.dart';
import 'runtime_model_info.dart';

class DiseasePrediction {
  final String requestId;
  final bool isLeaf;
  final double leafProb;
  final String? label;
  final double? confidence;
  final String status;
  final Map<String, double> probabilities;
  final RuntimeModelInfo? model;
  final PredictionImageInfo? image;
  final double? processingMs;
  final String? frameId;
  final int? clientTimestampMs;

  DiseasePrediction({
    required this.requestId,
    required this.isLeaf,
    required this.leafProb,
    required this.label,
    required this.confidence,
    required this.status,
    required this.probabilities,
    this.model,
    this.image,
    this.processingMs,
    this.frameId,
    this.clientTimestampMs,
  });

  factory DiseasePrediction.fromJson(Map<String, dynamic> json) {
    final probabilities = <String, double>{};
    final rawProbabilities = json['probabilities'];
    if (rawProbabilities is Map) {
      rawProbabilities.forEach((key, value) {
        if (value is num) {
          probabilities[key.toString()] = value.toDouble();
        }
      });
    }

    return DiseasePrediction(
      requestId: json['request_id']?.toString() ?? '',
      isLeaf: json['is_leaf'] == true,
      leafProb: asDouble(json['leaf_prob']) ?? 0,
      label: json['label']?.toString(),
      confidence: asDouble(json['confidence']),
      status: json['status']?.toString() ?? 'unknown',
      probabilities: probabilities,
      model: json['model'] is Map<String, dynamic>
          ? RuntimeModelInfo.fromJson(json['model'] as Map<String, dynamic>)
          : null,
      image: json['image'] is Map<String, dynamic>
          ? PredictionImageInfo.fromJson(json['image'] as Map<String, dynamic>)
          : null,
      processingMs: asDouble(json['processing_ms']),
      frameId: json['frame_id']?.toString(),
      clientTimestampMs: json['client_timestamp_ms'] is num
          ? (json['client_timestamp_ms'] as num).toInt()
          : null,
    );
  }

  bool get isHealthy => label == 'Healthy' && status == 'ok';
  bool get isNotLeaf => status == 'not_leaf' || !isLeaf;
  bool get isUncertain => status == 'uncertain';

  String get displayLabel {
    if (isNotLeaf) return 'Not a corn leaf';
    if (isUncertain) return 'Uncertain result';
    return (label ?? 'Unknown').replaceAll('_', ' ');
  }

  String get statusText {
    switch (status) {
      case 'ok':
        return isHealthy ? 'Healthy leaf' : 'Disease detected';
      case 'not_leaf':
        return 'Leaf check failed';
      case 'uncertain':
        return 'Needs another scan';
      default:
        return 'Analysis complete';
    }
  }
}
