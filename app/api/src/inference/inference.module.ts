import { Module } from '@nestjs/common';
import { InferenceController } from './inference.controller';
import { InferenceService } from './inference.service';
import { JobsService } from '../jobs/jobs.service';
import { VideosModule } from '../videos/videos.module';

@Module({
  imports: [VideosModule],
  controllers: [InferenceController],
  providers: [JobsService, InferenceService],
  exports: [InferenceService],
})
export class InferenceModule {}
