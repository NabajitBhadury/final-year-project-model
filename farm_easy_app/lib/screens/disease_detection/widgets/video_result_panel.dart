import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../models/disease_prediction_model.dart';
import 'prediction_result_panel.dart';
import 'status_panels.dart';

class VideoResultPanel extends StatelessWidget {
  final VideoPredictionResult result;

  const VideoResultPanel({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final best = result.bestPrediction;
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: colorScheme.outlineVariant),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Video summary',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  MetricChip(
                    label: 'Frames',
                    value: result.sampledFrames.toString(),
                  ),
                  if (result.fps != null)
                    MetricChip(
                      label: 'FPS',
                      value: result.fps!.toStringAsFixed(1),
                    ),
                  if (result.durationSec != null)
                    MetricChip(
                      label: 'Length',
                      value: '${result.durationSec!.toStringAsFixed(1)} s',
                    ),
                  ...result.statusCounts.entries.map(
                    (entry) =>
                        MetricChip(label: entry.key, value: '${entry.value}'),
                  ),
                ],
              ),
            ],
          ),
        ),
        if (best != null) ...[
          const SizedBox(height: 14),
          PredictionResultPanel(result: best),
        ],
        const SizedBox(height: 14),
        Container(
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: colorScheme.outlineVariant),
          ),
          child: ExpansionTile(
            shape: const Border(),
            collapsedShape: const Border(),
            title: Text(
              'Sampled frames',
              style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
            ),
            children: result.frames.take(12).map((frame) {
              final prediction = frame.prediction;
              return ListTile(
                dense: true,
                title: Text(prediction.displayLabel),
                subtitle: Text(
                  '${(frame.timestampMs / 1000).toStringAsFixed(1)} s • ${prediction.status}',
                ),
                trailing: prediction.confidence == null
                    ? null
                    : Text(
                        '${(prediction.confidence! * 100).toStringAsFixed(0)}%',
                      ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
