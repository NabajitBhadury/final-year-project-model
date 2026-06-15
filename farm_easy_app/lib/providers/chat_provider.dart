import 'package:flutter/material.dart';
import '../services/chat_service.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

class ChatProvider extends ChangeNotifier {
  final ChatService _chatService = ChatService();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;

  ChatProvider() {
    _addMessage(
      "Hello! I'm your farming assistant. Ask me anything about your crops or livestock.",
      false,
    );
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    _addMessage(text, true);
    _isLoading = true;
    notifyListeners();

    // Create an empty message for the assistant
    _messages.add(
      ChatMessage(text: '', isUser: false, timestamp: DateTime.now()),
    );
    final assistantMsgIndex = _messages.length - 1;

    try {
      await for (final chunk in _chatService.sendMessage(text)) {
        if (_isLoading) {
          _isLoading = false;
        }
        _messages[assistantMsgIndex] = ChatMessage(
          text: _messages[assistantMsgIndex].text + chunk,
          isUser: false,
          timestamp: _messages[assistantMsgIndex].timestamp,
        );
        notifyListeners();
      }
    } catch (e) {
      _messages[assistantMsgIndex] = ChatMessage(
        text: "Error: $e",
        isUser: false,
        timestamp: _messages[assistantMsgIndex].timestamp,
      );
    }

    _isLoading = false;
    notifyListeners();
  }

  void _addMessage(String text, bool isUser) {
    _messages.add(
      ChatMessage(text: text, isUser: isUser, timestamp: DateTime.now()),
    );
    notifyListeners();
  }

  void clearChat() {
    _messages.clear();
    _chatService.clearHistory();
    _addMessage(
      "Hello! I'm your farming assistant. Ask me anything about your crops or livestock.",
      false,
    );
    notifyListeners();
  }
}
