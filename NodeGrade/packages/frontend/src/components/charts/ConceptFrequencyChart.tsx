import { Typography } from '@mui/material';
import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { VisualizationSpec } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface BarEntry {
  label: string;
  concept: string;
  count: number;
  percentage: number;
  color: string;
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

// Neutral color used for all bars in Condition A.
// Condition A must not see per-concept color differentiation because the backend
// assigns colors based on expected/rubric status — the same signal the CONTRADICTS
// trace would highlight in Condition B. Showing that color to Condition A would
// confound H2 by allowing frequency-based identification of rubric-expected concepts.
const CONDITION_A_BAR_COLOR = '#3b82f6';

export const ConceptFrequencyChart: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const bars = (spec.data.bars as BarEntry[]) ?? [];
  const isConditionA = condition === 'A';

  if (bars.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
        No concept frequency data available for this dataset.
      </Typography>
    );
  }

  return (
    <div
      onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}
    >
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
        {spec.title}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
        {/* Condition A subtitle strips mention of expected/match status to avoid signal leakage */}
        {isConditionA ? 'Total student answer frequency (coverage status not shown)' : spec.subtitle}
      </Typography>
      <ResponsiveContainer width="100%" height={Math.max(240, bars.length * 28)}>
        <BarChart
          data={bars}
          layout="vertical"
          margin={{ top: 4, right: 40, left: 130, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fontSize: 10 }}
            width={120}
          />
          <Tooltip
            formatter={(value: number, _name: string, props: { payload?: BarEntry }) => [
              `${value} students (${props.payload?.percentage ?? 0}%)`,
              'Coverage',
            ]}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Students">
            {bars.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                // Condition B: use backend-assigned color (green = expected/rubric concept,
                // grey = incidental coverage). Condition A: uniform neutral blue — no match
                // status encoding to prevent confounding H2 semantic alignment analysis.
                fill={isConditionA ? CONDITION_A_BAR_COLOR : (entry.color ?? CONDITION_A_BAR_COLOR)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
