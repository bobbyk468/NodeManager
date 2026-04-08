import { Controller, Get, Param } from '@nestjs/common';
import { VisualizationService } from './visualization.service';
import { DatasetSummaryResponse, VisualizationSpec } from './visualization.types';

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
}
