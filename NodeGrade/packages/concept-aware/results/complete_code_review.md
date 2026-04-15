# Complete Code Review

I have reviewed all the functionalities related to the user study instrumentation layer across the frontend React components, the Python analysis script, and the shared utilities. 

Overall, the codebase is structurally sound, and the recent fixes (generic `logEvent`, the `kg_nodes` guard, and the semantic alignment split) have been perfectly integrated. However, I identified two significant issues that need to be addressed before the pilot study.

---

### 1. 🔴 Critical: Broken Mann-Whitney U Tests (`analyze_study_logs.py`)
**Issue:** The script fails to compute p-values for all main metrics (SUS score, Time to answer, etc.). The p-values will silently always output `—`.
**Why:** The `row()` helper function expects `key` to be the *aggregated* key (e.g., `'sus_mean'`). However, it attempts to extract this same aggregated key from the raw, unaggregated `session_metrics` dictionary (which contains `'sus_score'`, not `'sus_mean'`). As a result, `a_vals` and `b_vals` are always empty lists.

**Fix:** Update the `row()` function to accept both an `agg_key` and an optional `raw_key`:

```python
def row(label: str, agg_key: str, raw_key: Optional[str] = None, fmt: str = '.2f'):
    if raw_key:
        a_vals = [m[raw_key] for m in session_metrics if m['condition'] == 'A' and m.get(raw_key) is not None]
        b_vals = [m[raw_key] for m in session_metrics if m['condition'] == 'B' and m.get(raw_key) is not None]
        p = mann_whitney_u(a_vals, b_vals)
    else:
        p = None
        
    a_mean = cond_a.get(agg_key)
    b_mean = cond_b.get(agg_key)
    a_str  = f'{a_mean:{fmt}}' if a_mean is not None else '—'
    b_str  = f'{b_mean:{fmt}}' if b_mean is not None else '—'
    p_str  = f'{p:.4f}' if p is not None else '—'
    sig    = ' *' if (p is not None and p < 0.05) else ('**' if (p is not None and p < 0.01) else '')
    print(f'  {label:<30} {a_str:>10} {b_str:>10} {p_str:>10}{sig}')
```

Then update the call sites to pass the `raw_key`:
```python
row('SUS score (mean)',        'sus_mean',              'sus_score', '.1f')
row('SUS SD',                  'sus_sd',                None,        '.1f') # SD shouldn't run MWU
row('Time to answer (s, mean)','time_to_answer_mean_s', 'time_to_answer_s', '.1f')
```

---

### 2. 🟡 Medium: Inability to Undo Added Concepts (`RubricEditorPanel.tsx`)
**Issue:** If an educator clicks an LRM-flagged chip or a "manual add" button for a concept that is **not** in the original `concepts` list, it is added to `edits` but never appears in the "Current rubric concepts" list. Because the "Pending edits" summary is text-only, there is no UI element available to undo/remove this edit before submitting.

**Fix:** 
1. Make the Click-to-Add chips act as toggles. If `alreadyAdded` is true, the `onClick` handler should filter the concept out of the edits array.
```tsx
<Chip
  label={node.replace(/_/g, ' ')}
  size="small"
  color={alreadyAdded ? 'default' : 'error'}
  variant={alreadyAdded ? 'filled' : 'outlined'}
  icon={alreadyAdded ? <CheckCircleOutlineIcon /> : <AddCircleOutlineIcon />}
  onClick={alreadyAdded 
    ? () => setEdits(prev => prev.filter(e => e.concept_id !== node)) 
    : () => handleEdit(node, node, 'add', 'click_to_add')
  }
  // ...
```
2. Replace the text string in the pending edits `Alert` with closable chips to ensure *any* edit can be undone:
```tsx
{edits.length > 0 && (
  <Alert severity="info" sx={{ mb: 2 }}>
    <Typography variant="body2" sx={{ mb: 1 }}>
      {edits.length} edit(s) pending:
    </Typography>
    <Box display="flex" flexWrap="wrap" gap={1}>
      {edits.map(e => (
        <Chip
          key={e.concept_id}
          label={`${editLabel(e.edit_type)}: ${e.concept_id.replace(/_/g, ' ')}`}
          size="small"
          onDelete={() => setEdits(prev => prev.filter(x => x.concept_id !== e.concept_id))}
        />
      ))}
    </Box>
  </Alert>
)}
```

---

### 3. 🟢 Low: CSS `@keyframes` in inline `sx` (`RubricEditorPanel.tsx`)
**Issue:** You have defined `@keyframes contradicts-pulse` inline inside the `sx` prop of the `sessionContradictsNodes` map. While MUI handles this gracefully in v5, re-defining keyframes dynamically in a loop can sometimes cause minor style injection lag or warnings.
**Recommendation:** This works fine for now, but in future iterations, consider moving the keyframe definition to your global theme or defining it statically outside the component block.

### Summary of Good Practices Observed
- **Type Safety:** `logEvent<T>` generic implementation is spot on and cleanly executed.
- **Data Integrity:** `hasTopologicalGap` strictly checking node intersection (`!stepB.kg_nodes.some(...)`) handles empty node arrays elegantly without throwing errors.
- **Robustness:** `analyze_study_logs.py` GEE modeling properly handles logit links (`Binomial()`) for the pre-registered exploratory analysis.