import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../models/disease_prediction_model.dart';
import 'status_panels.dart';

class LiveResultPanel extends StatelessWidget {
  final DiseasePrediction result;

  const LiveResultPanel({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final color = result.isNotLeaf
        ? Colors.grey
        : result.isHealthy
        ? Colors.green
        : result.isUncertain
        ? Colors.orange
        : Colors.redAccent;
    return Container(
      padding: const EdgeInsets.all(16),
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
              Icon(Icons.eco_outlined, color: color, size: 32),
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
          const SizedBox(height: 12),
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
              if (result.frameId != null)
                MetricChip(label: 'Frame', value: result.frameId!),
            ],
          ),
        ],
      ),
    );
  }
}
