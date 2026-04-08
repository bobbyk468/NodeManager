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
  level: number;
  count: number;
  percentage: number;
  color: string;
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

export const SoloBarChart: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const bars = (spec.data.bars as BarEntry[]) ?? [];

  return (
    <div
      onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}
    >
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
        {spec.title}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
        {spec.subtitle}
      </Typography>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={bars} margin={{ top: 4, right: 16, left: 0, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10 }}
            angle={-15}
            textAnchor="end"
            interval={0}
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value: number) => [value, 'Students']}
            labelFormatter={(label) => `SOLO: ${label}`}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} name="Students">
            {bars.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
