import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../../models/disease_prediction_model.dart';
import '../../../services/chat_service.dart';
import 'status_panels.dart';

class PredictionResultPanel extends StatelessWidget {
  final DiseasePrediction result;

  const PredictionResultPanel({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(result);
    final icon = result.isNotLeaf
        ? Icons.block_outlined
        : result.isHealthy
        ? Icons.check_circle_outline
        : result.isUncertain
        ? Icons.help_outline
        : Icons.warning_amber_rounded;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 34),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      result.displayLabel,
                      style: GoogleFonts.outfit(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      result.statusText,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              MetricChip(
                label: 'Leaf',
                value: '${(result.leafProb * 100).toStringAsFixed(1)}%',
              ),
              if (result.confidence != null)
                MetricChip(
                  label: 'Confidence',
                  value: '${(result.confidence! * 100).toStringAsFixed(1)}%',
                ),
              if (result.processingMs != null)
                MetricChip(
                  label: 'Time',
                  value: '${result.processingMs!.toStringAsFixed(0)} ms',
                ),
            ],
          ),
          if (result.probabilities.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text(
              'Class probabilities',
              style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 12),
            ...result.probabilities.entries.map(
              (entry) => _ProbabilityBar(
                label: entry.key.replaceAll('_', ' '),
                value: entry.value,
                active: entry.key == result.label,
              ),
            ),
          ],
          if (!result.isHealthy && !result.isNotLeaf && !result.isUncertain) ...[
            const SizedBox(height: 24),
            _PrecautionsWidget(diseaseName: result.displayLabel),
          ],
        ],
      ),
    ).animate().fadeIn().slideY(begin: 0.08);
  }

  Color _statusColor(DiseasePrediction result) {
    if (result.isNotLeaf) return Colors.grey;
    if (result.isHealthy) return Colors.green;
    if (result.isUncertain) return Colors.orange;
    return Colors.redAccent;
  }
}

class _ProbabilityBar extends StatelessWidget {
  final String label;
  final double value;
  final bool active;

  const _ProbabilityBar({
    required this.label,
    required this.value,
    required this.active,
  });

  @override
  Widget build(BuildContext context) {
    final color = active ? Theme.of(context).colorScheme.primary : Colors.grey;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ),
              Text(
                '${(value * 100).toStringAsFixed(1)}%',
                style: TextStyle(color: color, fontWeight: FontWeight.w800),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: value.clamp(0, 1),
              minHeight: 7,
              color: color,
              backgroundColor: color.withValues(alpha: 0.12),
            ),
          ),
        ],
      ),
    );
  }
}

class _PrecautionsWidget extends StatefulWidget {
  final String diseaseName;
  const _PrecautionsWidget({required this.diseaseName});

  @override
  State<_PrecautionsWidget> createState() => _PrecautionsWidgetState();
}

class _PrecautionsWidgetState extends State<_PrecautionsWidget> {
  String _precautions = "";
  bool _isLoading = true;
  late final ChatService _chatService;

  @override
  void initState() {
    super.initState();
    _chatService = ChatService();
    _fetchPrecautions();
  }

  Future<void> _fetchPrecautions() async {
    try {
      await for (final chunk in _chatService.getPrecautionsStream(widget.diseaseName)) {
        if (mounted) {
          setState(() {
            _isLoading = false;
            _precautions += chunk;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _precautions = "Failed to load precautions.";
        });
      }
    }
    if (mounted && _precautions.isEmpty) {
      setState(() {
        _isLoading = false;
        _precautions = "No precautions available.";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading && _precautions.isEmpty) {
      return const Padding(
        padding: EdgeInsets.only(top: 8),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.healing, size: 20, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 8),
            Text(
              'Precautions & Treatment',
              style: GoogleFonts.outfit(fontWeight: FontWeight.w700, fontSize: 16),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHigh.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(16),
          ),
          child: MarkdownBody(
            data: _precautions,
            styleSheet: MarkdownStyleSheet(
              p: const TextStyle(fontSize: 14, height: 1.5),
            ),
          ),
        ),
      ],
    );
  }
}
