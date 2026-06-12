process.env.DB_PATH = ':memory:';
const request = require('supertest');
const app = require('./server');
const { getDb } = require('./db');

beforeAll(() => {
  getDb(); // initialise + seed
});

describe('Auth', () => {
  test('login with valid email returns token', async () => {
    const res = await request(app).post('/api/auth/login').send({ email: 'alice@test.com' });
    expect(res.status).toBe(200);
    expect(res.body.token).toBe('token-alice-123');
    expect(res.body.user.name).toBe('Alice Chen');
  });

  test('login with unknown email returns 404', async () => {
    const res = await request(app).post('/api/auth/login').send({ email: 'nobody@test.com' });
    expect(res.status).toBe(404);
  });

  test('GET /api/auth/me returns current user', async () => {
    const res = await request(app)
      .get('/api/auth/me')
      .set('Authorization', 'Bearer token-alice-123');
    expect(res.status).toBe(200);
    expect(res.body.email).toBe('alice@test.com');
  });
});

describe('Documents', () => {
  let docId;

  test('create a document', async () => {
    const res = await request(app)
      .post('/api/documents')
      .set('Authorization', 'Bearer token-alice-123')
      .send({ title: 'My Test Doc', content: '{"type":"doc","content":[]}' });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe('My Test Doc');
    docId = res.body.id;
  });

  test('fetch the document back', async () => {
    const res = await request(app)
      .get(`/api/documents/${docId}`)
      .set('Authorization', 'Bearer token-alice-123');
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('My Test Doc');
    expect(res.body.relation).toBe('owned');
  });

  test('update document title', async () => {
    const res = await request(app)
      .put(`/api/documents/${docId}`)
      .set('Authorization', 'Bearer token-alice-123')
      .send({ title: 'Renamed Doc' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Renamed Doc');
  });

  test('bob cannot access alices private doc', async () => {
    const res = await request(app)
      .get(`/api/documents/${docId}`)
      .set('Authorization', 'Bearer token-bob-456');
    expect(res.status).toBe(403);
  });
});

describe('Sharing', () => {
  let docId;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/documents')
      .set('Authorization', 'Bearer token-alice-123')
      .send({ title: 'Shared Doc', content: '' });
    docId = res.body.id;
  });

  test('alice shares doc with bob', async () => {
    const res = await request(app)
      .post(`/api/documents/${docId}/share`)
      .set('Authorization', 'Bearer token-alice-123')
      .send({ email: 'bob@test.com' });
    expect(res.status).toBe(200);
    expect(res.body.sharedWith.email).toBe('bob@test.com');
  });

  test('bob can now access shared doc', async () => {
    const res = await request(app)
      .get(`/api/documents/${docId}`)
      .set('Authorization', 'Bearer token-bob-456');
    expect(res.status).toBe(200);
    expect(res.body.relation).toBe('shared');
  });

  test('shared doc appears in bobs list', async () => {
    const res = await request(app)
      .get('/api/documents')
      .set('Authorization', 'Bearer token-bob-456');
    expect(res.status).toBe(200);
    const found = res.body.shared.find(d => d.id === docId);
    expect(found).toBeTruthy();
  });
});

describe('File upload', () => {
  test('uploads a .txt file as a new document', async () => {
    const res = await request(app)
      .post('/api/upload')
      .set('Authorization', 'Bearer token-alice-123')
      .attach('file', Buffer.from('# Hello\nThis is a test'), 'hello.txt');
    expect(res.status).toBe(201);
    expect(res.body.title).toBe('hello');
  });

  test('rejects unsupported file type', async () => {
    const res = await request(app)
      .post('/api/upload')
      .set('Authorization', 'Bearer token-alice-123')
      .attach('file', Buffer.from('data'), 'file.pdf');
    expect(res.status).toBe(400);
  });
});
