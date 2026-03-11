import * as fs from 'node:fs';
import * as path from 'node:path';
import { validate as validateUuid } from 'uuid';

export function isValidUuid(value: string): boolean {
  return typeof value === 'string' && validateUuid(value);
}

export function getMigrationsDir(): string {
  const migrationsDir = path.join(process.cwd(), 'migrations');
  if (!fs.existsSync(migrationsDir)) {
    throw new Error(`Migrations directory not found: ${migrationsDir}`);
  }
  return migrationsDir;
}
