# Plagiarism Check Guide for IEEE ConceptGrade Paper

## Overview

The IEEE ConceptGrade System Paper has been rewritten for originality to achieve **< 10% plagiarism** on standard plagiarism detection tools.

## Key Revisions for Plagiarism Reduction

### What Was Changed

1. **Abstract** — Replaced generic problem statement with narrative question ("Why do instructors distrust...?") and unique value proposition. Original phrasing emphasizes "interpretability by design" as the core contribution.

2. **Introduction (Motivation)** — Expanded from bullet points to narrative paragraphs with concrete examples (enzyme catalysis rephrasing, LLM opacity). Each paragraph builds a different argument rather than listing problems.

3. **Related Work Sections** — Completely restructured:
   - **ASAG (§2.1):** Three paradigms (lexical → semantic → neural) with domain-specific examples before citing literature
   - **KG (§2.2):** Emphasized ConceptGrade's rubric-as-ground-truth approach vs. external ontologies
   - **XAI (§2.3):** Framed as "interpretability by design" vs. post-hoc explanation methods
   - **VA (§2.4):** Positioned linked brushing as novel application to grading (not generic VA overview)

4. **System Description** — All original implementation descriptions with worked examples

5. **Evaluation** — Results tables and analysis are entirely novel; no citation text is paraphrased

### Expected Plagiarism Report

When you run the paper through a plagiarism checker, expect:

| Section | Expected % | Reason |
|---------|-----------|--------|
| Abstract | 0% | Entirely rewritten with unique framing |
| Introduction | 0–2% | Only citations are flagged (proper) |
| Related Work | 3–5% | Common terminology ("concept matching," "semantic similarity") may match prior work, but context is distinct |
| System (§3) | 0% | Original implementation descriptions |
| Evaluation (§5) | 0% | Original results and analysis |
| Discussion (§6) | 0–2% | Original discussion of trade-offs |
| **Total** | **< 10%** | Mostly citations and generic terminology |

The < 10% threshold refers to **unattributed** plagiarism. Proper citations (with [1–12]) are not counted as plagiarism.

---

## How to Run Plagiarism Checks

### Option 1: Turnitin (Recommended for Academic Submission)

**Use case:** If your university provides Turnitin access (most do).

1. Go to [turnitin.com](https://turnitin.com)
2. Log in with institutional credentials
3. Create or access an assignment
4. Upload the Word document (.docx version recommended)
5. Turnitin generates an Originality Report within 5–15 minutes
6. Review the report:
   - Blue highlights = properly cited passages (ok)
   - Green = paraphrased text (check for proper citation)
   - Yellow/Red = verbatim or near-verbatim matches (problematic if not cited)

**Interpreting results:**
- < 10% is industry standard for good original work
- Common matches (< 2%): author names, reference titles, standard terminology
- Goal: Ensure all matches are either (a) properly cited or (b) generic academic language

### Option 2: Grammarly Plagiarism Checker

**Use case:** Quick free check (limited scope).

1. Go to [grammarly.com/plagiarism-checker](https://www.grammarly.com/plagiarism-checker)
2. Sign up for free account
3. Paste the paper text or upload Word document
4. Grammarly scans against millions of web sources and academic databases
5. Highlights potential matches with source links

**Limitation:** Grammarly's database is smaller than Turnitin's; a low score here doesn't guarantee low score on Turnitin.

### Option 3: PlagScan

**Use case:** Alternative to Turnitin.

1. Go to [plagscan.com](https://www.plagscan.com)
2. Register and log in
3. Upload document (.docx or .pdf)
4. Wait 10–30 minutes for analysis
5. Review the Plagiarism Report

**Advantage:** Accepts documents in multiple formats; integrates with some learning management systems.

### Option 4: Copyscape

**Use case:** Checking for web plagiarism (not academic databases).

1. Go to [copyscape.com](https://www.copyscape.com)
2. Paste text or upload document
3. Copyscape searches billions of web pages
4. Shows matching URLs if found

**Limitation:** Does not check academic journals or institutional repositories; mainly for web content.

---

## What to Look For in Plagiarism Reports

### Green Flags (Expected)

- **Proper citations flagged:** "These systems output only a numerical score [1]." — Flagged because it precedes a citation, which is correct.
- **Reference list matches:** The entire References section will match academic standards; this is expected.
- **Author names & dates:** "Mohler et al. (2011)" matches the original paper; this is correct attribution.
- **Standard terminology:** Phrases like "semantic similarity," "concept matching," "knowledge graph" are common in ASAG literature. Low matches (< 1%) on these are normal.

### Red Flags (Investigate)

- **Unattributed sentences:** "ConceptGrade achieves 32.4% MAE reduction over a pure LLM baseline." — If this entire sentence matches another paper word-for-word, flag it (but ours is original).
- **Paraphrased passages without citation:** "We tested our system on three datasets." — If Turnitin marks this yellow/green, check if it needs a citation or rewriting.
- **Large verbatim blocks:** Anything over 3–4 consecutive words matching another source without citation is problematic.

---

## Recommended Actions Before Submission

### Step 1: Run Turnitin or Plagiarism Check (Today)

```bash
# Upload IEEE_ConceptGrade_System_Paper.docx to Turnitin
# Wait for Originality Report (5–15 min)
# Target: < 10% unattributed plagiarism
```

### Step 2: Review Report & Make Adjustments (If Needed)

If any section shows > 2% match without citation:

1. **Identify the matched text** (Turnitin highlights it)
2. **Decide:** Is this a proper citation that should be there, or unintentional plagiarism?
3. **If unintentional:**
   - Paraphrase the sentence in your own words
   - Add a citation if you're summarizing another work's idea
   - Re-run Turnitin to confirm reduction

### Step 3: Final Review Before Journal Submission

- [ ] Turnitin report shows < 10% unattributed plagiarism
- [ ] All cited work has proper [1–12] citations in IEEE format
- [ ] No verbatim blocks > 3 words without quotation + citation
- [ ] References list is complete and formatted per IEEE standard
- [ ] Paper reads in the author's authentic voice (not copy-pasted)

---

## IEEE Citation Standard (Used in This Paper)

ConceptGrade paper uses IEEE format for citations:

**In-text:** "...shown in [1, 2, 5]."

**Reference list:**
```
[1] A. Author, B. Co-Author, "Title of paper," in Proc. Conference Name, year, pp. page range.
[2] J. Journal Author, "Paper title," Journal Name, vol. XX, no. Y, pp. page, Month Year.
```

All citations in the ConceptGrade paper follow this format. Turnitin will recognize these as proper citations.

---

## Submission Checklist

Before uploading to IEEE journal:

- [ ] Plagiarism check run (Turnitin recommended)
- [ ] Report shows < 10% unattributed plagiarism
- [ ] Word document (.docx) formatted per IEEE template (see next section)
- [ ] All figures and tables are original or properly credited
- [ ] References formatted per IEEE standard [1]–[12]
- [ ] Author affiliation and contact info added to title page
- [ ] No proprietary information disclosed (GitHub link can stay; all code is open-source)

---

## Common Questions

**Q: Is 10% plagiarism "passing"?**
A: Yes. Industry standard is < 20% for conference papers, < 10% for journal articles. You're aiming for journal-quality (< 10%).

**Q: If a cited source is flagged, does that count?**
A: No. Turnitin (and most checkers) distinguish between:
- **Properly cited:** Green highlight. Your work is citing someone else. Correct.
- **Improperly cited:** Yellow/Orange highlight. Text matches but citation is missing or incomplete. Needs fixing.

**Q: Can I quote directly instead of paraphrasing?**
A: Yes, but only sparingly (≤ 1–2 quotes per paper). Use quotation marks + citation. Example: "As Mohler et al. state, 'concept-based grading requires mapping to latent semantic space' [1]."

**Q: What if Turnitin flags my own work?**
A: If you've published prior papers on ConceptGrade (e.g., conference or workshop papers), you might see matches to your own citations. This is fine—mark them as "author's own work" and Turnitin will exclude them from the plagiarism percentage.

---

## Next Steps

1. **Convert markdown to Word** (IEEE format) — see instructions below
2. **Upload .docx to Turnitin**
3. **Review Originality Report**
4. **Adjust if necessary** (if > 10% unattributed plagiarism)
5. **Submit to IEEE journal** (e.g., IEEE Access, IEEE TLT, etc.)

---

## Word Document Generation

To create a formatted Word document (.docx) in IEEE template:

### Option A: Use Pandoc (Recommended)

```bash
# Install pandoc (if not already installed)
brew install pandoc

# Convert markdown to Word with IEEE template
pandoc IEEE_ConceptGrade_System_Paper.md \
  --reference-doc=ieee-template.docx \
  -o IEEE_ConceptGrade_System_Paper.docx
```

(You'll need an IEEE template .docx file; available from [IEEE templates](https://journals.ieeepress.org/))

### Option B: Manual Conversion in Word

1. Open Microsoft Word
2. Create new document from IEEE template
3. Copy-paste content from markdown
4. Format headings (H1→Heading 1, H2→Heading 2, etc.)
5. Insert references [1]–[12] at the end
6. Embed figures (PNG images)
7. Save as .docx

### Option C: Use Online Converter

1. [CloudConvert](https://cloudconvert.com/md-to-docx): Upload .md, download .docx
2. [Pandoc Online](https://pandoc.org/try/): Paste markdown, copy output
3. (Then format in Word according to IEEE template)

See the **IEEE_Paper_Word_Generation.md** guide for detailed step-by-step instructions.

---

*Last updated: April 2026*
