import {
  Injectable,
  BadRequestException,
  UnauthorizedException,
  ConflictException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { OAuth2Client } from 'google-auth-library';
import * as bcrypt from 'bcryptjs';
import { UsersService } from '../users/users.service';
import { RegisterDto } from './dto/register.dto';
import { LoginDto } from './dto/login.dto';
import { GoogleAuthDto } from './dto/google-auth.dto';

export interface AuthUserResponse {
  id: string;
  name: string;
  email: string;
  avatar: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  token: string;
  user: AuthUserResponse;
}

@Injectable()
export class AuthService {
  private googleClient: OAuth2Client | null = null;
  private readonly googleClientId?: string;

  constructor(
    private readonly usersService: UsersService,
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {
    this.googleClientId = this.configService.get<string>('auth.googleClientId');
    if (this.googleClientId) {
      this.googleClient = new OAuth2Client(this.googleClientId);
    }
  }

  /**
   * Register a new user with password hashing and duplicate checks.
   */
  async register(registerDto: RegisterDto): Promise<AuthResponse> {
    const { name, email, password } = registerDto;
    const normalizedEmail = email.toLowerCase().trim();

    const existingUser = await this.usersService.findByEmail(normalizedEmail);
    if (existingUser) {
      throw new BadRequestException({
        success: false,
        message: 'User with this email already exists.',
      });
    }

    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    const user = await this.usersService.create({
      name: name.trim(),
      email: normalizedEmail,
      password: hashedPassword,
      authProvider: 'local',
    });

    const token = this.generateToken(user._id.toString(), user.name, user.email);

    return {
      success: true,
      message: 'Account created successfully!',
      token,
      user: {
        id: user._id.toString(),
        name: user.name,
        email: user.email,
        avatar: user.avatar || '',
      },
    };
  }

  /**
   * Authenticate user with password comparison via bcrypt.
   */
  async login(loginDto: LoginDto): Promise<AuthResponse> {
    const { email, password } = loginDto;
    const normalizedEmail = email.toLowerCase().trim();

    // Explicitly select password hash
    const user = await this.usersService.findByEmail(normalizedEmail, true);
    if (!user) {
      throw new UnauthorizedException({
        success: false,
        message: 'Invalid credentials.',
      });
    }

    if (!user.password || user.authProvider !== 'local') {
      throw new UnauthorizedException({
        success: false,
        message: 'Invalid credentials.',
      });
    }

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      throw new UnauthorizedException({
        success: false,
        message: 'Invalid credentials.',
      });
    }

    const token = this.generateToken(user._id.toString(), user.name, user.email);

    return {
      success: true,
      message: 'Login successful!',
      token,
      user: {
        id: user._id.toString(),
        name: user.name,
        email: user.email,
        avatar: user.avatar || '',
      },
    };
  }

  /**
   * Authenticate user using verified Google ID token.
   */
  async googleAuth(googleAuthDto: GoogleAuthDto): Promise<AuthResponse> {
    const rawToken = googleAuthDto.idToken || googleAuthDto.credential;
    if (!rawToken || typeof rawToken !== 'string' || rawToken.trim() === '') {
      throw new BadRequestException({
        success: false,
        message: 'Google ID token (idToken or credential) is required.',
      });
    }

    if (!this.googleClientId || !this.googleClient) {
      throw new BadRequestException({
        success: false,
        message: 'Google Sign-In is not configured on this server.',
      });
    }

    let payload;
    try {
      const ticket = await this.googleClient.verifyIdToken({
        idToken: rawToken.trim(),
        audience: this.googleClientId,
      });
      payload = ticket.getPayload();
    } catch (err: any) {
      throw new UnauthorizedException({
        success: false,
        message: 'Google token verification failed.',
      });
    }

    if (!payload || !payload.email || !payload.email_verified) {
      throw new UnauthorizedException({
        success: false,
        message: 'Google token is invalid or email is not verified.',
      });
    }

    const verifiedEmail = payload.email.toLowerCase().trim();
    const verifiedName = payload.name || payload.given_name || verifiedEmail.split('@')[0];
    const verifiedAvatar = payload.picture || '';

    let user = await this.usersService.findByEmail(verifiedEmail);
    if (user) {
      if (user.authProvider !== 'google') {
        throw new ConflictException({
          success: false,
          message: 'An account with this email already exists using password authentication. Account linking is not supported.',
        });
      }
    } else {
      user = await this.usersService.create({
        name: verifiedName,
        email: verifiedEmail,
        avatar: verifiedAvatar,
        authProvider: 'google',
      });
    }

    const token = this.generateToken(user._id.toString(), user.name, user.email);

    return {
      success: true,
      message: 'Google Sign In successful!',
      token,
      user: {
        id: user._id.toString(),
        name: user.name,
        email: user.email,
        avatar: user.avatar || '',
      },
    };
  }

  /**
   * Internal helper to sign JWT with minimal payload.
   */
  private generateToken(id: string, name: string, email: string): string {
    return this.jwtService.sign({
      id,
      sub: id,
      name,
      email,
    });
  }
}
