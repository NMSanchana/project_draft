import { IsOptional, IsString } from 'class-validator';

export class UpdateProfileDto {
  @IsOptional()
  @IsString({ message: 'Name must be a valid string.' })
  name?: string;

  @IsOptional()
  @IsString({ message: 'Avatar must be a valid string or URL.' })
  avatar?: string;
}
