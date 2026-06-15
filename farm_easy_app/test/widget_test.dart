import 'package:flutter_test/flutter_test.dart';

import 'package:final_year_project/core/app_constants.dart';

void main() {
  test('FarmEasy backend constants are configured', () {
    expect(AppConstants.apiBaseUrl, isNotEmpty);
    expect(
      AppConstants.apiUri(AppConstants.predictPath).path,
      contains('/predict'),
    );
    expect(AppConstants.wsUri(AppConstants.livePath).scheme, startsWith('ws'));
  });
}
