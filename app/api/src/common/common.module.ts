import { Global, Module } from '@nestjs/common';
import { MigrationRunnerService } from './migration-runner.service';

@Global()
@Module({
  providers: [MigrationRunnerService],
  exports: [MigrationRunnerService],
})
export class CommonModule {}
