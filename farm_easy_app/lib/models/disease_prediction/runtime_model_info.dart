import 'model_parsing.dart';

class RuntimeModelInfo {
  final String models;
  final bool tta;
  final double gateThreshold;
  final double confThreshold;

  RuntimeModelInfo({
    required this.models,
    required this.tta,
    required this.gateThreshold,
    required this.confThreshold,
  });

  factory RuntimeModelInfo.fromJson(Map<String, dynamic> json) {
    return RuntimeModelInfo(
      models: json['models']?.toString() ?? 'effb3',
      tta: json['tta'] == true,
      gateThreshold: asDouble(json['gate_threshold']) ?? 0.5,
      confThreshold: asDouble(json['conf_threshold']) ?? 0.45,
    );
  }
}
