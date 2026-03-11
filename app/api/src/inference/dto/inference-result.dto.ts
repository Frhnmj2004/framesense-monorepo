import {
  IsArray,
  IsNumber,
  IsString,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';

export class MaskRleDto {
  @IsString()
  counts: string;

  @IsArray()
  @IsNumber({}, { each: true })
  size: number[];
}

export class ObjectDetectionDto {
  @IsNumber()
  object_id: number;

  @IsNumber()
  score: number;

  @IsArray()
  @IsNumber({}, { each: true })
  box: number[];

  @ValidateNested()
  @Type(() => MaskRleDto)
  mask_rle: MaskRleDto;
}

export class FrameDetectionDto {
  @IsNumber()
  frame_index: number;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => ObjectDetectionDto)
  objects: ObjectDetectionDto[];
}

export class InferenceResultDto {
  @IsString()
  session_id: string;

  @IsNumber()
  frames_processed: number;

  @IsNumber()
  video_width: number;

  @IsNumber()
  video_height: number;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => FrameDetectionDto)
  detections: FrameDetectionDto[];
}
