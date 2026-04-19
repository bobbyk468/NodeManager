/**
 * CrossDatasetComparisonChart — SVG slopegraph with vocabulary richness annotations.
 *
 * Shows C_LLM MAE vs ConceptGrade MAE across all three datasets side-by-side.
 * Each line = one dataset.  Steeper downward slope = KG adds more value.
 *
 * Annotation brackets on the right side group datasets by domain vocabulary richness
 * (the "preliminary observation" driving the cross-dataset design per VIS reviewers):
 *   • "High KG Vocabulary Richness" — Mohler (CS), DigiKlausur (Neural Nets)
 *   • "Everyday Vocabulary" — Kaggle ASAG (Science)
 */

import { Box, Chip, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';

import { DatasetSummaryResponse } from '../../common/visualization.types';
import { logEvent } from '../../utils/studyLogger';

interface DatasetPoint {
  dataset: string;
  shortLabel: string;
  domainLabel: string;
  cllm_mae: number;
  c5_mae: number;
  delta_pct: number;
  wilcoxon_p: number;
}

interface Props {
  apiBase: string;
  condition?: string;
}

const DATASET_META: Record<string, { short: string; domain: string }> = {
  mohler:      { short: 'Mohler',      domain: 'CS / Q&A'    },
  offline:     { short: 'Mohler',      domain: 'CS / Q&A'    },
  digiklausur: { short: 'DigiKlausur', domain: 'Neural Nets' },
  kaggle_asag: { short: 'Kaggle ASAG', domain: 'Science'     },
};

/**
 * Vocabulary richness class: 'high' = domain-specific KG vocabulary;
 * 'everyday' = close to everyday language, KG adds less.
 */
const VOCAB_CLASS: Record<string, 'high' | 'everyday'> = {
  mohler:      'high',
  offline:     'high',
  digiklausur: 'high',
  kaggle_asag: 'everyday',
};

// SVG layout constants — wider than before to accommodate right-side annotation brackets
const W      = 620;
const H      = 300;
const PAD_L  = 130;
const PAD_R  = 170;   // extra room for brackets + labels
const PAD_T  = 42;
const PAD_B  = 36;

const SLOPE_COLORS = ['#7c3aed', '#2563eb', '#0891b2', '#d97706'];

function ys(mae: number, maeMin: number, maeMax: number): number {
  return PAD_T + ((maeMax - mae) / (maeMax - maeMin)) * (H - PAD_T - PAD_B);
}

export const CrossDatasetComparisonChart: React.FC<Props> = ({ apiBase, condition = 'B' }) => {
  const [points, setPoints] = useState<DatasetPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${apiBase}/api/visualization/datasets`)
      .then((r) => r.json())
      .then(async (res: { datasets: string[] }) => {
        const settled = await Promise.allSettled(
          res.datasets.map((ds) =>
            fetch(`${apiBase}/api/visualization/datasets/${ds}`)
              .then((r) => (r.ok ? (r.json() as Promise<DatasetSummaryResponse>) : Promise.reject()))
              .then(
                (d): DatasetPoint => ({
                  dataset:    ds,
                  shortLabel: DATASET_META[ds]?.short  ?? ds,
                  domainLabel:DATASET_META[ds]?.domain ?? '',
                  cllm_mae:   d.metrics.C_LLM.mae,
                  c5_mae:     d.metrics.C5_fix.mae,
                  delta_pct:  d.mae_reduction_pct,
                  wilcoxon_p: d.wilcoxon_p,
                }),
              ),
          ),
        );
        const fulfilled = settled
          .filter((r): r is PromiseFulfilledResult<DatasetPoint> => r.status === 'fulfilled')
          .map((r) => r.value)
          .sort((a, b) => b.cllm_mae - a.cllm_mae); // highest CLLM MAE first = top of chart
        setPoints(fulfilled);
        setLoading(false);
      })
      .catch(() => { setError(true); setLoading(false); });
  }, [apiBase]);

  if (loading) return null;
  if (error || points.length < 2) {
    return (
      <Box sx={{ p: 2, color: 'text.secondary', fontStyle: 'italic', fontSize: 13 }}>
        Cross-dataset comparison requires data from at least two datasets. Run the pipeline for additional datasets to populate this chart.
      </Box>
    );
  }

  const allMae = points.flatMap((p) => [p.cllm_mae, p.c5_mae]);
  const maeMin = Math.min(...allMae) * 0.88;
  const maeMax = Math.max(...allMae) * 1.08;

  const xLeft  = PAD_L;
  const xRight = W - PAD_R;

  // Y-axis reference ticks
  const range = maeMax - maeMin;
  const step  = range > 0.4 ? 0.1 : 0.05;
  const ticks: number[] = [];
  for (
    let v = Math.ceil(maeMin / step) * step;
    v <= maeMax;
    v = Math.round((v + step) * 1000) / 1000
  ) ticks.push(v);

  // ── Vocabulary-class annotation bracket computation ──────────────────────────
  // bx = x-coordinate of the bracket's spine (right of all delta labels)
  const BX = xRight + 100;

  const highPoints     = points.filter((p) => (VOCAB_CLASS[p.dataset] ?? 'everyday') === 'high');
  const everydayPoints = points.filter((p) => (VOCAB_CLASS[p.dataset] ?? 'everyday') === 'everyday');

  const highY2s = highPoints.map((p) => ys(p.c5_mae, maeMin, maeMax));
  const everydayY2s = everydayPoints.map((p) => ys(p.c5_mae, maeMin, maeMax));

  // Bracket extents (C5 / right-column endpoints)
  const highTop    = highY2s.length ? Math.min(...highY2s) : 0;
  const highBottom = highY2s.length ? Math.max(...highY2s) : 0;
  const highMid    = (highTop + highBottom) / 2;

  return (
    <div onMouseEnter={() => logEvent(condition, '', 'chart_hover', { viz_id: 'cross_dataset_slopegraph' })}>
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
        Cross-Dataset MAE: C_LLM vs ConceptGrade
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
        Each line = one dataset · steeper drop = KG adds more value · dashed = p ≥ 0.05
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={1.5} sx={{ fontStyle: 'italic' }}>
        Preliminary observation: KG improvements are stronger in vocabulary-rich academic domains
        than in everyday-language domains.
      </Typography>

      <Box display="flex" justifyContent="center" sx={{ overflowX: 'auto' }}>
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ maxHeight: H + 20, display: 'block' }}>

          {/* Column header labels */}
          <text x={xLeft}  y={14} textAnchor="middle" fontSize={10} fontWeight={700} fill="#dc2626">C_LLM</text>
          <text x={xLeft}  y={25} textAnchor="middle" fontSize={8}  fill="#6b7280">(no KG)</text>
          <text x={xRight} y={14} textAnchor="middle" fontSize={10} fontWeight={700} fill="#16a34a">ConceptGrade</text>
          <text x={xRight} y={25} textAnchor="middle" fontSize={8}  fill="#6b7280">(+ KG)</text>

          {/* Y-axis reference lines */}
          {ticks.map((v) => {
            const y = ys(v, maeMin, maeMax);
            return (
              <g key={v}>
                <line x1={xLeft - 10} x2={xRight + 10} y1={y} y2={y} stroke="#f3f4f6" strokeWidth={1} />
                <text x={xLeft - 13} y={y + 3} textAnchor="end" fontSize={7.5} fill="#9ca3af">
                  {v.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Vertical axis lines */}
          <line x1={xLeft}  y1={PAD_T - 5} x2={xLeft}  y2={H - PAD_B + 5} stroke="#e5e7eb" strokeWidth={1} />
          <line x1={xRight} y1={PAD_T - 5} x2={xRight} y2={H - PAD_B + 5} stroke="#e5e7eb" strokeWidth={1} />

          {/* Slope lines per dataset */}
          {points.map((p, i) => {
            const y1      = ys(p.cllm_mae, maeMin, maeMax);
            const y2      = ys(p.c5_mae,   maeMin, maeMax);
            const color   = SLOPE_COLORS[i % SLOPE_COLORS.length];
            const improved = p.c5_mae < p.cllm_mae;
            const sig      = p.wilcoxon_p < 0.05;
            const delta    = `${improved ? '▼' : '▲'}${Math.abs(p.delta_pct).toFixed(1)}%`;

            return (
              <g key={p.dataset}>
                {/* Slope line */}
                <line x1={xLeft} y1={y1} x2={xRight} y2={y2}
                  stroke={color} strokeWidth={improved ? 2.5 : 1.5}
                  strokeDasharray={sig ? undefined : '5,3'}
                  opacity={0.9} />

                {/* Left endpoint + labels */}
                <circle cx={xLeft} cy={y1} r={5} fill={color} />
                <text x={xLeft - 8} y={y1 - 5}  textAnchor="end" fontSize={9} fontWeight={700} fill={color}>
                  {p.cllm_mae.toFixed(3)}
                </text>
                <text x={xLeft - 8} y={y1 + 6}  textAnchor="end" fontSize={9} fill={color}>
                  {p.shortLabel}
                </text>
                <text x={xLeft - 8} y={y1 + 16} textAnchor="end" fontSize={7.5} fill="#9ca3af">
                  {p.domainLabel}
                </text>

                {/* Right endpoint + delta labels */}
                <circle cx={xRight} cy={y2} r={5} fill={color} />
                <text x={xRight + 8} y={y2 - 5} textAnchor="start" fontSize={9} fontWeight={700} fill={color}>
                  {p.c5_mae.toFixed(3)}
                </text>
                <text x={xRight + 8} y={y2 + 6} textAnchor="start" fontSize={10} fontWeight={700}
                  fill={improved ? '#16a34a' : '#dc2626'}>
                  {delta}
                </text>
                {!sig && (
                  <text x={xRight + 8} y={y2 + 17} textAnchor="start" fontSize={7.5} fill="#9ca3af">
                    n.s.
                  </text>
                )}
              </g>
            );
          })}

          {/* ── Domain Annotation Brackets ────────────────────────────────────────── */}
          {/* Labels use factual domain descriptors (not hypothesis language).     */}
          {/* The hypothesis itself lives in the chart subtitle below.             */}

          {/* "Academic Domains (CS/NN)" bracket — groups Mohler + DigiKlausur */}
          {highPoints.length > 0 && (
            <g>
              {highPoints.length > 1 ? (
                /* Multi-dataset: top tick → vertical spine → bottom tick */
                <path
                  d={`M ${BX - 6} ${highTop} L ${BX} ${highTop} L ${BX} ${highBottom} L ${BX - 6} ${highBottom}`}
                  fill="none" stroke="#64748b" strokeWidth={1.2} strokeLinecap="round"
                />
              ) : (
                <line x1={BX - 6} y1={highTop} x2={BX} y2={highTop}
                  stroke="#64748b" strokeWidth={1.2} />
              )}
              <text x={BX + 5} y={highMid - 5} textAnchor="start" fontSize={7.5} fontWeight={400} fontStyle="italic" fill="#64748b">
                Academic Domains
              </text>
              <text x={BX + 5} y={highMid + 5} textAnchor="start" fontSize={7.5} fontWeight={400} fontStyle="italic" fill="#64748b">
                (CS / NN)
              </text>
            </g>
          )}

          {/* "General Education (K-5 Science)" annotation — one tick per dataset */}
          {everydayPoints.map((p) => {
            const yPos = ys(p.c5_mae, maeMin, maeMax);
            return (
              <g key={`ev-${p.dataset}`}>
                <line x1={BX - 6} y1={yPos} x2={BX} y2={yPos}
                  stroke="#64748b" strokeWidth={1.2} />
                <text x={BX + 5} y={yPos - 3} textAnchor="start" fontSize={7.5} fontWeight={400} fontStyle="italic" fill="#64748b">
                  General Education
                </text>
                <text x={BX + 5} y={yPos + 7} textAnchor="start" fontSize={7.5} fontWeight={400} fontStyle="italic" fill="#64748b">
                  (K-5 Science)
                </text>
              </g>
            );
          })}

        </svg>
      </Box>

      {/* Summary chips */}
      <Box display="flex" gap={0.75} flexWrap="wrap" mt={1.5}>
        {points.map((p, i) => {
          const improved = p.delta_pct > 0;
          const sig      = p.wilcoxon_p < 0.05;
          return (
            <Chip
              key={p.dataset}
              label={`${p.shortLabel}: ${improved ? '▼' : '▲'}${Math.abs(p.delta_pct).toFixed(1)}% MAE${sig ? '' : ' (n.s.)'}`}
              size="small"
              sx={{
                bgcolor:    `${SLOPE_COLORS[i % SLOPE_COLORS.length]}18`,
                color:      SLOPE_COLORS[i % SLOPE_COLORS.length],
                fontWeight: 600,
                fontSize:   10,
                border:     `1px solid ${SLOPE_COLORS[i % SLOPE_COLORS.length]}44`,
              }}
            />
          );
        })}
      </Box>
    </div>
  );
};
