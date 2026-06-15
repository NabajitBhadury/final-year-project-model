double? asDouble(dynamic value) {
  if (value is num) return value.toDouble();
  return null;
}

Map<String, int> intMap(dynamic value) {
  final map = <String, int>{};
  if (value is Map) {
    value.forEach((key, raw) {
      if (raw is num) {
        map[key.toString()] = raw.toInt();
      }
    });
  }
  return map;
}
