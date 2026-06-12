const { getDb } = require('./db');

function requireAuth(req, res, next) {
  const token = req.headers['authorization']?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ error: 'Missing token' });

  const user = getDb().prepare('SELECT * FROM users WHERE token = ?').get(token);
  if (!user) return res.status(401).json({ error: 'Invalid token' });

  req.user = user;
  next();
}

module.exports = { requireAuth };
