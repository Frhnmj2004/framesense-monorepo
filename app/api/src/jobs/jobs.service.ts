import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../db/prisma.service';
import { v4 as uuidv4 } from 'uuid';

export type JobStatus = 'queued' | 'completed' | 'failed';

@Injectable()
export class JobsService {
  constructor(private readonly prisma: PrismaService) {}

  async create(videoId: string, prompt: string): Promise<{
    job_id: string;
    video_id: string;
    prompt: string;
    status: JobStatus;
    created_at: Date;
  }> {
    const jobId = uuidv4();
    const job = await this.prisma.job.create({
      data: {
        jobId,
        videoId,
        prompt,
        status: 'queued',
      },
    });
    return {
      job_id: job.jobId,
      video_id: job.videoId,
      prompt: job.prompt,
      status: job.status as JobStatus,
      created_at: job.createdAt,
    };
  }

  async updateResult(
    jobId: string,
    status: 'completed' | 'failed',
    resultJson?: object,
  ): Promise<void> {
    await this.prisma.job.update({
      where: { jobId },
      data: {
        status,
        resultJson: resultJson ?? undefined,
      },
    });
  }

  async findById(jobId: string) {
    const job = await this.prisma.job.findUnique({
      where: { jobId },
      include: { video: true },
    });
    if (!job) {
      throw new NotFoundException(`Job not found: ${jobId}`);
    }
    return {
      job_id: job.jobId,
      video_id: job.videoId,
      prompt: job.prompt,
      status: job.status,
      result_json: job.resultJson,
      created_at: job.createdAt.toISOString(),
      updated_at: job.updatedAt.toISOString(),
    };
  }
}
