/**
 * ConceptKGPanel — Interactive SVG KG ego-graph.
 *
 * VIS upgrades (Gemini recommendations):
 *   - Draggable nodes (SVG onMouseDown/Move/Up)
 *   - Student state overlay: when a student is selected (DashboardContext.selectedStudentMatchedConcepts),
 *     nodes are colored green (matched) / red (missed) / grey (unrelated)
 *   - MUI Tooltip popovers (richer than SVG <title>)
 *   - Edge type legend tooltip
 */

import CloseIcon from '@mui/icons-material/Close';
import {
  Alert,
  Box,
  CircularProgress,
  IconButton,
  Tooltip,
  Typography,
} from '@mui/material';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import { KGSubgraphResponse, KGNode, KGEdge } from '../../common/visualization.types';
import { useDashboard } from '../../contexts/DashboardContext';

interface Props {
  dataset: string;
  conceptId: string;
  apiBase: string;
  onClose: () => void;
}

const SVG_W = 560;
const SVG_H = 360;
const CX = SVG_W / 2;
const CY = SVG_H / 2;
const LAYOUT_RADIUS = 130;
const NODE_R = 28;

const REL_COLOR: Record<string, string> = {
  PREREQUISITE_FOR: '#7c3aed',
  PRODUCES: '#2563eb',
  HAS_PART: '#0891b2',
  HAS_PROPERTY: '#0d9488',
  IMPLEMENTS: '#059669',
  OPERATES_ON: '#d97706',
  CONTRASTS_WITH: '#dc2626',
  VARIANT_OF: '#9333ea',
};

type NodePos = { x: number; y: number };

function initialLayout(nodes: KGNode[]): Map<string, NodePos> {
  const positions = new Map<string, NodePos>();
  const central = nodes.find((n) => n.is_central);
  if (!central) return positions;
  positions.set(central.id, { x: CX, y: CY });
  const neighbors = nodes.filter((n) => !n.is_central);
  const step = (2 * Math.PI) / Math.max(neighbors.length, 1);
  neighbors.forEach((n, i) => {
    const angle = i * step - Math.PI / 2;
    positions.set(n.id, {
      x: CX + LAYOUT_RADIUS * Math.cos(angle),
      y: CY + LAYOUT_RADIUS * Math.sin(angle),
    });
  });
  return positions;
}

function edgeEndpoints(from: NodePos, to: NodePos, r: number) {
  const dx = to.x - from.x, dy = to.y - from.y;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const ux = dx / len, uy = dy / len;
  return {
    x1: from.x + ux * r, y1: from.y + uy * r,
    x2: to.x - ux * (r + 6), y2: to.y - uy * (r + 6),
    midX: (from.x + to.x) / 2, midY: (from.y + to.y) / 2,
  };
}

/** Determine node fill based on student concept state overlay */
function nodeStateColor(
  node: KGNode,
  matchedSet: Set<string>,
  hasStudentSelected: boolean,
): { fill: string; stroke: string; textColor: string } {
  if (!hasStudentSelected) {
    const base = node.is_central ? '#3b82f6' : node.is_expected ? '#16a34a' : '#6b7280';
    return { fill: base, stroke: base, textColor: base };
  }
  if (matchedSet.has(node.id)) {
    return { fill: '#16a34a', stroke: '#15803d', textColor: '#15803d' };
  }
  if (node.is_expected) {
    return { fill: '#dc2626', stroke: '#b91c1c', textColor: '#b91c1c' };
  }
  return { fill: '#9ca3af', stroke: '#6b7280', textColor: '#6b7280' };
}

function KGGraph({
  data,
  matchedConcepts,
  overlayLoading,
}: {
  data: KGSubgraphResponse;
  matchedConcepts: string[];
  overlayLoading: boolean;
}) {
  const [positions, setPositions] = useState<Map<string, NodePos>>(() => initialLayout(data.nodes));
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const dragState = useRef<{ nodeId: string; offsetX: number; offsetY: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Re-layout when concept changes
  useEffect(() => {
    setPositions(initialLayout(data.nodes));
  }, [data.concept_id]);

  const matchedSet = new Set(matchedConcepts);
  const hasStudentSelected = matchedConcepts.length > 0;
  const nodeMap = new Map<string, KGNode>(data.nodes.map((n) => [n.id, n]));

  const onMouseDown = useCallback((nodeId: string, e: React.MouseEvent<SVGGElement>) => {
    e.preventDefault();
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = SVG_W / rect.width;
    const scaleY = SVG_H / rect.height;
    const pos = positions.get(nodeId);
    if (!pos) return;
    dragState.current = {
      nodeId,
      offsetX: (e.clientX - rect.left) * scaleX - pos.x,
      offsetY: (e.clientY - rect.top) * scaleY - pos.y,
    };
    // Directly mutate the DOM node — dragState is a ref, not state, so reading it in
    // JSX would never trigger a re-render and the cursor style would not update.
    svg.style.cursor = 'grabbing';
  }, [positions]);

  const onMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!dragState.current) return;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = SVG_W / rect.width;
    const scaleY = SVG_H / rect.height;
    const x = Math.max(NODE_R, Math.min(SVG_W - NODE_R, (e.clientX - rect.left) * scaleX - dragState.current.offsetX));
    const y = Math.max(NODE_R, Math.min(SVG_H - NODE_R, (e.clientY - rect.top) * scaleY - dragState.current.offsetY));
    setPositions((prev) => new Map(prev).set(dragState.current!.nodeId, { x, y }));
  }, []);

  const onMouseUp = useCallback(() => {
    dragState.current = null;
    if (svgRef.current) svgRef.current.style.cursor = 'default';
  }, []);

  return (
    <svg
      ref={svgRef}
      width="100%"
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      style={{ display: 'block', maxHeight: 360, cursor: 'default' }}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <defs>
        {Object.entries(REL_COLOR).map(([type, color]) => (
          <marker key={type} id={`arr-${type}`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill={color} />
          </marker>
        ))}
        <marker id="arr-default" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#9ca3af" />
        </marker>
      </defs>

      {/* Edges */}
      {data.edges.map((edge, i) => {
        const fp = positions.get(edge.from), tp = positions.get(edge.to);
        if (!fp || !tp) return null;
        const { x1, y1, x2, y2, midX, midY } = edgeEndpoints(fp, tp, NODE_R);
        const color = REL_COLOR[edge.type] ?? '#9ca3af';
        const isHov = hoveredNode === edge.from || hoveredNode === edge.to;
        return (
          <Tooltip key={i} title={<Box><Typography variant="caption" sx={{ fontWeight: 700 }}>{edge.type.replace(/_/g, ' ')}</Typography><br /><Typography variant="caption">{edge.description}</Typography></Box>} arrow placement="top">
            <g>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={isHov ? 2.5 : 1.5}
                strokeOpacity={isHov ? 1 : 0.65} markerEnd={`url(#arr-${REL_COLOR[edge.type] ? edge.type : 'default'})`} />
              <text x={midX} y={midY - 4} textAnchor="middle" fontSize={8} fill={color} opacity={isHov ? 1 : 0.7}
                style={{ pointerEvents: 'none', fontFamily: 'monospace' }}>
                {edge.type.replace(/_/g, ' ')}
              </text>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="transparent" strokeWidth={14} style={{ cursor: 'default' }} />
            </g>
          </Tooltip>
        );
      })}

      {/* Nodes */}
      {data.nodes.map((node) => {
        const pos = positions.get(node.id);
        if (!pos) return null;
        const { fill, stroke, textColor } = nodeStateColor(node, matchedSet, hasStudentSelected);
        const isHov = hoveredNode === node.id;
        const words = node.name.split(' ');
        return (
          <Tooltip
            key={node.id}
            title={
              <Box sx={{ maxWidth: 220 }}>
                <Typography variant="caption" sx={{ fontWeight: 700, display: 'block' }}>{node.name}</Typography>
                <Typography variant="caption" color="inherit">{node.description}</Typography>
                {hasStudentSelected && (
                  <Typography variant="caption" sx={{ display: 'block', mt: 0.5, fontStyle: 'italic', color: matchedSet.has(node.id) ? '#86efac' : node.is_expected ? '#fca5a5' : '#d1d5db' }}>
                    {matchedSet.has(node.id) ? '✓ Demonstrated by this student' : node.is_expected ? '✗ Expected but not demonstrated' : 'Not required for this question'}
                  </Typography>
                )}
              </Box>
            }
            arrow
            placement="top"
          >
            <g
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onMouseDown={(e) => onMouseDown(node.id, e)}
              style={{ cursor: 'grab' }}
            >
              <circle cx={pos.x} cy={pos.y} r={isHov ? NODE_R + 3 : NODE_R}
                fill={fill} fillOpacity={overlayLoading ? 0.07 : 0.18}
                stroke={stroke} strokeOpacity={overlayLoading ? 0.35 : 1}
                strokeWidth={node.is_central ? 3 : 1.5} />
              {words.map((word, wi) => (
                <text key={wi} x={pos.x}
                  y={pos.y + (wi - (words.length - 1) / 2) * 11}
                  textAnchor="middle" dominantBaseline="central"
                  fontSize={node.is_central ? 9 : 8}
                  fontWeight={node.is_central ? 700 : 400}
                  fill={textColor}
                  style={{ pointerEvents: 'none', userSelect: 'none' }}>
                  {word}
                </text>
              ))}
              {/* Expected badge */}
              {node.is_expected && !node.is_central && (
                <circle cx={pos.x + NODE_R - 5} cy={pos.y - NODE_R + 5} r={5} fill={fill} stroke="#fff" strokeWidth={1} />
              )}
            </g>
          </Tooltip>
        );
      })}
    </svg>
  );
}

export const ConceptKGPanel: React.FC<Props> = ({ dataset, conceptId, apiBase, onClose }) => {
  const { selectedStudentMatchedConcepts, studentOverlayLoading, studentOverlayError } = useDashboard();
  const [data, setData] = useState<KGSubgraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true); setError(null); setData(null);
    fetch(`${apiBase}/api/visualization/datasets/${dataset}/kg/concept/${conceptId}`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<KGSubgraphResponse>; })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [dataset, conceptId, apiBase]);

  const centralNode = data?.nodes.find((n) => n.is_central);
  // Consider overlay "active" both when concepts are loaded AND while loading (legend should
  // switch to student-state mode immediately on click, before the fetch resolves).
  const hasStudentSelected = selectedStudentMatchedConcepts.length > 0 || studentOverlayLoading;

  return (
    <Box sx={{ border: '1px solid #e5e7eb', borderRadius: 2, p: 2, bgcolor: 'background.paper', boxShadow: 2 }}>
      {/* Header */}
      <Box display="flex" alignItems="flex-start" justifyContent="space-between" mb={1}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            KG: {centralNode?.name ?? conceptId.replace(/_/g, ' ')}
          </Typography>
          <Box display="flex" alignItems="center" gap={0.75} flexWrap="wrap">
            <Typography variant="caption" color="text.secondary">
              Drag nodes to explore · hover for details
              {hasStudentSelected && !studentOverlayLoading && !studentOverlayError && ' · student state overlay active'}
            </Typography>
            {/* Subtle spinner while the async /sample/:id XAI fetch is in-flight */}
            {studentOverlayLoading && (
              <>
                <CircularProgress size={10} thickness={5} sx={{ color: 'text.disabled' }} />
                <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>
                  fetching overlay…
                </Typography>
              </>
            )}
            {/* Persistent chip when the XAI fetch failed — respects the instructor's
                cognitive flow by not auto-dismissing like a Snackbar would. */}
            {studentOverlayError && (
              <Box
                component="span"
                sx={{
                  display: 'inline-flex', alignItems: 'center', gap: 0.25,
                  px: 0.75, py: 0.25, borderRadius: 1,
                  bgcolor: 'warning.50', border: '1px solid', borderColor: 'warning.200',
                  color: 'warning.800', fontSize: 10, lineHeight: 1.4,
                }}
              >
                ⚠ overlay unavailable
              </Box>
            )}
          </Box>
        </Box>
        <IconButton size="small" onClick={onClose}><CloseIcon fontSize="small" /></IconButton>
      </Box>

      {/* Legend */}
      <Box display="flex" gap={2} mb={1} flexWrap="wrap">
        {hasStudentSelected ? (
          <>
            {[{ color: '#16a34a', label: 'Demonstrated' }, { color: '#dc2626', label: 'Missing (expected)' }, { color: '#9ca3af', label: 'Not required' }].map(({ color, label }) => (
              <Box key={label} display="flex" alignItems="center" gap={0.5}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color }} />
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </Box>
            ))}
          </>
        ) : (
          <>
            {[{ color: '#3b82f6', label: 'Selected concept' }, { color: '#16a34a', label: 'Expected in rubric' }, { color: '#6b7280', label: 'Related' }].map(({ color, label }) => (
              <Box key={label} display="flex" alignItems="center" gap={0.5}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color }} />
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </Box>
            ))}
          </>
        )}
        <Tooltip title={
          <Box>{Object.entries(REL_COLOR).map(([type, color]) => (
            <Box key={type} display="flex" gap={0.5} alignItems="center">
              <Box sx={{ width: 8, height: 2, bgcolor: color }} />
              <Typography variant="caption">{type.replace(/_/g, ' ')}</Typography>
            </Box>
          ))}</Box>
        } arrow>
          <Typography variant="caption" color="primary" sx={{ cursor: 'help', textDecoration: 'underline dotted' }}>
            Edge types
          </Typography>
        </Tooltip>
      </Box>

      {loading && <Box display="flex" justifyContent="center" py={4}><CircularProgress size={28} /></Box>}
      {error && <Alert severity="error">Could not load KG: {error}</Alert>}
      {!loading && !error && data && (
        <>
          {data.nodes.length === 0
            ? <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>No KG data found for this concept.</Typography>
            : <KGGraph data={data} matchedConcepts={selectedStudentMatchedConcepts} overlayLoading={studentOverlayLoading} />
          }
          <Typography variant="caption" color="text.secondary">
            {data.nodes.length - 1} neighbors · {data.edges.length} relationships
            {hasStudentSelected && ` · showing student #${data.concept_id} state`}
          </Typography>
        </>
      )}
    </Box>
  );
};
