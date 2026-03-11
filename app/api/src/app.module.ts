import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { ConfigModule } from './config/config.module';
import { CommonModule } from './common/common.module';
import { DbModule } from './db/db.module';
import { VideosModule } from './videos/videos.module';
import { InferenceModule } from './inference/inference.module';

@Module({
  imports: [
    ConfigModule,
    CommonModule,
    DbModule,
    VideosModule,
    InferenceModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
