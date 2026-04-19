import { NestFactory } from '@nestjs/core';
import { AppModule } from './app/app.module';
import * as dotenv from 'dotenv';
import { WebSocketCookieAdapter } from './utils/websocket-cookie.adapter';

dotenv.config();
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Use our custom WebSocketCookieAdapter
  app.useWebSocketAdapter(new WebSocketCookieAdapter(app));

  // Enable CORS with configurable origin
  const allowedOrigins = process.env.CORS_ORIGIN
    ? process.env.CORS_ORIGIN.split(',').map((origin) =>
        origin.trim().replace(/^"|"$/g, ''),
      )
    : [
        'https://nodegrade.haski.app',
        // Vite dev server origins used during the user study (localhost)
        'http://localhost:5173',
        'http://127.0.0.1:5173',
      ];

  app.enableCors({
    origin: allowedOrigins,
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
    credentials: true,
    allowedHeaders: [
      'Content-Type',
      'Authorization',
      'Origin',
      'X-Requested-With',
      'Accept',
    ],
  });

  await app.listen(process.env.PORT ?? 5000);
  console.log(
    `NestJS server running on port ${process.env.PORT ?? 5000} with CORS enabled for origins: ${allowedOrigins.join(', ')}`,
  );
}
void bootstrap();
