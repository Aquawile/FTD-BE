import { createServer } from '@devvit/server';
import { reddit } from '@devvit/reddit';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const SUBREDDITS = [
  'investing',
  'stocks',
  'SecurityAnalysis',
  'StockMarket',
  'wallstreetbets',
  'options',
  'pennystocks',
  'financialindependence',
];
const MAX_POSTS_PER_SUBREDDIT = 100;
const INGESTION_ENDPOINT = process.env.INGESTION_ENDPOINT || '';
const API_KEY = process.env.INGESTION_API_KEY || '';

// ---------------------------------------------------------------------------
// Load Fortune 500 tickers from local JSON (downloaded from GCS SEC/config)
// ---------------------------------------------------------------------------

interface RosterPayload {
  source: string;
  tickers: string[];
}

function loadTickers(): string[] {
  try {
    const raw = require('fs').readFileSync('src/tickers.json', 'utf-8');
    const payload = JSON.parse(raw) as RosterPayload;
    const tickers = payload.tickers || [];
    return [...new Set(tickers.map((t) => normalizeTicker(t)))];
  } catch {
    console.error('Failed to load src/tickers.json — falling back to empty list');
    return [];
  }
}

const TICKERS = loadTickers();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase().replace(/^\$/, '').replace('.', '-');
}

function isValidSubredditName(name: string): boolean {
  return /^[a-zA-Z0-9_]{3,21}$/.test(name);
}

function validateSubreddit(name: string): void {
  if (!isValidSubredditName(name)) {
    throw new Error(`Refusing to search: invalid subreddit name "${name}"`);
  }
}

function toUtcIso(date: Date): string {
  return date.toISOString();
}

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length > 0)
  );
}

// ---------------------------------------------------------------------------
// Types for collected data
// ---------------------------------------------------------------------------

interface CollectedPost {
  id: string;
  tickers: string[];
  subreddit: string;
  title: string;
  body: string;
  author: string | null;
  score: number;
  numComments: number;
  timestamp: string;
  permalink: string;
  comments: Array<{
    id: string;
    author: string | null;
    body: string;
    score: number;
    timestamp: string;
  }>;
}

// ---------------------------------------------------------------------------
// Fetch + match logic
// ---------------------------------------------------------------------------

async function fetchCommentsForPost(postId: string): Promise<CollectedPost['comments']> {
  try {
    const results = await reddit.getComments({
      postId: postId as any,
      limit: 500,
      sort: 'new',
    });

    const comments: CollectedPost['comments'] = [];
    const allComments = await results.all();
    for (const c of allComments) {
      const comment = c as {
        id: string;
        authorName?: string;
        body?: string;
        score?: number;
        createdAt?: Date;
      };
      comments.push({
        id: comment.id,
        author: comment.authorName ?? null,
        body: comment.body ?? '',
        score: comment.score ?? 0,
        timestamp: comment.createdAt ? toUtcIso(comment.createdAt) : new Date().toISOString(),
      });
    }
    return comments;
  } catch {
    return [];
  }
}

async function fetchAndMatchSubreddit(subreddit: string): Promise<CollectedPost[]> {
  validateSubreddit(subreddit);

  const results = await reddit.getNewPosts({
    subredditName: subreddit,
    limit: MAX_POSTS_PER_SUBREDDIT,
    pageSize: MAX_POSTS_PER_SUBREDDIT,
  });

  const allPosts = await results.all();
  const tickerSet = new Set(TICKERS);
  const matchedPosts: CollectedPost[] = [];

  for (const p of allPosts) {
    const post = p as {
      id: string;
      title: string;
      body?: string;
      createdAt: Date;
      authorName?: string;
      score?: number;
      numberOfComments?: number;
      permalink?: string;
    };

    const text = `${post.title ?? ''} ${post.body ?? ''}`;
    const tokens = tokenize(text);

    const matchedTickers = TICKERS.filter((ticker) => {
      const symbol = ticker.replace(/[^a-z0-9]/g, '');
      const token = ticker.toLowerCase();
      return tokens.has(token) || tokens.has(symbol);
    });

    if (matchedTickers.length === 0) continue;

    const comments = await fetchCommentsForPost(post.id);

    matchedPosts.push({
      id: `t3_${post.id}`,
      tickers: matchedTickers,
      subreddit,
      title: post.title ?? '',
      body: post.body ?? '',
      author: post.authorName ?? null,
      score: post.score ?? 0,
      numComments: post.numberOfComments ?? 0,
      timestamp: toUtcIso(post.createdAt),
      permalink: post.permalink ?? '',
      comments,
    });
  }

  return matchedPosts;
}

// ---------------------------------------------------------------------------
// GCP ingestion
// ---------------------------------------------------------------------------

async function ingestToGcp(payload: { posts: CollectedPost[] }): Promise<void> {
  if (!INGESTION_ENDPOINT) {
    console.log('No INGESTION_ENDPOINT configured — skipping upload');
    return;
  }

  const response = await fetch(INGESTION_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`GCP ingestion failed [${response.status}]: ${text}`);
  }

  const result = await response.json();
  console.log(`Ingested ${(result as { uploaded?: number }).uploaded ?? 0} posts`);
}

// ---------------------------------------------------------------------------
// Scheduler cycle
// ---------------------------------------------------------------------------

async function runIngestionCycle(): Promise<void> {
  if (TICKERS.length === 0) {
    console.error('No tickers loaded from src/tickers.json — aborting cycle');
    return;
  }

  console.log(`Reddit ingestion cycle started — ${TICKERS.length} tickers, ${SUBREDDITS.length} subreddits`);

  let totalPosts = 0;

  for (const subreddit of SUBREDDITS) {
    try {
      console.log(`Scanning r/${subreddit}...`);
      const posts = await fetchAndMatchSubreddit(subreddit);
      if (posts.length === 0) continue;

      const payload = { posts };
      await ingestToGcp(payload);
      totalPosts += posts.length;
      console.log(`  → ${posts.length} matched posts from r/${subreddit}`);
    } catch (err) {
      console.error(`Error on r/${subreddit}: ${err}`);
    }
  }

  console.log(`Reddit ingestion cycle complete — ${totalPosts} total posts collected`);
}

// ---------------------------------------------------------------------------
// HTTP Server (Devvit scheduler endpoint)
// ---------------------------------------------------------------------------

async function handleRequest(
  req: { method?: string; url?: string },
  res: { writeHead: (code: number, headers?: Record<string, string>) => void; end: (body: string) => void }
): Promise<void> {
  const url = req.url || '/';
  const method = req.method || 'GET';

  if (method === 'POST' && url === '/internal/scheduler/reddit-ingestion') {
    console.log('Scheduler triggered at', new Date().toISOString());
    try {
      await runIngestionCycle();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok' }));
    } catch (err) {
      console.error('Scheduler error:', err);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'error', message: String(err) }));
    }
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
}

const server = createServer(handleRequest);

export default server;
