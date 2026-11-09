import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';

export interface JwtPayload {
  id?: string;
  sub?: string;
  name: string;
  email: string;
  iat?: number;
  exp?: number;
}

export interface AuthenticatedUser {
  id: string;
  name: string;
  email: string;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(configService: ConfigService) {
    const jwtSecret = configService.get<string>('auth.jwtSecret');
    if (!jwtSecret) {
      throw new Error('JWT_SECRET is not configured for JwtStrategy');
    }

    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: jwtSecret,
    });
  }

  async validate(payload: JwtPayload): Promise<AuthenticatedUser> {
    const userId = payload.id || payload.sub;
    if (!userId || !payload.email) {
      throw new UnauthorizedException({
        success: false,
        message: 'Invalid token payload.',
      });
    }

    return {
      id: userId,
      name: payload.name,
      email: payload.email,
    };
  }
}
