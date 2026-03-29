/**
 * Playwright globalSetup — seeds the concept-grade template into the DB
 * at the test path so suite9 can navigate to it.
 */
import path from 'path'
import fs from 'fs'
import dotenv from 'dotenv'
import { PrismaClient } from '@prisma/client'

const TEMPLATE_PATH = path.resolve(
  __dirname,
  '../../frontend/public/templates/concept-grade.json'
)
export const TEST_GRAPH_PATH = '/ws/student/biology/1/1'

export default async function globalSetup() {
  dotenv.config({ path: path.resolve(__dirname, '../../backend/.env') })

  const graphJson = fs.readFileSync(TEMPLATE_PATH, 'utf8')
  const prisma = new PrismaClient()

  try {
    const existing = await prisma.graph.findFirst({ where: { path: TEST_GRAPH_PATH } })
    if (existing) {
      await prisma.graph.update({
        where: { path: TEST_GRAPH_PATH },
        data: { graph: graphJson }
      })
    } else {
      await prisma.graph.create({ data: { path: TEST_GRAPH_PATH, graph: graphJson } })
    }
    console.log(`[globalSetup] Seeded concept-grade template at ${TEST_GRAPH_PATH}`)
  } finally {
    await prisma.$disconnect()
  }
}
