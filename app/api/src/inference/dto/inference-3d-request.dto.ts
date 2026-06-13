import { IsNumber, IsOptional, IsString, IsUrl, ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';

export class MaskRleDto {
  @IsString()
  counts: string;

  @IsNumber({}, { each: true })
  size: number[];
}

export class Inference3DRequestDto {
  @IsUrl()
  image_url: string;

  @ValidateNested()
  @Type(() => MaskRleDto)
  mask_rle: MaskRleDto;

  @IsOptional()
  @IsString()
  preset?: 'fast' | 'quality';

  @IsOptional()
  @IsNumber()
  seed?: number;

  @IsOptional()
  @IsString()
  job_id?: string;
}
