module.exports = {
  development: {
    client: 'postgresql',
    connection: {
      host: process.env.DB_HOST || '127.0.0.1',
      database: process.env.DB_NAME || 'energy_trading_db',
      user:     process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
      port:     parseInt(process.env.DB_PORT || '5432')
    },
    pool: {
      min: 2,
      max: 10
    },
    migrations: {
      tableName: 'knex_migrations',
      directory: './migrations'
    }
  }
};
