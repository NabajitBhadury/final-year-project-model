class PredictionImageInfo {
  final int? width;
  final int? height;
  final String? mode;
  final String? format;
  final String? filename;
  final String? contentType;

  PredictionImageInfo({
    this.width,
    this.height,
    this.mode,
    this.format,
    this.filename,
    this.contentType,
  });

  factory PredictionImageInfo.fromJson(Map<String, dynamic> json) {
    return PredictionImageInfo(
      width: json['width'] is num ? (json['width'] as num).toInt() : null,
      height: json['height'] is num ? (json['height'] as num).toInt() : null,
      mode: json['mode']?.toString(),
      format: json['format']?.toString(),
      filename: json['filename']?.toString(),
      contentType: json['content_type']?.toString(),
    );
  }
}
