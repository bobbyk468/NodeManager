import { ServerEventPayload } from '@haski/ta-lib'
import { Alert, Box, Button, Chip, Divider, FormControl, Stack, TextField, Tooltip, Typography } from '@mui/material'
import LinearProgress, { linearProgressClasses } from '@mui/material/LinearProgress'
import { styled } from '@mui/material/styles'
import { memo, useCallback, useEffect, useState } from 'react'

/**
 * based on value of successPercentage, the color of the progress bar changes
 */
const BorderLinearProgress = styled(LinearProgress)<{ value: number }>(({ theme, value }) => ({
  height: 10,
  borderRadius: 5,
  [`&.${linearProgressClasses.colorPrimary}`]: {
    backgroundColor: theme.palette.grey[theme.palette.mode === 'light' ? 200 : 800]
  },
  [`& .${linearProgressClasses.bar}`]: {
    borderRadius: 5,
    backgroundColor: value >= 60 ? '#388E3C' : '#308fe8'
  }
}))

const TaskView = ({
  onSubmit,
  outputs,
  question,
  questionImage,
  maxInputChars = Infinity,
  processingPercentage = 0
}: {
  onSubmit: (answer: string) => void
  outputs?: Record<string, ServerEventPayload['outputSet']>
  question: string
  questionImage?: string
  maxInputChars?: number
  processingPercentage?: number
}) => {
  const [error, setError] = useState<string | null>(null)
  const [answer, setAnswer] = useState<string>('')
  const isGrading = processingPercentage > 0 && processingPercentage < 100
  const gradingStage = (outputs?.['grading-stage']?.value as string) || ''
  const validateAnswer = (value: string = answer): boolean => {
    if (value.length < 10) {
      setError('Answer must be at least 10 characters long')
      return false
    } else {
      setError(null)
      return true
    }
  }

  const handleSetAnswer = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value
    setAnswer(newValue)
    validateAnswer(newValue)
  }

  const keyDownHandlerCtrlEnter = useCallback(
    (event: KeyboardEvent): void => {
      if (event.ctrlKey && event.key === 'Enter') {
        if (validateAnswer()) {
          onSubmit(answer)
        }
      }
    },
    [answer, onSubmit]
  )

  const handleSubmit = (event?: React.FormEvent<HTMLFormElement>): void => {
    event?.preventDefault()
    if (validateAnswer()) {
      onSubmit(answer)
    }
  }

  useEffect(() => {
    document.addEventListener('keydown', keyDownHandlerCtrlEnter)

    return () => {
      document.removeEventListener('keydown', keyDownHandlerCtrlEnter)
    }
  }, [keyDownHandlerCtrlEnter])

  return (
    <Stack spacing={2} padding={2}>
      <span id="rewardId" />
      <Typography variant="h4">Task:</Typography>
      {questionImage && (
        <img
          src={questionImage}
          alt="Question"
          style={{
            maxWidth: '100%',
            height: 'auto'
          }}
        />
      )}
      <Typography
        style={{
          maxWidth: '60rem' // Set a maximum width
        }}
        variant="body1"
      >
        {question}
      </Typography>
      <form
        onSubmit={handleSubmit}
        noValidate
        autoComplete="off"
        style={{ width: '100%' }}
      >
        <FormControl fullWidth error={!!error}>
          <Stack spacing={2}>
            <TextField
              id="outlined-multiline-static"
              label="Answer"
              multiline
              error={!!error}
              helperText={error}
              rows={6}
              placeholder="Enter your answer here..."
              onChange={handleSetAnswer}
            />
            <Stack direction="row" spacing={2} alignItems="center">
              <Button variant="contained" type="submit" disabled={isGrading}>
                {isGrading ? 'Grading...' : 'Submit'}
              </Button>
              {!isGrading && (
                <Typography variant="caption">
                  Note: Grading can take up to a minute. Please do not reload the page.
                </Typography>
              )}
            </Stack>
            {isGrading && (
              <Box sx={{ mt: 1 }}>
                <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                  <Typography variant="caption" color="primary">
                    {gradingStage || 'Processing...'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {processingPercentage}%
                  </Typography>
                </Stack>
                <LinearProgress variant="determinate" value={processingPercentage} sx={{ borderRadius: 1 }} />
              </Box>
            )}
            {/* Map over all outputs and display them */}
            {outputs &&
              Object.values(outputs).map((out) => {
                switch (out.type) {
                  case 'text':
                    return (
                      <>
                        <Typography variant="h6">{out.label}</Typography>
                        <Typography
                          style={{
                            maxWidth: '50rem' // Set a maximum width
                          }}
                          variant="body1"
                        >
                          {out.value}
                        </Typography>
                        <Typography variant="body2">
                          Please note that answers generated by the system may be
                          incorrect or contain misleading information.
                        </Typography>
                      </>
                    )
                  case 'score': {
                    const numValue =
                      typeof out.value === 'number'
                        ? out.value
                        : parseFloat(out.value as string)
                    if (isNaN(numValue)) {
                      console.error('score output.value is not numeric:', out.value)
                      return null
                    }
                    // ConceptGrade returns 0–1; scale to 0–5 for display
                    const displayValue = numValue <= 1 ? numValue * 5 : numValue
                    const barValue = (displayValue / 5) * 100
                    return (
                      <>
                        {barValue >= 60 && <Alert severity="success">Passed!</Alert>}
                        <Typography variant="h6">
                          {out.label}: {displayValue.toFixed(2)} / 5
                        </Typography>
                        {barValue >= 0 && barValue <= 100 && (
                          <BorderLinearProgress variant="determinate" value={barValue} />
                        )}
                      </>
                    )
                  }
                  case 'classifications':
                    // assert that output.value is an array of strings
                    if (!Array.isArray(out.value)) {
                      console.error(
                        'output.value is not an array, but of type: ',
                        typeof out.value
                      )
                      return null
                    }
                    // display chips with classifications
                    return (
                      <>
                        <Typography variant="h6">Classifications:</Typography>
                        {out.value.map((classification) => (
                          <Typography variant="body1" key={classification}>
                            {classification}
                          </Typography>
                        ))}
                      </>
                    )
                  case 'feedback': {
                    let report: any = null
                    try { report = JSON.parse(out.value as string) } catch { return null }
                    if (!report) return null
                    if (report.error) {
                      return (
                        <Alert severity="error" key="feedback-error">
                          <Typography variant="body2" fontWeight={600}>Grading pipeline error</Typography>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', mt: 0.5 }}>{report.error}</Typography>
                        </Alert>
                      )
                    }
                    const blooms = report.blooms || {}
                    const solo = report.solo || {}
                    const miscList: any[] = report.misconceptions?.misconceptions || []
                    const concepts: any[] = report.concept_graph?.concepts || []
                    const overallScore: number = report.overall_score ?? 0
                    const pureLlmScore: number | null = report.pure_llm_score != null ? report.pure_llm_score : null
                    const scoreRationale: string | null = report.score_rationale || null
                    const scoreMissing: string | null = report.score_missing || null
                    const bloomsReasoning: string | null = blooms.reasoning || null
                    const soloReasoning: string | null = solo.reasoning || null
                    const severityColor = (s: string) =>
                      s === 'critical' ? 'error' : s === 'moderate' ? 'warning' : 'default'
                    return (
                      <Box sx={{ mt: 1 }}>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant="h6" gutterBottom>Detailed Feedback</Typography>

                        {/* ConceptGrade vs Pure LLM comparison panel */}
                        {pureLlmScore != null && (
                          <Box sx={{ mb: 2, p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
                            <Typography variant="subtitle2" gutterBottom>Score Comparison</Typography>
                            <Stack direction="row" spacing={3} alignItems="center">
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" color="text.secondary">ConceptGrade (KG-grounded)</Typography>
                                <Typography variant="h5" color="primary.main" fontWeight={700}>
                                  {(overallScore * 5).toFixed(2)} / 5
                                </Typography>
                                <BorderLinearProgress value={(overallScore * 5 / 5) * 100} variant="determinate" />
                              </Box>
                              <Divider orientation="vertical" flexItem />
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" color="text.secondary">Pure LLM (zero-shot)</Typography>
                                <Typography variant="h5" color="text.secondary" fontWeight={700}>
                                  {(pureLlmScore * 5).toFixed(2)} / 5
                                </Typography>
                                <BorderLinearProgress value={(pureLlmScore * 5 / 5) * 100} variant="determinate" sx={{ '& .MuiLinearProgress-bar': { bgcolor: 'text.disabled' } }} />
                              </Box>
                              <Box sx={{ textAlign: 'center', minWidth: 80 }}>
                                <Typography variant="caption" color="text.secondary">Difference</Typography>
                                <Typography
                                  variant="h6"
                                  fontWeight={700}
                                  color={overallScore > pureLlmScore ? 'success.main' : overallScore < pureLlmScore ? 'error.main' : 'text.secondary'}
                                >
                                  {overallScore > pureLlmScore ? '+' : ''}{((overallScore - pureLlmScore) * 5).toFixed(2)}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block">
                                  {overallScore > pureLlmScore ? 'KG improves score' : overallScore < pureLlmScore ? 'LLM scores higher' : 'Equal'}
                                </Typography>
                              </Box>
                            </Stack>
                          </Box>
                        )}

                        {/* Cognitive depth chips */}
                        <Stack direction="row" spacing={1} sx={{ mb: 1 }} flexWrap="wrap">
                          <Tooltip title="Bloom's Revised Taxonomy level">
                            <Chip label={`Bloom's: ${blooms.label || 'N/A'} (L${blooms.level ?? '?'})`} color="primary" variant="outlined" size="small" />
                          </Tooltip>
                          <Tooltip title="SOLO Taxonomy level">
                            <Chip label={`SOLO: ${solo.label || 'N/A'} (L${solo.level ?? '?'})`} color="secondary" variant="outlined" size="small" />
                          </Tooltip>
                          <Chip label={`${concepts.length} concept${concepts.length !== 1 ? 's' : ''} identified`} variant="outlined" size="small" />
                        </Stack>

                        {/* Chain-of-Thought reasoning */}
                        {(bloomsReasoning || soloReasoning) && (
                          <Box sx={{ mb: 2, p: 1.5, bgcolor: 'primary.50', border: '1px solid', borderColor: 'primary.100', borderRadius: 1 }}>
                            <Typography variant="subtitle2" color="primary.dark" gutterBottom>Assessment reasoning</Typography>
                            {bloomsReasoning && (
                              <Typography variant="body2" sx={{ mb: soloReasoning ? 0.5 : 0 }}>
                                <strong>Bloom's:</strong> {bloomsReasoning}
                              </Typography>
                            )}
                            {soloReasoning && (
                              <Typography variant="body2">
                                <strong>SOLO:</strong> {soloReasoning}
                              </Typography>
                            )}
                          </Box>
                        )}

                        {/* Misconceptions */}
                        {miscList.length > 0 && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              ⚠ {miscList.length} misconception{miscList.length !== 1 ? 's' : ''} detected
                            </Typography>
                            <Stack spacing={1}>
                              {miscList.map((m: any, i: number) => (
                                <Alert key={i} severity={m.severity === 'critical' ? 'error' : m.severity === 'moderate' ? 'warning' : 'info'} variant="outlined">
                                  <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 0.5 }}>
                                    <Chip label={m.severity} color={severityColor(m.severity) as any} size="small" />
                                    {m.type && (
                                      <Chip label={m.type} variant="outlined" size="small" />
                                    )}
                                    {m.taxonomy_match && m.taxonomy_match !== 'novel' && (
                                      <Tooltip title="Known misconception pattern from CS taxonomy">
                                        <Chip label={m.taxonomy_match} color="default" size="small" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }} />
                                      </Tooltip>
                                    )}
                                  </Stack>
                                  <Typography variant="body2" fontWeight={600}>{m.explanation}</Typography>
                                  {m.remediation_hint && (
                                    <Typography variant="body2" sx={{ mt: 0.5, color: 'text.secondary' }}>
                                      💡 {m.remediation_hint}
                                    </Typography>
                                  )}
                                </Alert>
                              ))}
                            </Stack>
                          </Box>
                        )}

                        {/* Score rationale */}
                        {scoreRationale && (
                          <Box sx={{ p: 1.5, bgcolor: 'grey.50', border: '1px solid', borderColor: 'grey.200', borderRadius: 1, mb: 1 }}>
                            <Typography variant="subtitle2" gutterBottom>Score rationale</Typography>
                            <Typography variant="body2">{scoreRationale}</Typography>
                            {scoreMissing && (
                              <Typography variant="body2" sx={{ mt: 0.5, color: 'text.secondary' }}>
                                To improve further: {scoreMissing}
                              </Typography>
                            )}
                          </Box>
                        )}

                        {/* Strengths and gaps */}
                        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                          {/* Positives */}
                          <Box sx={{ flex: 1, p: 1.5, bgcolor: 'success.50', border: '1px solid', borderColor: 'success.200', borderRadius: 1 }}>
                            <Typography variant="subtitle2" color="success.dark" gutterBottom>What you did well</Typography>
                            {blooms.level >= 4 && (
                              <Typography variant="body2">✓ Demonstrates higher-order thinking ({blooms.label})</Typography>
                            )}
                            {blooms.level >= 2 && blooms.level < 4 && (
                              <Typography variant="body2">✓ Shows conceptual understanding beyond recall</Typography>
                            )}
                            {solo.level >= 4 && (
                              <Typography variant="body2">✓ Integrates multiple concepts into a coherent explanation</Typography>
                            )}
                            {solo.level >= 2 && solo.level < 4 && (
                              <Typography variant="body2">✓ Covers multiple relevant concepts</Typography>
                            )}
                            {concepts.length >= 3 && (
                              <Typography variant="body2">✓ Identified {concepts.length} distinct concepts</Typography>
                            )}
                            {miscList.length === 0 && (
                              <Typography variant="body2">✓ No misconceptions detected</Typography>
                            )}
                            {miscList.length > 0 && miscList.filter((m: any) => m.severity === 'critical').length === 0 && (
                              <Typography variant="body2">✓ No critical misconceptions</Typography>
                            )}
                            {blooms.level < 2 && solo.level < 2 && concepts.length < 3 && miscList.length > 0 && (
                              <Typography variant="body2" color="text.secondary">— Submit a more detailed answer to see strengths</Typography>
                            )}
                          </Box>

                          {/* Negatives */}
                          <Box sx={{ flex: 1, p: 1.5, bgcolor: 'warning.50', border: '1px solid', borderColor: 'warning.200', borderRadius: 1 }}>
                            <Typography variant="subtitle2" color="warning.dark" gutterBottom>Gaps in understanding</Typography>
                            {overallScore >= 0.9 ? (
                              <Typography variant="body2" color="text.secondary">— No major gaps detected at this level</Typography>
                            ) : (
                              <>
                                {blooms.level < 2 && (
                                  <Typography variant="body2">✗ Answer stays at recall level — explain <em>how</em> and <em>why</em>, not just <em>what</em></Typography>
                                )}
                                {blooms.level >= 2 && blooms.level < 4 && (
                                  <Typography variant="body2">✗ Missing analysis — add trade-offs, comparisons, or worked examples</Typography>
                                )}
                                {blooms.level === 4 && (
                                  <Typography variant="body2">✗ Not yet at evaluation level — justify design choices or critique alternative approaches</Typography>
                                )}
                                {solo.level < 2 && (
                                  <Typography variant="body2">✗ Only one concept addressed — broaden the scope of your answer</Typography>
                                )}
                                {solo.level >= 2 && solo.level < 4 && (
                                  <Typography variant="body2">✗ Concepts listed but not connected — show how ideas relate to each other</Typography>
                                )}
                                {solo.level === 4 && (
                                  <Typography variant="body2">✗ Not yet at extended abstract level — generalise your argument beyond this specific topic</Typography>
                                )}
                                {concepts.length === 0 && (
                                  <Typography variant="body2">✗ No explicit concepts extracted — name and define key terms clearly</Typography>
                                )}
                                {concepts.length > 0 && concepts.length < 3 && (
                                  <Typography variant="body2">✗ Only {concepts.length} concept{concepts.length !== 1 ? 's' : ''} identified — mention more relevant ideas</Typography>
                                )}
                                {miscList.filter((m: any) => m.severity === 'critical').length > 0 && (
                                  <Typography variant="body2" color="error.main">✗ {miscList.filter((m: any) => m.severity === 'critical').length} critical misconception{miscList.filter((m: any) => m.severity === 'critical').length !== 1 ? 's' : ''} — see details above</Typography>
                                )}
                                {blooms.level >= 5 && solo.level >= 5 && miscList.length === 0 && (
                                  <Typography variant="body2" color="text.secondary">— No major gaps detected at this level</Typography>
                                )}
                              </>
                            )}
                          </Box>
                        </Stack>
                      </Box>
                    )
                  }
                }
              })}
          </Stack>
        </FormControl>
      </form>
    </Stack>
  )
}
export default memo(TaskView)
