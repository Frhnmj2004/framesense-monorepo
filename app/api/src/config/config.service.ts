import { Injectable } from '@nestjs/common';

@Injectable()
export class ConfigService {
  private get env(): NodeJS.ProcessEnv {
    return process.env;
  }

  get port(): number {
    const v = this.env['PORT'];
    return v != null ? parseInt(v, 10) : 3000;
  }

  get databaseUrl(): string {
    return this.env['DATABASE_URL'] ?? 'postgresql://postgres:postgres@localhost:5432/framesense';
  }

  get awsRegion(): string {
    return this.env['AWS_REGION'] ?? 'us-east-1';
  }

  get awsAccessKeyId(): string {
    return this.env['AWS_ACCESS_KEY_ID'] ?? '';
  }

  get awsSecretAccessKey(): string {
    return this.env['AWS_SECRET_ACCESS_KEY'] ?? '';
  }

  get s3Bucket(): string {
    return this.env['S3_BUCKET'] ?? '';
  }

  get s3UploadMaxBytes(): number {
    const v = this.env['S3_UPLOAD_MAX_BYTES'];
    return v != null ? parseInt(v, 10) : 1073741824;
  }

  get inferenceUrl(): string {
    return this.env['INFERENCE_URL'] ?? 'http://localhost:8000';
  }

  get inferenceTimeoutMs(): number {
    const v = this.env['INFERENCE_TIMEOUT_MS'];
    return v != null ? parseInt(v, 10) : 900000;
  }

  get jwtSecret(): string {
    return this.env['JWT_SECRET'] ?? 'changeme';
  }

  get migrationTableName(): string {
    return this.env['MIGRATION_TABLE_NAME'] ?? 'schema_migrations';
  }

  get presignedUrlExpiresSec(): number {
    const v = this.env['PRESIGNED_URL_EXPIRES_SEC'];
    return v != null ? parseInt(v, 10) : 3600;
  }

  get presignedUrlExpiresSecForInference(): number {
    const v = this.env['PRESIGNED_URL_EXPIRES_INFERENCE_SEC'];
    return v != null ? parseInt(v, 10) : 7200;
  }

  get backendUrl(): string {
    return this.env['BACKEND_URL'] ?? 'http://localhost:3000';
  }
}
