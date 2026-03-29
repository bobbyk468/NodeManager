/**
 * Suite 9 — ConceptGrade End-to-End Scenario Tests
 *
 * Tests the full grading pipeline via the browser:
 *   navigate → fill answer → submit → wait → assert score + depth
 *
 * globalSetup seeds the concept-grade.json template at /ws/student/biology/1/1
 * so every test hits a fresh copy of the biology ConceptGradeNode graph.
 *
 * Score scale: 0–5 (displayed as "X.XX / 5" in the UI)
 * Depth: "surface" | "deep"
 */

import { test, expect, Page } from '@playwright/test'

// ─── Constants ────────────────────────────────────────────────────────────────
const STUDENT_ROUTE = '/ws/student/biology/1/1'
const ANSWER_INPUT   = '#outlined-multiline-static'
const SUBMIT_BTN     = 'button[type="submit"]'
/** How long to wait for Gemini to finish grading (ms) */
const GRADE_TIMEOUT  = 120_000

// ─── Helper ───────────────────────────────────────────────────────────────────
async function grade(page: Page, answer: string) {
  await page.goto(STUDENT_ROUTE)
  await expect(page.locator('h4', { hasText: 'Task:' })).toBeVisible({ timeout: 15_000 })
  await page.locator(ANSWER_INPUT).fill(answer)
  await page.locator(SUBMIT_BTN).click()
  // "Grading..." disappears once the graph finishes
  await expect(page.getByRole('button', { name: /^Submit$/i }))
    .toBeVisible({ timeout: GRADE_TIMEOUT })
}

async function getScore(page: Page): Promise<number> {
  const el = page.locator('h6', { hasText: /overall score/i })
  await expect(el).toBeVisible({ timeout: 8_000 })
  const text = await el.textContent() ?? ''
  const m = text.match(/([\d.]+)\s*\/\s*5/)
  if (!m) throw new Error(`Cannot parse score from: "${text}"`)
  return parseFloat(m[1])
}

async function getDepth(page: Page): Promise<string> {
  const el = page.locator('h6', { hasText: /depth category/i })
  await expect(el).toBeVisible({ timeout: 8_000 })
  // Walk the DOM to get the <p> sibling immediately after the heading
  const depth = await page.evaluate(() => {
    const headings = Array.from(document.querySelectorAll('h6'))
    const heading = headings.find(h => /depth category/i.test(h.textContent ?? ''))
    return heading?.nextElementSibling?.textContent?.trim().toLowerCase() ?? ''
  })
  return depth
}

// ─── Scenarios ────────────────────────────────────────────────────────────────
// All scenarios are in the "biology" domain (template default).
// Score ranges are calibrated to Bloom bands (0–5 scale).
//   L1 Remember  → [0.5, 2.9]
//   L2 Understand→ [1.4, 3.5]
//   L3 Apply     → [2.0, 3.9]
//   L4 Analyze   → [3.1, 5.0]

const scenarios = [
  // ── Bloom L1: Remember ──────────────────────────────────────────────────────
  {
    id: 'BIO-L1-S1',
    level: 1,
    label: 'Remember — one-sentence recall',
    answer:
      'Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of glucose.',
    minScore: 0.5,
    maxScore: 2.9,
    expectedDepth: 'surface'
  },
  {
    id: 'BIO-L1-S2',
    level: 1,
    label: 'Remember — list of reactants/products',
    answer:
      'Photosynthesis takes in carbon dioxide and water and uses light energy to produce glucose and oxygen. It happens in the chloroplasts of plant cells.',
    minScore: 0.5,
    maxScore: 2.9,
    expectedDepth: 'surface'
  },

  // ── Bloom L2: Understand ────────────────────────────────────────────────────
  // Strictly L2: paraphrase with a simple reason — no component breakdown or
  // multi-concept integration (which pushes into L4 territory).
  {
    id: 'BIO-L2-M1',
    level: 2,
    label: 'Understand — paraphrase with simple reason',
    answer:
      'Photosynthesis is how plants make their own food using sunlight. They take in carbon dioxide and water, and use the energy from light to turn these into glucose and oxygen. It is important because it produces the oxygen we breathe and creates the food that almost all living things depend on, either directly or indirectly.',
    minScore: 1.4,
    maxScore: 3.5,
    expectedDepth: 'surface'
  },
  {
    id: 'BIO-L2-M2',
    level: 2,
    label: 'Understand — explain in own words why it matters',
    answer:
      'Photosynthesis is the way green plants use light to produce sugar from carbon dioxide and water. This is important because it is the main way energy from the sun enters the food chain. Plants are eaten by animals, which are eaten by other animals, so without photosynthesis most life on Earth could not exist. It also releases oxygen as a by-product, which animals need to breathe.',
    minScore: 1.4,
    maxScore: 3.5,
    expectedDepth: 'surface'
  },

  // ── Bloom L3: Apply ─────────────────────────────────────────────────────────
  // L3 answers must still address the question (what is photosynthesis + why important)
  // while applying that knowledge to a specific scenario.
  {
    id: 'BIO-L3-M1',
    level: 3,
    label: 'Apply — explain photosynthesis then predict low-light effect',
    answer:
      'Photosynthesis is the process by which plants convert light energy, water and carbon dioxide into glucose and oxygen. It is important because it is the foundation of almost every food chain and it produces the oxygen that animals breathe. In a low-light environment, the rate of photosynthesis slows because less light energy is available to drive the reactions. This means less glucose is produced, so the plant grows more slowly and may eventually show yellowing leaves as chlorophyll breaks down.',
    minScore: 2.0,
    maxScore: 3.9,
    expectedDepth: 'surface'
  },
  {
    id: 'BIO-L3-M2',
    level: 3,
    label: 'Apply — use photosynthesis to explain C3 vs C4 adaptation',
    answer:
      'C4 plants (like maize) use a two-stage carbon fixation strategy to minimise photorespiration in hot, dry climates. CO₂ is first fixed into 4-carbon compounds in mesophyll cells, then shuttled to bundle-sheath cells where it is released at high concentration for the Calvin cycle. This concentrating mechanism keeps RuBisCO saturated with CO₂, so it cannot bind O₂, boosting photosynthetic efficiency. C3 plants lack this adaptation and suffer reduced yields in hot conditions.',
    minScore: 2.5,
    maxScore: 4.2,
    expectedDepth: 'surface'
  },

  // ── Bloom L4: Analyze ───────────────────────────────────────────────────────
  {
    id: 'BIO-L4-L1',
    level: 4,
    label: 'Analyze — coupled light/dark reactions with feedback',
    answer: `Photosynthesis is a two-stage process. The light-dependent reactions occur on the thylakoid membranes where photosystems I and II work in tandem: PSII uses light to excite electrons, which pass down the electron transport chain and drive ATP synthesis via chemiosmosis; PSI then re-energises them to reduce NADP⁺ to NADPH. Water is oxidised to replace the lost electrons, releasing O₂. The light-independent reactions (Calvin cycle) occur in the stroma and use the ATP and NADPH to fix CO₂ into G3P via RuBisCO, which is then used to regenerate RuBP and synthesise glucose. The two stages are tightly coupled: if ATP or NADPH run low, the Calvin cycle slows and a feedback signal reduces the light reactions. This importance is multi-layered: photosynthesis provides the organic carbon that heterotrophs depend on, it has historically shaped Earth's atmosphere from anoxic to oxic, and it represents the primary entry point of solar energy into most terrestrial ecosystems.`,
    minScore: 3.1,
    maxScore: 5.0,
    expectedDepth: 'deep'
  },
  {
    id: 'BIO-L4-L2',
    level: 4,
    label: 'Analyze — evolutionary significance and limiting factors',
    answer: `The evolution of oxygenic photosynthesis approximately 2.7 billion years ago fundamentally transformed Earth's atmosphere and biosphere. The Great Oxidation Event, triggered by cyanobacteria releasing O₂ as a by-product of water splitting, wiped out many anaerobic lineages but enabled the evolution of aerobic respiration, which is far more energetically efficient. Modern plants integrate multiple regulatory mechanisms to maximise photosynthetic efficiency: stomata open to allow CO₂ in but close under drought to prevent water loss, creating a trade-off. The rate of photosynthesis is limited by whichever factor is most scarce — light, CO₂, or temperature (Liebig's Law of the Minimum applied to biochemical kinetics). At the molecular level, RuBisCO's dual affinity for CO₂ and O₂ (photorespiration) is an evolutionary artefact of a high-CO₂ ancestral atmosphere; C4 and CAM plants have independently evolved workarounds, demonstrating convergent evolution driven by the same selection pressure.`,
    minScore: 3.5,
    maxScore: 5.0,
    expectedDepth: 'deep'
  }
]

// ─── Tests ────────────────────────────────────────────────────────────────────
for (const s of scenarios) {
  test(`9.${scenarios.indexOf(s) + 1} [${s.id}] L${s.level} ${s.label}`, async ({ page }) => {
    test.setTimeout(GRADE_TIMEOUT + 20_000)

    await grade(page, s.answer)

    const score = await getScore(page)
    const depth = await getDepth(page)

    console.log(`[${s.id}] score=${score}/5  expected=[${s.minScore}–${s.maxScore}]  depth="${depth}" expected="${s.expectedDepth}"`)

    expect(score, `Score out of range for ${s.id}`).toBeGreaterThanOrEqual(s.minScore)
    expect(score, `Score out of range for ${s.id}`).toBeLessThanOrEqual(s.maxScore)
    expect(depth, `Depth mismatch for ${s.id}`).toBe(s.expectedDepth)
  })
}
