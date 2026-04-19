/**
 * StudentRadarChart — 4-quartile cognitive profile radar.
 *
 * Clicking a quartile legend item selects it → updates DashboardContext.selectedQuartileIndex
 * so StudentAnswerPanel filters to students in that score range (bidirectional brushing).
 */

import { Box, Chip, Typography } from '@mui/material';
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
import { useDashboard } from '../../contexts/DashboardContext';
import { logEvent } from '../../utils/studyLogger';

interface RadarStudent {
  student_id: string;
  color: string;
  n: number;
  avg_human_score: number;
  values: number[];
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

function toRadarData(
  dimensions: string[],
  students: RadarStudent[],
): Array<Record<string, string | number>> {
  return dimensions.map((dim, i) => {
    const entry: Record<string, string | number> = { dimension: dim };
    students.forEach((s) => { entry[s.student_id] = s.values[i] ?? 0; });
    return entry;
  });
}

const QUARTILE_LABELS = ['Low Scorers (Q1)', 'Mid-Low (Q2)', 'Mid-High (Q3)', 'High Scorers (Q4)'];

export const StudentRadarChart: React.FC<Props> = ({ spec, condition = 'B', dataset = '' }) => {
  const { selectedQuartileIndex, selectQuartile } = useDashboard();

  const dimensions = (spec.data.dimensions as string[]) ?? [];
  const allStudents = (spec.data.students as RadarStudent[]) ?? [];
  const students = allStudents.slice(0, 5);
  const radarData = toRadarData(dimensions, students);

  if (dimensions.length === 0 || students.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
        No radar data available. Run: python3 generate_dashboard_extras.py
      </Typography>
    );
  }

  const handleQuartileClick = (studentId: string) => {
    const qIndex = QUARTILE_LABELS.findIndex((l) => l === studentId);
    if (qIndex === -1) return;
    const next = selectedQuartileIndex === qIndex ? null : qIndex;
    selectQuartile(next);
    logEvent(condition, dataset, 'chart_click', { viz_id: 'student_radar', quartile: qIndex });
  };

  return (
    <div onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}>
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
        {spec.title}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
        {spec.subtitle}
      </Typography>
      <Typography variant="caption" color="primary" display="block" mb={1} sx={{ fontStyle: 'italic' }}>
        Click a quartile label to filter the student answer panel
      </Typography>

      {/* Quartile filter chips */}
      <Box display="flex" gap={0.5} flexWrap="wrap" mb={1}>
        {students.map((s, i) => {
          const isActive = selectedQuartileIndex === i;
          return (
            <Chip
              key={s.student_id}
              label={s.student_id}
              size="small"
              onClick={() => handleQuartileClick(s.student_id)}
              sx={{
                bgcolor: isActive ? s.color : `${s.color}22`,
                color: isActive ? '#fff' : s.color,
                fontWeight: isActive ? 700 : 400,
                cursor: 'pointer',
                fontSize: 10,
                border: `1px solid ${s.color}`,
                transition: 'all 0.15s',
              }}
            />
          );
        })}
        {selectedQuartileIndex !== null && (
          <Chip
            label="Clear filter"
            size="small"
            variant="outlined"
            onClick={() => selectQuartile(null)}
            sx={{ fontSize: 10, cursor: 'pointer' }}
          />
        )}
      </Box>

      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={radarData} margin={{ top: 8, right: 40, left: 40, bottom: 8 }}>
          <PolarGrid />
          <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 10 }} />
          <Tooltip formatter={(val: number) => (val * 100).toFixed(1) + '%'} />
          {students.map((s, i) => {
            const isSelected = selectedQuartileIndex === null || selectedQuartileIndex === i;
            return (
              <Radar
                key={s.student_id}
                name={s.student_id}
                dataKey={s.student_id}
                stroke={s.color}
                fill={s.color}
                fillOpacity={isSelected ? 0.2 : 0.03}
                strokeOpacity={isSelected ? 1 : 0.3}
                strokeWidth={isSelected ? 2 : 1}
              />
            );
          })}
          <Legend
            wrapperStyle={{ fontSize: 10 }}
            onClick={(e) => handleQuartileClick(e.dataKey as string)}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
