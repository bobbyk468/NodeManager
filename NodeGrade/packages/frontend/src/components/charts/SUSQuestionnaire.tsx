/**
 * SUSQuestionnaire — System Usability Scale (Brooke, 1996).
 *
 * 10 standardised questions rated 1–5 (Strongly disagree → Strongly agree).
 * Rendered after the study task is submitted; score is computed and logged.
 *
 * Scoring algorithm (standard SUS):
 *   Odd questions  (1,3,5,7,9):  contribution = rating - 1
 *   Even questions (2,4,6,8,10): contribution = 5 - rating
 *   SUS score = sum of contributions × 2.5   (range 0–100)
 *
 * Score interpretation (Bangor et al., 2008):
 *   90–100  Best imaginable   (A+)
 *   80–89   Excellent         (A)
 *   70–79   Good              (B)
 *   60–69   OK                (C)
 *   50–59   Poor              (D)
 *   < 50    Unacceptable      (F)
 *
 * The completed responses + SUS score are logged via studyLogger.logEvent
 * so both the localStorage export and the server-side JSONL file contain them.
 */

import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControlLabel,
  Radio,
  RadioGroup,
  Tooltip,
  Typography,
} from '@mui/material';
import { logEvent } from '../../utils/studyLogger';

// ── SUS items ─────────────────────────────────────────────────────────────────

const SUS_ITEMS: { id: number; text: string; polarity: 'positive' | 'negative' }[] = [
  { id: 1,  text: 'I think that I would like to use this system frequently.',            polarity: 'positive' },
  { id: 2,  text: 'I found the system unnecessarily complex.',                           polarity: 'negative' },
  { id: 3,  text: 'I thought the system was easy to use.',                               polarity: 'positive' },
  { id: 4,  text: 'I think that I would need the support of a technical person to be able to use this system.', polarity: 'negative' },
  { id: 5,  text: 'I found the various functions in this system were well integrated.',  polarity: 'positive' },
  { id: 6,  text: 'I thought there was too much inconsistency in this system.',          polarity: 'negative' },
  { id: 7,  text: 'I would imagine that most people would learn to use this system very quickly.', polarity: 'positive' },
  { id: 8,  text: 'I found the system very cumbersome to use.',                          polarity: 'negative' },
  { id: 9,  text: 'I felt very confident using the system.',                             polarity: 'positive' },
  { id: 10, text: 'I needed to learn a lot of things before I could get going with this system.', polarity: 'negative' },
];

const SCALE_LABELS = ['Strongly\ndisagree', '', 'Neutral', '', 'Strongly\nagree'];

// ── Score helpers ─────────────────────────────────────────────────────────────

function computeSUS(ratings: Record<number, number>): number {
  let total = 0;
  for (const item of SUS_ITEMS) {
    const r = ratings[item.id];
    if (r === undefined) return -1; // incomplete
    total += item.polarity === 'positive' ? r - 1 : 5 - r;
  }
  return Math.round(total * 2.5);
}

function scoreLabel(score: number): { grade: string; label: string; color: string } {
  if (score >= 90) return { grade: 'A+', label: 'Best imaginable', color: '#15803d' };
  if (score >= 80) return { grade: 'A',  label: 'Excellent',        color: '#16a34a' };
  if (score >= 70) return { grade: 'B',  label: 'Good',             color: '#65a30d' };
  if (score >= 60) return { grade: 'C',  label: 'OK',               color: '#d97706' };
  if (score >= 50) return { grade: 'D',  label: 'Poor',             color: '#ea580c' };
  return              { grade: 'F',  label: 'Unacceptable',    color: '#dc2626' };
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  condition: string;
  dataset: string;
  sessionStart: number;
}

export function SUSQuestionnaire({ condition, dataset, sessionStart }: Props) {
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);
  const [susScore, setSusScore] = useState<number | null>(null);

  const allAnswered = SUS_ITEMS.every((item) => ratings[item.id] !== undefined);

  const handleChange = (itemId: number, value: number) => {
    setRatings((prev) => ({ ...prev, [itemId]: value }));
  };

  const handleSubmit = () => {
    const score = computeSUS(ratings);
    setSusScore(score);
    setSubmitted(true);

    const elapsed = Date.now() - sessionStart;
    logEvent(condition, dataset, 'task_submit', {
      sus_responses: ratings,
      sus_score: score,
      sus_instrument: 'SUS-Brooke-1996',
      time_to_complete_ms: elapsed,
      event_subtype: 'sus_questionnaire',
    });
  };

  if (submitted && susScore !== null) {
    const { grade, label, color } = scoreLabel(susScore);
    return (
      <Alert
        severity="success"
        sx={{ mt: 2 }}
        action={
          <Chip
            label={`${susScore} / 100 — ${label} (${grade})`}
            size="small"
            sx={{ fontWeight: 700, bgcolor: color, color: '#fff', fontSize: 12 }}
          />
        }
      >
        SUS questionnaire submitted. Thank you for your feedback!
      </Alert>
    );
  }

  return (
    <Card variant="outlined" sx={{ mt: 3, borderColor: 'secondary.light' }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5, color: 'secondary.main' }}>
          Usability Questionnaire (SUS)
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" mb={2}>
          Please rate each statement from 1 (Strongly disagree) to 5 (Strongly agree).
          There are no right or wrong answers — your honest first impression matters most.
        </Typography>

        {SUS_ITEMS.map((item, index) => (
          <Box key={item.id} mb={2}>
            {index > 0 && <Divider sx={{ mb: 2 }} />}
            <Typography variant="body2" sx={{ mb: 0.75, fontWeight: 500 }}>
              {item.id}. {item.text}
            </Typography>
            <RadioGroup
              row
              value={ratings[item.id] ?? ''}
              onChange={(e) => handleChange(item.id, Number(e.target.value))}
              sx={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}
            >
              {[1, 2, 3, 4, 5].map((val) => (
                <Tooltip
                  key={val}
                  title={SCALE_LABELS[val - 1].replace('\n', ' ')}
                  placement="top"
                  arrow
                >
                  <FormControlLabel
                    value={val}
                    control={
                      <Radio
                        size="small"
                        sx={{
                          color: ratings[item.id] === val ? 'primary.main' : 'action.active',
                        }}
                      />
                    }
                    label={
                      <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.2, textAlign: 'center', whiteSpace: 'pre-line' }}>
                        {val === 1 || val === 5 ? SCALE_LABELS[val - 1] : String(val)}
                      </Typography>
                    }
                    labelPlacement="bottom"
                    sx={{ mx: 0, alignItems: 'center' }}
                  />
                </Tooltip>
              ))}
            </RadioGroup>
          </Box>
        ))}

        <Box mt={2} display="flex" alignItems="center" gap={2}>
          <Button
            variant="contained"
            color="secondary"
            onClick={handleSubmit}
            disabled={!allAnswered}
          >
            Submit SUS responses
          </Button>
          {!allAnswered && (
            <Typography variant="caption" color="text.secondary">
              {SUS_ITEMS.filter((i) => ratings[i.id] === undefined).length} question
              {SUS_ITEMS.filter((i) => ratings[i.id] === undefined).length !== 1 ? 's' : ''} remaining
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

export default SUSQuestionnaire;
