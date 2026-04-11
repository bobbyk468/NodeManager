import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import React from 'react';

import { VisualizationSpec } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
}

function cellText(v: unknown): string {
  if (v === null || v === undefined) return '';
  return String(v);
}

export const ScoreSamplesTable: React.FC<Props> = ({
  spec,
  condition = 'B',
  dataset = '',
}) => {
  const columns = (spec.data.columns as string[]) ?? [];
  const rows = (spec.data.rows as Record<string, unknown>[]) ?? [];

  if (columns.length === 0 || rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
        No per-sample rows in this dataset.
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
        {spec.subtitle} ({rows.length} rows)
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 420 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell key={col} sx={{ fontWeight: 700 }}>
                  {col}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={cellText(row.id) || i}>
                {columns.map((col) => (
                  <TableCell key={col}>{cellText(row[col])}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
};
