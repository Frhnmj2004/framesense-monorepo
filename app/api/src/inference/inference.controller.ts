import {
  BadRequestException,
  Body,
  Controller,
  Get,
  Param,
  ParseUUIDPipe,
  Post,
  Query,
} from '@nestjs/common';
import { InferenceService } from './inference.service';
import { SegmentRequestDto } from './dto/segment-request.dto';

@Controller()
export class InferenceController {
  constructor(private readonly inferenceService: InferenceService) {}

  @Post('segment')
  async segment(@Body() dto: SegmentRequestDto) {
    const out = await this.inferenceService.runSegment(dto);
    if (out.result != null) {
      return { success: true, data: { job_id: out.job_id, result: out.result } };
    }
    return { success: true, data: { job_id: out.job_id, status: out.status } };
  }

  @Get('jobs/:id')
  async getJob(@Param('id', ParseUUIDPipe) id: string) {
    const data = await this.inferenceService.getJob(id);
    return { success: true, data };
  }

  @Post('inference/callback')
  async callback(
    @Query('job_id') jobIdQuery: string | undefined,
    @Body() body: object,
  ) {
    const jobId =
      jobIdQuery ?? (body as { job_id?: string }).job_id;
    if (!jobId || typeof jobId !== 'string') {
      throw new BadRequestException('job_id is required in query or body');
    }
    await this.inferenceService.handleCallback(jobId, body);
    return { success: true };
  }
}
