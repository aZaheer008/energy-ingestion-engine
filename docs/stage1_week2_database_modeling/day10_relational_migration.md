# Day 10 - Relational Migrations

## Lesson

Today we take the database designs from the earlier lessons and make them repeatable. A migration records a schema change as version-controlled code, so development, staging, and production can apply the same change in a predictable order instead of relying on manual database edits.

Each migration has an `up` step to apply a change and a `down` step to reverse it. A rollback is useful when a release needs to be backed out, but it should be designed and tested carefully, especially when a change could affect existing data.

Knex.js provides a schema builder for common table structures. PostgreSQL features such as declarative range partitioning need SQL that the builder does not express directly, so the migration combines Knex table-building methods with raw SQL where PostgreSQL-specific features are required.

## What we added to the code

The `db-infrastructure` package now contains a Knex configuration and an initial energy-ledger migration.

- **Knex configuration:** `knexfile.js` defines the development PostgreSQL connection, taking host, database, user, password, and port from environment variables with local-development defaults. It also sets a connection pool and places migration history in the `knex_migrations` table. The migration directory is configured as `./migrations`.
- **Migration commands:** The package scripts provide commands to create a migration, apply outstanding migrations, and roll back the latest migration batch.
- **Initial migration:** The migration creates PostgreSQL enums for trade direction, product type, and market operator. It builds a `trade_ledger` table for shared trade fields and JSONB asset attributes, adds product-specific JSONB integrity checks and lookup indexes, then creates a time-partitioned `nodal_market_ticks` table with a default partition, one example daily partition, and a node-and-time index.
- **Rollback:** The `down` step removes the tick and ledger tables, then drops the enum types in dependency-safe order.

The migration uses Knex's schema builder for the ledger's ordinary columns and indexes, and raw PostgreSQL statements for the enums, check constraint, GIN index, and range-partitioned table. No seed script or seed data was added in this change.

## How I remember the pattern

Think of a migration as a dated revision in a construction blueprint set. Instead of telling each team how to modify a building from memory, everyone applies the same ordered revisions. The migration history becomes the shared record of how each environment reached its current schema.

## Interview takeaway

I would explain that database changes are treated as code: migrations are reviewed and tracked in version control, then applied through a controlled deployment process. Each change has an explicit forward operation and a considered rollback. Knex handles the standard relational structure, while carefully scoped raw SQL provides access to PostgreSQL-specific features such as enums and partitioning. This makes environments more consistent and reduces the risk of undocumented manual changes.

Before running a migration in a live environment, I would verify it against the target PostgreSQL version, assess locking and data impact, and make sure deployment ordering and recovery procedures are clear. The example configuration is for development; production credentials and environment-specific deployment settings should be managed outside the repository.

## Notes and limitations

The sample migration creates a single daily partition for October 13, 2026, plus a default partition. This is useful for a local demonstration, but it is not an automated partition lifecycle. A production deployment would need an operational process to create future partitions, monitor the default partition, and handle data in it before adding overlapping ranges.

The code also does not include seed data. Seeds are useful for repeatable development or test fixtures, but they are separate from schema migrations and should be designed according to the data and environment they are meant to populate.
