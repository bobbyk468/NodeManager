import { Typography } from '@mui/material';
import React from 'react';
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

import { VisualizationSpec } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface RadarStudent {
  student_id: string;
  values: number[];
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

// Recharts RadarChart expects data as [{dimension, student_0, student_1, ...}]
function toRadarData(
  dimensions: string[],
  students: RadarStudent[],
): Array<Record<string, string | number>> {
  return dimensions.map((dim, i) => {
    const entry: Record<string, string | number> = { dimension: dim };
    students.forEach((s) => {
      entry[s.student_id] = s.values[i] ?? 0;
    });
    return entry;
  });
}

const COLORS = ['#3b82f6', '#f97316', '#22c55e', '#ef4444', '#8b5cf6'];

export const StudentRadarChart: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const dimensions = (spec.data.dimensions as string[]) ?? [];
  const allStudents = (spec.data.students as RadarStudent[]) ?? [];
  // Show at most 5 students to keep the radar readable
  const students = allStudents.slice(0, 5);
  const radarData = toRadarData(dimensions, students);

  if (dimensions.length === 0 || students.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
        No radar data available for this dataset.
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
        {spec.subtitle} (showing {students.length} of {allStudents.length} students)
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={radarData} margin={{ top: 8, right: 40, left: 40, bottom: 8 }}>
          <PolarGrid />
          <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 10 }} />
          <Tooltip />
          {students.map((s, i) => (
            <Radar
              key={s.student_id}
              name={`Student ${i + 1}`}
              dataKey={s.student_id}
              stroke={COLORS[i % COLORS.length]}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.15}
            />
          ))}
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
