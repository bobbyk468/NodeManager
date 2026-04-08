import { Box, Grid, Tooltip, Typography } from '@mui/material';
import React from 'react';

import { VisualizationSpec } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface HeatCell {
  concept: string;
  severity: string;
  count: number;
  intensity: number;
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

function intensityToColor(intensity: number): string {
  // Scale from white → orange-red
  const scale = ['#fef2f2', '#fca5a5', '#ef4444', '#991b1b'];
  if (intensity <= 0) return scale[0];
  const idx = Math.min(Math.round(intensity * (scale.length - 1)), scale.length - 1);
  return scale[idx];
}

export const MisconceptionHeatmap: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const cells = (spec.data.cells as HeatCell[]) ?? [];
  const xLabels = (spec.data.x_labels as string[]) ?? ['critical', 'moderate', 'minor'];
  const yLabels = (spec.data.y_labels as string[]) ?? [];

  if (cells.length === 0) {
    return (
      <Box onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}>
        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
          {spec.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ p: 1 }}>
          No misconception data available for this dataset. Misconception heatmap requires
          live pipeline output.
        </Typography>
      </Box>
    );
  }

  // Build lookup: {concept: {severity: intensity}}
  const lookup: Record<string, Record<string, { intensity: number; count: number }>> = {};
  for (const cell of cells) {
    if (!lookup[cell.concept]) lookup[cell.concept] = {};
    lookup[cell.concept][cell.severity] = { intensity: cell.intensity, count: cell.count };
  }

  return (
    <Box
      onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}
    >
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
        {spec.title}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
        {spec.subtitle}
      </Typography>

      {/* Header row */}
      <Grid container spacing={0.5} sx={{ mb: 0.5 }}>
        <Grid item xs={4}>
          <Typography variant="caption" color="text.secondary">
            Concept
          </Typography>
        </Grid>
        {xLabels.map((sev) => (
          <Grid key={sev} item xs={Math.floor(8 / xLabels.length)}>
            <Typography variant="caption" color="text.secondary" align="center" display="block">
              {sev}
            </Typography>
          </Grid>
        ))}
      </Grid>

      {/* Data rows */}
      {yLabels.map((concept) => (
        <Grid container spacing={0.5} key={concept} sx={{ mb: 0.5 }}>
          <Grid item xs={4}>
            <Typography variant="caption" noWrap title={concept}>
              {concept.replace(/_/g, ' ')}
            </Typography>
          </Grid>
          {xLabels.map((sev) => {
            const cell = lookup[concept]?.[sev];
            const intensity = cell?.intensity ?? 0;
            const count = cell?.count ?? 0;
            return (
              <Grid key={sev} item xs={Math.floor(8 / xLabels.length)}>
                <Tooltip title={`${concept} | ${sev}: ${count} occurrences`} arrow>
                  <Box
                    sx={{
                      height: 24,
                      borderRadius: 0.5,
                      backgroundColor: intensityToColor(intensity),
                      border: '1px solid rgba(0,0,0,0.08)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {count > 0 && (
                      <Typography variant="caption" sx={{ fontSize: 9, color: intensity > 0.5 ? '#fff' : '#374151' }}>
                        {count}
                      </Typography>
                    )}
                  </Box>
                </Tooltip>
              </Grid>
            );
          })}
        </Grid>
      ))}
    </Box>
  );
};
