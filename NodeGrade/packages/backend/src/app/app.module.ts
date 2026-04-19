import { Module } from '@nestjs/common';
import { GraphModule } from '../graphgateway/graph.module';
import { VisualizationModule } from '../visualization/visualization.module';
import { StudyModule } from '../study/study.module';
import { PrismaService } from '../prisma.service';
import { GraphController } from '../graph/graph.controller';
import { GraphService } from '../graph/graph.service';
import { BenchmarkController } from '../benchmark/benchmark.controller';
import { BenchmarkService } from '../benchmark/benchmark.service';
import { LtiController } from '../lti/lti.controller';
import { LtiService } from '../lti/lti.service';
import { XapiService } from '../xapi.service';
import { HealthController } from '../health/health.controller';
import { HealthService } from '../health/health.service';
import { ReportsController } from '../reports/reports.controller';

@Module({
  imports: [GraphModule, VisualizationModule, StudyModule],
  controllers: [
    GraphController,
    BenchmarkController,
    LtiController,
    HealthController,
    ReportsController,
  ],
  providers: [
    GraphService,
    PrismaService,
    BenchmarkService,
    LtiService,
    XapiService,
    HealthService,
  ],
})
export class AppModule {}
