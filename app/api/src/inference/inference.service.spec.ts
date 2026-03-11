import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '../config/config.service';
import { JobsService } from '../jobs/jobs.service';
import { VideosService } from '../videos/videos.service';
import { InferenceService } from './inference.service';

describe('InferenceService', () => {
  let service: InferenceService;

  const mockConfig = {
    inferenceUrl: 'http://localhost:8000',
    inferenceTimeoutMs: 900000,
  };
  const mockVideosService = {
    findByIdAndGetS3Key: jest.fn(),
    getPresignedUrl: jest.fn().mockResolvedValue('https://presigned.example.com/video.mp4'),
  };
  const mockJobsService = {
    create: jest.fn().mockResolvedValue({ job_id: 'job-uuid', status: 'queued' }),
    updateResult: jest.fn().mockResolvedValue(undefined),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        InferenceService,
        { provide: ConfigService, useValue: mockConfig },
        { provide: VideosService, useValue: mockVideosService },
        { provide: JobsService, useValue: mockJobsService },
      ],
    }).compile();
    service = module.get<InferenceService>(InferenceService);
    jest.clearAllMocks();
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('validateInferenceResult', () => {
    it('accepts valid inference result shape', async () => {
      const valid = {
        session_id: '45881e5d-827b-4f78-8cfe-b846ed62697d',
        frames_processed: 5,
        video_width: 640,
        video_height: 360,
        detections: [
          {
            frame_index: 0,
            objects: [
              {
                object_id: 0,
                score: 0.94,
                box: [354, 129, 455, 261],
                mask_rle: { counts: '127617 7 329', size: [360, 640] },
              },
            ],
          },
        ],
      };
      const result = await (service as any).validateInferenceResult(valid);
      expect(result).toEqual(valid);
    });
  });
});
