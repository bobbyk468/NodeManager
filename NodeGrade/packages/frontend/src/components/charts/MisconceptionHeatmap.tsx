import { Box, Chip, Tooltip, Typography } from '@mui/material';
import React from 'react';

import { VisualizationSpec } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface HeatCell {
  // Backend extras file uses x/y/value layout
  x: string;        // severity column (critical / moderate / minor)
  y: string;        // concept row id
  value: number;    // student count
  intensity: number;
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
  selectedConcept?: string | null;
  onCellClick?: (concept: string, severity: string) => void;
}

function intensityToColor(intensity: number, selected: boolean): string {
  if (selected) return '#3b82f6';
  const scale = ['#fef2f2', '#fca5a5', '#ef4444', '#991b1b'];
  if (intensity <= 0) return scale[0];
  const idx = Math.min(Math.round(intensity * (scale.length - 1)), scale.length - 1);
  return scale[idx];
}

export const MisconceptionHeatmap: React.FC<Props> = ({
  spec,
  condition = 'B',
  dataset = '',
  selectedConcept = null,
  onCellClick,
}) => {
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

  // Build lookup: { conceptId: { severity: { intensity, count } } }
  // The backend extras file sends cells with x=severity, y=concept, value=count.
  const lookup: Record<string, Record<string, { intensity: number; count: number }>> = {};
  for (const cell of cells) {
    const conceptKey = cell.y;
    const severityKey = cell.x;
    if (!lookup[conceptKey]) lookup[conceptKey] = {};
    lookup[conceptKey][severityKey] = { intensity: cell.intensity, count: cell.value };
  }

  const isInteractive = !!onCellClick;
  // Condition A isolation: severity labels (critical/moderate/minor) are KG-derived signals —
  // they reveal which concepts are rubric-expected. Showing severity breakdown to Condition A
  // participants would let them identify expected concepts via the heatmap, confounding H2.
  // In Condition A: aggregate all severities into a single "students affected" count per concept,
  // with no color encoding that distinguishes severity levels.
  const isConditionA = condition === 'A';

  if (isConditionA) {
    // Build aggregated counts: sum across all severity columns per concept
    const aggregated = yLabels.map((concept) => {
      const total = xLabels.reduce((sum, sev) => sum + (lookup[concept]?.[sev]?.count ?? 0), 0);
      return { concept, total };
    }).filter((r) => r.total > 0).sort((a, b) => b.total - a.total);

    return (
      <Box onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}>
        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
          {spec.title}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" mb={1}>
          Students with concept gaps (severity breakdown not shown)
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {aggregated.map(({ concept, total }) => (
            <Box key={concept} display="flex" alignItems="center" justifyContent="space-between"
              sx={{ px: 1, py: 0.5, borderRadius: 0.5, bgcolor: '#f8fafc', border: '1px solid #e2e8f0' }}>
              <Typography variant="caption" noWrap title={concept} sx={{ flexGrow: 1 }}>
                {concept.replace(/_/g, ' ')}
              </Typography>
              <Chip label={`${total} students`} size="small"
                sx={{ fontSize: 9, height: 18, bgcolor: '#e0f2fe', color: '#0369a1', ml: 1 }} />
            </Box>
          ))}
        </Box>
      </Box>
    );
  }

  return (
    <Box
      onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}
    >
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
        {spec.title}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
        {spec.subtitle}
      </Typography>
      {isInteractive && (
        <Typography variant="caption" color="primary" display="block" mb={1} sx={{ fontStyle: 'italic' }}>
          Click any cell to see student answers for that concept
        </Typography>
      )}

      {/* CSS grid: concept label gets 2fr, each severity column gets 1fr — fills 100% always */}
      <Box sx={{ display: 'grid', gridTemplateColumns: `2fr repeat(${xLabels.length}, 1fr)`, gap: '4px', mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary">Concept</Typography>
        {xLabels.map((sev) => (
          <Typography key={sev} variant="caption" color="text.secondary" align="center" display="block">
            {sev}
          </Typography>
        ))}
      </Box>

      {/* Data rows */}
      {yLabels.map((concept) => {
        const isRowSelected = selectedConcept === concept;
        return (
          <Box
            key={concept}
            sx={{
              display: 'grid',
              gridTemplateColumns: `2fr repeat(${xLabels.length}, 1fr)`,
              gap: '4px',
              mb: 0.5,
              borderRadius: 0.5,
              outline: isRowSelected ? '2px solid #3b82f6' : 'none',
              alignItems: 'center',
            }}
          >
            <Typography
              variant="caption"
              noWrap
              title={concept}
              sx={{
                fontWeight: isRowSelected ? 700 : 400,
                color: isRowSelected ? 'primary.main' : 'text.primary',
              }}
            >
              {concept.replace(/_/g, ' ')}
            </Typography>
            {xLabels.map((sev) => {
              const cell = lookup[concept]?.[sev];
              const intensity = cell?.intensity ?? 0;
              const count = cell?.count ?? 0;
              return (
                <Tooltip key={sev} title={`${concept.replace(/_/g, ' ')} · ${sev}: ${count} students`} arrow>
                  <Box
                    onClick={() => {
                      if (!isInteractive || count === 0) return;
                      logEvent(condition, dataset, 'chart_click', { viz_id: spec.viz_id, concept_id: concept, severity: sev });
                      onCellClick!(concept, sev);
                    }}
                    sx={{
                      height: 24,
                      borderRadius: 0.5,
                      backgroundColor: intensityToColor(intensity, isRowSelected && count > 0),
                      border: isRowSelected && count > 0
                        ? '2px solid #1d4ed8'
                        : '1px solid rgba(0,0,0,0.08)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: isInteractive && count > 0 ? 'pointer' : 'default',
                      transition: 'transform 0.1s',
                      '&:hover': isInteractive && count > 0 ? { transform: 'scale(1.05)' } : {},
                    }}
                  >
                    {count > 0 && (
                      <Typography
                        variant="caption"
                        sx={{ fontSize: 9, color: (isRowSelected || intensity > 0.5) ? '#fff' : '#374151' }}
                      >
                        {count}
                      </Typography>
                    )}
                  </Box>
                </Tooltip>
              );
            })}
          </Box>
        );
      })}
    </Box>
  );
};
