import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { GetObjectCommand, PutObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { PrismaService } from '../db/prisma.service';
import { ConfigService } from '../config/config.service';
import { v4 as uuidv4 } from 'uuid';

const ALLOWED_MIME = ['video/mp4', 'application/octet-stream'];
const ALLOWED_EXT = '.mp4';

@Injectable()
export class VideosService {
  private readonly s3: S3Client;

  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService,
  ) {
    this.s3 = new S3Client({
      region: this.config.awsRegion,
      credentials: {
        accessKeyId: this.config.awsAccessKeyId,
        secretAccessKey: this.config.awsSecretAccessKey,
      },
    });
  }

  async upload(
    file: Express.Multer.File,
    title?: string,
  ): Promise<{
    id: string;
    title: string | null;
    s3_key: string;
    presigned_url: string;
    uploaded_at: string;
  }> {
    if (file.size > this.config.s3UploadMaxBytes) {
      throw new BadRequestException(
        `File size exceeds maximum allowed (${this.config.s3UploadMaxBytes} bytes)`,
      );
    }
    const mimeOk = ALLOWED_MIME.includes(file.mimetype);
    const extOk = file.originalname?.toLowerCase().endsWith(ALLOWED_EXT);
    if (!mimeOk && !extOk) {
      throw new BadRequestException(
        'Invalid file type. Only MP4 video is accepted.',
      );
    }

    const id = uuidv4();
    const now = new Date();
    const y = now.getUTCFullYear();
    const m = String(now.getUTCMonth() + 1).padStart(2, '0');
    const s3Key = `videos/${y}/${m}/${id}${ALLOWED_EXT}`;

    await this.s3.send(
      new PutObjectCommand({
        Bucket: this.config.s3Bucket,
        Key: s3Key,
        Body: file.buffer,
        ContentType: file.mimetype,
        ContentLength: file.size,
      }),
    );

    await this.prisma.video.create({
      data: {
        id,
        title: title ?? null,
        s3Key,
        status: 'uploaded',
        createdAt: now,
        updatedAt: now,
      },
    });

    const presigned_url = await getSignedUrl(
      this.s3,
      new GetObjectCommand({
        Bucket: this.config.s3Bucket,
        Key: s3Key,
      }),
      { expiresIn: this.config.presignedUrlExpiresSec },
    );

    return {
      id,
      title: title ?? null,
      s3_key: s3Key,
      presigned_url,
      uploaded_at: now.toISOString(),
    };
  }

  async findOne(id: string) {
    const video = await this.prisma.video.findUnique({
      where: { id },
      include: {
        jobs: {
          where: { status: 'completed' },
          orderBy: { updatedAt: 'desc' },
          take: 1,
        },
      },
    });
    if (!video) {
      throw new NotFoundException(`Video not found: ${id}`);
    }
    const latestJob = video.jobs[0];
    return {
      id: video.id,
      title: video.title,
      s3_key: video.s3Key,
      status: video.status,
      metadata: video.metadata,
      created_at: video.createdAt.toISOString(),
      updated_at: video.updatedAt.toISOString(),
      result_json: latestJob?.resultJson ?? undefined,
    };
  }

  async getPresignedUrl(s3Key: string, expiresIn?: number): Promise<string> {
    return getSignedUrl(
      this.s3,
      new GetObjectCommand({
        Bucket: this.config.s3Bucket,
        Key: s3Key,
      }),
      { expiresIn: expiresIn ?? this.config.presignedUrlExpiresSecForInference },
    );
  }

  async findByIdAndGetS3Key(id: string): Promise<{ s3Key: string }> {
    const video = await this.prisma.video.findUnique({
      where: { id },
      select: { s3Key: true },
    });
    if (!video) {
      throw new NotFoundException(`Video not found: ${id}`);
    }
    return { s3Key: video.s3Key };
  }
}
