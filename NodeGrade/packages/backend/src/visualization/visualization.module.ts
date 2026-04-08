import { Module } from '@nestjs/common';
import { VisualizationController } from './visualization.controller';
import { VisualizationService } from './visualization.service';

@Module({
  controllers: [VisualizationController],
  providers: [VisualizationService],
})
export class VisualizationModule {}
