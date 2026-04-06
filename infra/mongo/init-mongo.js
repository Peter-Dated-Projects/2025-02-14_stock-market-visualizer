// ============================================================
// SMV MongoDB — Bootstrap Collections & Indexes
// Runs automatically on first MongoDB container start
// ============================================================

// Switch to the application database
db = db.getSiblingDB('smv');

// --- Users collection ---
db.createCollection('users');
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ username: 1 }, { unique: true });

// --- Portfolios collection (one per user) ---
db.createCollection('portfolios');
db.portfolios.createIndex({ user_id: 1 }, { unique: true });
db.portfolios.createIndex({ 'holdings.ticker': 1 });
db.portfolios.createIndex({ 'stocks_of_interest.ticker': 1 });

// --- Agent Heuristics collection (append-only log) ---
db.createCollection('agent_heuristics');
db.agent_heuristics.createIndex({ workflow: 1, created_at: -1 });
db.agent_heuristics.createIndex({ ticker: 1, created_at: -1 });
db.agent_heuristics.createIndex({ industry: 1, created_at: -1 });

// TTL index: auto-expire documents older than 180 days (6 months)
db.agent_heuristics.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 15552000 }  // 180 * 24 * 60 * 60
);

// --- Seed a default user and portfolio for staging ---
if (db.users.countDocuments({}) === 0) {
  const userId = 'default_user';

  db.users.insertOne({
    _id: userId,
    username: 'trader',
    email: 'trader@smv.local',
    password_hash: '',  // No auth in staging
    preferences: {
      theme: 'dark',
      sidebar_collapsed: false,
      default_view: 'dashboard'
    },
    created_at: new Date(),
    updated_at: new Date()
  });

  db.portfolios.insertOne({
    user_id: userId,
    cash_balance: 100000.00,
    holdings: [],
    looking_at_industries: [
      { name: 'AI & Semiconductors', sentiment: 0.0, updated_at: new Date() },
      { name: 'Cloud Computing', sentiment: 0.0, updated_at: new Date() },
      { name: 'Cybersecurity', sentiment: 0.0, updated_at: new Date() }
    ],
    avoiding_industries: [],
    stocks_of_interest: [],
    updated_at: new Date()
  });

  print('✓ Seeded default user and portfolio');
}

print('✓ MongoDB initialization complete');
