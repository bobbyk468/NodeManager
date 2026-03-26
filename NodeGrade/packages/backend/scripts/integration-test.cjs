/**
 * End-to-end checks for:
 * 1) DB-backed runGraph (path + answer; graph JSON from PostgreSQL)
 * 2) WeightedScoreNode (no LLM)
 * 3) LLM JSON mode via MODEL_WORKER_URL (LiteLLM + Groq — start LiteLLM with GROQ_API_KEY in env)
 *
 * Usage (from repo root):
 *   cd NodeManager/NodeGrade
 *   corepack yarn workspace backend exec node scripts/integration-test.cjs
 *
 * Prerequisites:
 *   - PostgreSQL running, DATABASE_URL in packages/backend/.env
 *   - Backend on PORT/WS_PORT (default 5001 in .env)
 *   - LiteLLM on MODEL_WORKER_URL (default http://localhost:8000) with GROQ_API_KEY set for the LLM test
 */

const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

const REPORT_PATH = path.join(__dirname, '../../../reports/integration-results.json');

const { PrismaClient } = require('@prisma/client');
const { io } = require('socket.io-client');

const {
  LGraph,
  LGraphRegisterCustomNodes,
  AnswerInputNode,
  Textfield,
  ConcatString,
  PromptMessage,
  LLMNode,
  OutputNode,
  NumberNode,
  WeightedScoreNode,
} = require('@haski/ta-lib');

LGraphRegisterCustomNodes();

const TEST_PATH_LLM = 'integration-test-llm';
const TEST_PATH_WEIGHTED = 'integration-test-weighted';

function buildLlmGraphJson() {
  const g = new LGraph();
  const tf = new Textfield();
  tf.properties.value =
    'You are an automatic grader. Respond with ONLY a JSON object (no markdown) with keys "score" (0-100 number) and "feedback" (short string).';

  const ans = new AnswerInputNode();
  const concat = new ConcatString();
  concat.properties.space = true;

  const pm = new PromptMessage();
  pm.properties.value = { role: 'user', content: '' };

  const llm = new LLMNode();
  llm.properties.model = 'groq/llama-3.1-8b-instant';
  llm.properties.max_tokens = 256;
  llm.properties.temperature = 0.3;
  llm.properties.top_p = 0.9;
  llm.properties.available_models = ['groq/llama-3.1-8b-instant'];
  llm.properties.available_model_sources = {
    'groq/llama-3.1-8b-instant': 'local',
  };

  const out = new OutputNode();
  out.properties.type = 'text';
  out.properties.label = 'llm_json';

  g.add(tf);
  g.add(ans);
  g.add(concat);
  g.add(pm);
  g.add(llm);
  g.add(out);

  tf.connect(0, concat, 0);
  ans.connect(0, concat, 1);
  concat.connect(0, pm, 0);
  pm.connect(0, llm, 0);
  llm.connect(0, out, 0);

  return JSON.stringify(g.serialize());
}

function buildWeightedGraphJson() {
  const g = new LGraph();
  const n1 = new NumberNode();
  n1.properties.value = 80;
  const n2 = new NumberNode();
  n2.properties.value = 0.85;
  const w = new WeightedScoreNode();
  w.properties.weight_1 = 0.5;
  w.properties.weight_2 = 0.5;
  w.properties.normalize_to_100 = true;
  const out = new OutputNode();
  out.properties.type = 'score';
  out.properties.label = 'weighted';

  g.add(n1);
  g.add(n2);
  g.add(w);
  g.add(out);

  n1.connect(0, w, 0);
  n2.connect(0, w, 1);
  w.connect(0, out, 0);

  return JSON.stringify(g.serialize());
}

async function seedGraph(prisma, pathname, graphStr) {
  const existing = await prisma.graph.findFirst({ where: { path: pathname } });
  if (existing) {
    await prisma.graph.update({
      where: { path: pathname },
      data: { graph: graphStr },
    });
  } else {
    await prisma.graph.create({
      data: { path: pathname, graph: graphStr },
    });
  }
  console.log(`Seeded graph in DB: ${pathname}`);
}

function runGraphSocket(baseUrl, pathname, answer) {
  return new Promise((resolve, reject) => {
    const socket = io(baseUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: false,
      timeout: 120_000,
    });

    const outputs = [];
    const errors = [];

    socket.on('connect', () => {
      socket.emit('runGraph', {
        path: pathname,
        answer: answer ?? 'Test answer.',
      });
    });

    socket.on('outputSet', (payload) => {
      outputs.push(payload);
    });

    socket.on('nodeErrorOccured', (payload) => {
      errors.push(payload);
    });

    socket.on('error', (e) => {
      errors.push({ socketError: e });
    });

    socket.on('connect_error', (e) => {
      reject(e);
    });

    socket.on('graphFinished', () => {
      socket.close();
      resolve({ outputs, errors });
    });

    setTimeout(() => {
      socket.close();
      reject(new Error('Timeout waiting for graphFinished (120s)'));
    }, 120_000);
  });
}

async function checkLiteLlm(modelWorkerUrl) {
  try {
    const r = await fetch(`${modelWorkerUrl.replace(/\/$/, '')}/v1/models`);
    return r.ok;
  } catch {
    return false;
  }
}

async function main() {
  const prisma = new PrismaClient();
  const port = process.env.PORT || '5001';
  const baseUrl = `http://localhost:${port}`;
  const modelWorkerUrl =
    process.env.MODEL_WORKER_URL || 'http://localhost:8000';

  console.log(`Backend URL: ${baseUrl}`);
  console.log(`MODEL_WORKER_URL: ${modelWorkerUrl}`);

  const report = {
    timestamp: new Date().toISOString(),
    backendUrl: baseUrl,
    tests: {
      weightedScore: { status: 'pending', value: null, expected: 82.5, nodeErrors: [] },
      llmJson: { status: 'pending', value: null, nodeErrors: [] },
    },
    success: false,
  };

  await seedGraph(prisma, TEST_PATH_WEIGHTED, buildWeightedGraphJson());
  await seedGraph(prisma, TEST_PATH_LLM, buildLlmGraphJson());

  console.log('\n--- Test 1: WeightedScore (no external LLM) ---');
  const w = await runGraphSocket(baseUrl, TEST_PATH_WEIGHTED, 'ignored');
  console.log('outputs:', JSON.stringify(w.outputs, null, 2));
  if (w.errors.length) console.log('errors:', w.errors);
  const weightedVal = w.outputs.find((o) => o.label === 'weighted')?.value;
  const wNum = typeof weightedVal === 'number' ? weightedVal : parseFloat(weightedVal);
  if (!Number.isFinite(wNum) || Math.abs(wNum - 82.5) > 0.01) {
    console.error(
      `FAIL: expected weighted score ~82.5, got ${JSON.stringify(weightedVal)}`,
    );
    process.exitCode = 1;
    report.tests.weightedScore = { status: 'failed', value: wNum, expected: 82.5, nodeErrors: w.errors };
  } else {
    console.log('PASS: weighted score ~82.5');
    report.tests.weightedScore = { status: 'passed', value: wNum, expected: 82.5, nodeErrors: w.errors };
  }

  const llmUp = await checkLiteLlm(modelWorkerUrl);
  console.log('\n--- Test 2: LLM JSON (Groq via LiteLLM) ---');
  if (!llmUp) {
    console.warn(
      `SKIP: LiteLLM not reachable at ${modelWorkerUrl}/v1/models. Start e.g.:\n` +
        `  export GROQ_API_KEY="your-key"\n` +
        `  litellm --model groq/llama-3.1-8b-instant --port 8000`,
    );
    report.tests.llmJson = { status: 'skipped', reason: `LiteLLM not reachable at ${modelWorkerUrl}/v1/models`, value: null, nodeErrors: [] };
  } else {
    try {
      const r = await runGraphSocket(
        baseUrl,
        TEST_PATH_LLM,
        'Photosynthesis turns light energy into chemical energy stored in glucose.',
      );
      console.log('outputs:', JSON.stringify(r.outputs, null, 2));
      if (r.errors.length) console.log('node errors:', r.errors);

      const textOut = r.outputs.find((o) => o.label === 'llm_json');
      const raw = textOut?.value;
      if (typeof raw !== 'string') {
        console.error('FAIL: expected string output from LLM path');
        process.exitCode = 1;
        report.tests.llmJson = { status: 'failed', reason: 'expected string output', value: raw, nodeErrors: r.errors };
      } else {
        const parsed = JSON.parse(raw);
        if (typeof parsed.score !== 'number' || typeof parsed.feedback !== 'string') {
          console.error('FAIL: LLM output JSON missing score/feedback', raw);
          process.exitCode = 1;
          report.tests.llmJson = { status: 'failed', reason: 'missing score/feedback keys', value: parsed, nodeErrors: r.errors };
        } else {
          console.log('PASS: received JSON with score and feedback');
          report.tests.llmJson = { status: 'passed', value: parsed, nodeErrors: r.errors };
        }
      }
    } catch (e) {
      console.error('FAIL:', e.message);
      process.exitCode = 1;
      report.tests.llmJson = { status: 'failed', reason: e.message, value: null, nodeErrors: [] };
    }
  }

  report.success = process.exitCode !== 1;
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.log(`\nReport written to ${REPORT_PATH}`);

  await prisma.$disconnect();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
