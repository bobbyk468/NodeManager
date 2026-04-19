import { Controller, Get, Param, Query } from '@nestjs/common';
import { VisualizationService } from './visualization.service';
import {
  DatasetSummaryResponse,
  VisualizationSpec,
  ConceptAnswersResponse,
  KGSubgraphResponse,
  SampleXAIData,
  SampleTraceResponse,
} from './visualization.types';

@Controller('api/visualization')
export class VisualizationController {
  constructor(private readonly vizService: VisualizationService) {}

  @Get()
  async getAllDatasets(): Promise<{ datasets: DatasetSummaryResponse[] }> {
    const datasets = await this.vizService.getAllDatasets();
    return { datasets };
  }

  @Get('datasets')
  async listDatasets(): Promise<{ datasets: string[] }> {
    const datasets = await this.vizService.listDatasets();
    return { datasets };
  }

  @Get('datasets/:dataset')
  async getDataset(
    @Param('dataset') dataset: string,
  ): Promise<DatasetSummaryResponse> {
    return this.vizService.getDatasetVisualization(dataset);
  }

  @Get('datasets/:dataset/specs')
  async getSpecs(
    @Param('dataset') dataset: string,
  ): Promise<{ specs: VisualizationSpec[] }> {
    const response = await this.vizService.getDatasetVisualization(dataset);
    return { specs: response.visualizations };
  }

  /** Linking & brushing: student answers for a specific concept */
  @Get('datasets/:dataset/concept/:conceptId')
  async getConceptAnswers(
    @Param('dataset') dataset: string,
    @Param('conceptId') conceptId: string,
  ): Promise<ConceptAnswersResponse> {
    return this.vizService.getConceptStudentAnswers(dataset, conceptId);
  }

  /** KG subgraph: ego-graph around a concept for visualization.
   *  Pass ?questionId=<id> to scope is_expected flags to the question being examined.
   *  Without questionId, is_expected is computed globally across all questions (legacy behaviour). */
  @Get('datasets/:dataset/kg/concept/:conceptId')
  async getKGSubgraph(
    @Param('dataset') dataset: string,
    @Param('conceptId') conceptId: string,
    @Query('questionId') questionId?: string,
  ): Promise<KGSubgraphResponse> {
    return this.vizService.getConceptKGSubgraph(dataset, conceptId, questionId);
  }

  /** Per-sample XAI: matched + expected + missing concepts for score provenance */
  @Get('datasets/:dataset/sample/:sampleId')
  async getSampleXAI(
    @Param('dataset') dataset: string,
    @Param('sampleId') sampleId: string,
  ): Promise<SampleXAIData> {
    return this.vizService.getSampleXAI(dataset, sampleId);
  }

  /**
   * LRM Trace: Stage 3b parsed reasoning steps for a specific answer.
   *
   * Returns the structured TraceParser output (parsed_steps + trace_summary)
   * for rendering in the VerifierReasoningPanel dashboard component.
   *
   * If trace data has not been pre-computed for this answer (i.e., the LRM
   * ablation has not been run yet), returns 204 No Content so the panel
   * can show a graceful "Run the LRM verifier to generate trace data" message.
   *
   * GET /api/visualization/datasets/:dataset/sample/:sampleId/trace
   */
  @Get('datasets/:dataset/sample/:sampleId/trace')
  async getSampleTrace(
    @Param('dataset') dataset: string,
    @Param('sampleId') sampleId: string,
  ): Promise<SampleTraceResponse | null> {
    return this.vizService.getSampleTrace(dataset, sampleId);
  }
}
