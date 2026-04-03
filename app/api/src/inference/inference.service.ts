import {
  BadRequestException,
  Injectable,
  ServiceUnavailableException,
} from '@nestjs/common';
import axios, { AxiosError } from 'axios';
import { plainToInstance } from 'class-transformer';
import { validate } from 'class-validator';
import { ConfigService } from '../config/config.service';
import { JobsService } from '../jobs/jobs.service';
import { VideosService } from '../videos/videos.service';
import { InferenceResultDto } from './dto/inference-result.dto';
import type { SegmentRequestDto } from './dto/segment-request.dto';

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

@Injectable()
export class InferenceService {
  constructor(
    private readonly config: ConfigService,
    private readonly videosService: VideosService,
    private readonly jobsService: JobsService,
  ) {}

  async runSegment(dto: SegmentRequestDto): Promise<{
    job_id: string;
    result?: object;
    status?: string;
  }> {
    const { videoId, prompt, mode, config } = dto;

    const { s3Key } = await this.videosService.findByIdAndGetS3Key(videoId);
    const presignedUrl = await this.videosService.getPresignedUrl(s3Key);

    const job = await this.jobsService.create(videoId, prompt);
    const jobId = job.job_id;

    if (mode === 'sync') {
      const result = await this.callPythonSync(
        presignedUrl,
        prompt,
        config?.max_frame_count,
      );
      const validated = await this.validateInferenceResult(result);
      await this.jobsService.updateResult(jobId, 'completed', validated);
      return { job_id: jobId, result: validated };
    }

    // Async mode returns immediately; the inference work continues in the background.
    this.runPythonAsync(jobId, presignedUrl, prompt, config?.max_frame_count);
    return { job_id: jobId, status: 'queued' };
  }

  private async callPythonSync(
    videoUrl: string,
    prompt: string,
    maxFrames?: number,
  ): Promise<object> {
    const url = `${this.config.inferenceUrl.replace(/\/$/, '')}/process-video`;
    const payload = {
      video_url: videoUrl,
      text_prompt: prompt,
      ...(maxFrames != null && maxFrames > 0 ? { max_frames: maxFrames } : {}),
    };

    let lastError: Error | null = null;
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const res = await axios.post(url, payload, {
          timeout: this.config.inferenceTimeoutMs,
          headers: { 'Content-Type': 'application/json' },
          validateStatus: (status) => status >= 200 && status < 300,
        });
        return res.data as object;
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));
        const ax = err as AxiosError;
        const isRetryable =
          (axios.isAxiosError(err) &&
            (err.response?.status == null || err.response.status >= 500)) ||
          ax.code === 'ECONNRESET' ||
          ax.code === 'ETIMEDOUT';
        if (attempt < MAX_RETRIES && isRetryable) {
          await this.delay(RETRY_DELAY_MS * Math.pow(2, attempt - 1));
          continue;
        }
        break;
      }
    }
    throw new ServiceUnavailableException(
      `Inference service failed: ${lastError?.message ?? 'unknown'}`,
    );
  }

  private runPythonAsync(
    jobId: string,
    videoUrl: string,
    prompt: string,
    maxFrames?: number,
  ): void {
    setImmediate(async () => {
      try {
        const result = await this.callPythonSync(videoUrl, prompt, maxFrames);
        const validated = await this.validateInferenceResult(result);
        await this.jobsService.updateResult(jobId, 'completed', validated);
      } catch {
        await this.jobsService.updateResult(jobId, 'failed');
      }
    });
  }

  private async validateInferenceResult(data: object): Promise<object> {
    const instance = plainToInstance(InferenceResultDto, data);
    const errors = await validate(instance, {
      whitelist: true,
      forbidNonWhitelisted: false,
    });
    if (errors.length > 0) {
      throw new BadRequestException(
        `Invalid inference response: ${errors.map((e) => e.toString()).join('; ')}`,
      );
    }
    return data;
  }

  async handleCallback(jobId: string, body: object): Promise<void> {
    const validated = await this.validateInferenceResult(body);
    await this.jobsService.updateResult(jobId, 'completed', validated);
  }

  async getJob(jobId: string) {
    return this.jobsService.findById(jobId);
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
