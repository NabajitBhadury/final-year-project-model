import 'dart:convert';
import 'package:http/http.dart' as http;

class ChatService {
  static const String _apiKey =
      String.fromEnvironment('OPENROUTER_API_KEY', defaultValue: '');
  static const String _baseUrl =
      'https://openrouter.ai/api/v1/chat/completions';

  final List<Map<String, String>> _history = [
    {
      'role': 'system',
      'content':
          'You are an expert farming assistant. '
          'Answer only questions related to agriculture, crops, livestock, pests, soil health, and farm management. '
          'If a user asks about anything else (e.g., coding, movies, politics), politely refuse and guide them back to farming topics. '
          'Keep your answers concise, practical, and helpful for farmers.',
    },
  ];

  Stream<String> sendMessage(String message) async* {
    try {
      _history.add({'role': 'user', 'content': message});

      final request = http.Request('POST', Uri.parse(_baseUrl));
      request.headers.addAll({
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_apiKey',
        'HTTP-Referer': 'https://farmeasy.com',
        'X-Title': 'Farmers Companion',
      });
      request.body = jsonEncode({
        'model': 'google/gemini-2.5-flash-lite',
        'stream': true,
        'messages': _history,
      });

      final response = await http.Client().send(request);

      if (response.statusCode == 200) {
        String fullReply = "";
        await for (final chunk in response.stream.transform(utf8.decoder).transform(const LineSplitter())) {
          if (chunk.startsWith('data: ') && chunk != 'data: [DONE]') {
            try {
              final data = jsonDecode(chunk.substring(6));
              final content = data['choices'][0]['delta']['content'];
              if (content != null && content.isNotEmpty) {
                fullReply += content;
                yield content;
              }
            } catch (e) {
              // Ignore partial chunks or parse errors
            }
          }
        }
        _history.add({'role': 'assistant', 'content': fullReply});
      } else {
        final errorBody = await response.stream.bytesToString();
        yield "Error: ${response.statusCode} - $errorBody";
      }
    } catch (e) {
      yield "Error: $e";
    }
  }

  Stream<String> getPrecautionsStream(String disease) async* {
    try {
      final messages = [
        {
          'role': 'system',
          'content': 'You are an expert farming assistant. Provide a brief, practical list of precautions and treatments for the specified crop disease. Format your response clearly using markdown.'
        },
        {
          'role': 'user',
          'content': 'What are the precautions and treatments for $disease?'
        }
      ];

      final request = http.Request('POST', Uri.parse(_baseUrl));
      request.headers.addAll({
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_apiKey',
        'HTTP-Referer': 'https://farmeasy.com',
        'X-Title': 'Farmers Companion',
      });
      request.body = jsonEncode({
        'model': 'google/gemini-2.5-flash-lite',
        'stream': true,
        'messages': messages,
      });

      final response = await http.Client().send(request);

      if (response.statusCode == 200) {
        await for (final chunk in response.stream.transform(utf8.decoder).transform(const LineSplitter())) {
          if (chunk.startsWith('data: ') && chunk != 'data: [DONE]') {
            try {
              final data = jsonDecode(chunk.substring(6));
              final content = data['choices'][0]['delta']['content'];
              if (content != null && content.isNotEmpty) {
                yield content;
              }
            } catch (e) {
              // Ignore
            }
          }
        }
      } else {
        final errorBody = await response.stream.bytesToString();
        yield "Error: ${response.statusCode} - $errorBody";
      }
    } catch (e) {
      yield "Error: $e";
    }
  }

  void clearHistory() {
    _history.removeRange(1, _history.length); // Keep system prompt
  }
}
