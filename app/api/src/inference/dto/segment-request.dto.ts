import { IsEnum, IsNumber, IsObject, IsOptional, IsString, IsUUID, MinLength } from 'class-validator';

export class SegmentConfigDto {
  @IsOptional()
  @IsNumber()
  max_frame_count?: number;

  @IsOptional()
  @IsNumber()
  sample_fps?: number;
}

export class SegmentRequestDto {
  @IsUUID()
  videoId: string;

  @IsString()
  @MinLength(1)
  prompt: string;

  @IsEnum(['sync', 'async'])
  mode: 'sync' | 'async';

  @IsOptional()
  @IsObject()
  config?: SegmentConfigDto;
}
