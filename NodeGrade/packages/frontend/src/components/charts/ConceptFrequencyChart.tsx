import { Typography } from '@mui/material';
import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
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

export const ConceptFrequencyChart: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const bars = (spec.data.bars as BarEntry[]) ?? [];

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
        {spec.subtitle}
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
          <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} name="Students" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
