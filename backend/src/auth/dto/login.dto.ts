import { IsEmail, IsNotEmpty, IsString } from 'class-validator';

export class LoginDto {
  @IsEmail({}, { message: 'Please provide a valid email address.' })
  @IsNotEmpty({ message: 'Please provide email and password.' })
  email!: string;

  @IsString()
  @IsNotEmpty({ message: 'Please provide email and password.' })
  password!: string;
}
