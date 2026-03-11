import { IsOptional, IsString, MaxLength } from 'class-validator';

export class UploadVideoDto {
  @IsOptional()
  @IsString()
  @MaxLength(500)
  title?: string;
}
