import { Injectable } from '@nestjs/common';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { Client } from 'pg';
import { ConfigService } from '../config/config.service';
import { getMigrationsDir } from './utils';

@Injectable()
export class MigrationRunnerService {
  constructor(private readonly config: ConfigService) {}

  async run(): Promise<void> {
    const client = new Client({ connectionString: this.config.databaseUrl });
    const tableName = this.config.migrationTableName;

    try {
      await client.connect();

      await client.query(`
        CREATE TABLE IF NOT EXISTS ${tableName} (
          version TEXT PRIMARY KEY,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);

      const migrationsDir = getMigrationsDir();
      const files = fs.readdirSync(migrationsDir).filter((f) => f.endsWith('.sql'));
      files.sort();

      const applied = await client.query(
        `SELECT version FROM ${tableName} ORDER BY version`,
      );
      const appliedSet = new Set(applied.rows.map((r: { version: string }) => r.version));

      for (const file of files) {
        if (appliedSet.has(file)) continue;

        const filePath = path.join(migrationsDir, file);
        const sql = fs.readFileSync(filePath, 'utf-8');

        await client.query('BEGIN');
        try {
          await client.query(sql);
          await client.query(
            `INSERT INTO ${tableName} (version, applied_at) VALUES ($1, NOW())`,
            [file],
          );
          await client.query('COMMIT');
        } catch (err) {
          await client.query('ROLLBACK');
          throw new Error(`Migration ${file} failed: ${err instanceof Error ? err.message : String(err)}`);
        }
      }
    } finally {
      await client.end();
    }
  }
}
