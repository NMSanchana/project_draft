export interface AppConfig {
  port: number;
  environment: string;
}

export interface DatabaseConfig {
  uri: string;
}

export interface AuthConfig {
  jwtSecret: string;
  jwtExpiresIn: string;
  googleClientId?: string;
}

export interface Configuration {
  app: AppConfig;
  database: DatabaseConfig;
  auth: AuthConfig;
}

export const appConfig = (): Configuration => {
  const port = parseInt(process.env.PORT || '5000', 10);
  if (isNaN(port) || port <= 0 || port > 65535) {
    throw new Error(`Invalid PORT configuration: "${process.env.PORT}". Must be a valid TCP port (1-65535).`);
  }

  const mongoUri = process.env.MONGO_URI;
  if (!mongoUri || typeof mongoUri !== 'string' || mongoUri.trim() === '') {
    throw new Error('MONGO_URI is required in environment variables but was not found or is empty.');
  }

  const jwtSecret = process.env.JWT_SECRET;
  if (!jwtSecret || typeof jwtSecret !== 'string' || jwtSecret.trim() === '') {
    throw new Error('JWT_SECRET is required in environment variables but was not found or is empty.');
  }

  return {
    app: {
      port,
      environment: process.env.NODE_ENV || 'development',
    },
    database: {
      uri: mongoUri.trim(),
    },
    auth: {
      jwtSecret: jwtSecret.trim(),
      jwtExpiresIn: process.env.JWT_EXPIRES_IN || '1d',
      googleClientId: process.env.GOOGLE_CLIENT_ID ? process.env.GOOGLE_CLIENT_ID.trim() : undefined,
    },
  };
};
