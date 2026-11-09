import { IsOptional, IsString } from 'class-validator';

export class GoogleAuthDto {
  /**
   * Google ID token issued by Google Identity Services or OAuth2 SDK.
   */
  @IsString({ message: 'idToken must be a string' })
  @IsOptional()
  idToken?: string;

  /**
   * Google Identity Services standard credential parameter.
   */
  @IsString({ message: 'credential must be a string' })
  @IsOptional()
  credential?: string;
}
