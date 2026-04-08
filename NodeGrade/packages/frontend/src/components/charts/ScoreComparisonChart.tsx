import { Typography } from '@mui/material';
import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { VisualizationSpec } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface BucketEntry {
  student_id: string;
  cllm_mae: number;
  c5_mae: number;
  count: number;
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

export const ScoreComparisonChart: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const buckets = (spec.data.students as BucketEntry[]) ?? [];

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
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={buckets} margin={{ top: 4, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="student_id" tick={{ fontSize: 11 }} label={{ value: 'Score Range', position: 'insideBottom', offset: -4, fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} label={{ value: 'MAE', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <Tooltip
            formatter={(value: number, name: string) => [
              value.toFixed(3),
              name === 'cllm_mae' ? 'LLM Baseline MAE' : 'ConceptGrade MAE',
            ]}
          />
          <Legend
            formatter={(value) =>
              value === 'cllm_mae' ? 'LLM Baseline' : 'ConceptGrade'
            }
          />
          <Bar dataKey="cllm_mae" fill="#60a5fa" name="cllm_mae" radius={[4, 4, 0, 0]} />
          <Bar dataKey="c5_mae" fill="#f97316" name="c5_mae" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
