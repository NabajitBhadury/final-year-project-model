class AppConstants {
  AppConstants._();

  static const String appName = 'FarmEasy';

  static const String apiBaseUrl = String.fromEnvironment(
    'FARMEASY_API_BASE_URL',
    defaultValue: 'https://final-year-project-model-production.up.railway.app',
  );

  static const String healthPath = '/health';
  static const String metadataPath = '/metadata';
  static const String predictPath = '/predict';
  static const String predictBase64Path = '/predict/base64';
  static const String predictVideoPath = '/predict/video';
  static const String livePath = '/ws/live';

  static const Duration requestTimeout = Duration(seconds: 60);
  static const Duration videoRequestTimeout = Duration(minutes: 5);
  static const Duration liveFrameInterval = Duration(seconds: 2);

  static Uri apiUri(String path, [Map<String, String?> query = const {}]) {
    final filteredQuery = <String, String>{};
    query.forEach((key, value) {
      if (value != null && value.isNotEmpty) {
        filteredQuery[key] = value;
      }
    });

    final base = Uri.parse(apiBaseUrl);
    final normalizedPath =
        '${base.path.replaceAll(RegExp(r'/$'), '')}${path.startsWith('/') ? path : '/$path'}';
    return base.replace(
      path: normalizedPath,
      queryParameters: filteredQuery.isEmpty ? null : filteredQuery,
    );
  }

  static Uri wsUri(String path) {
    final base = Uri.parse(apiBaseUrl);
    final scheme = base.scheme == 'https' ? 'wss' : 'ws';
    final normalizedPath =
        '${base.path.replaceAll(RegExp(r'/$'), '')}${path.startsWith('/') ? path : '/$path'}';
    return base.replace(scheme: scheme, path: normalizedPath);
  }
}
