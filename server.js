/**
 * TGM Reporting Studio - Production Node.js Server & REST API
 * Supports Hostinger Web Apps, Render, Railway, Heroku, VPS, and local environments.
 * Zero external dependencies (uses standard Node.js runtime).
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');
const crypto = require('crypto');

const PORT = parseInt(process.env.PORT || '8000', 10);
const FRONTEND_DIR = path.join(__dirname, 'frontend');
const DATA_DIR = path.join(__dirname, 'backend', 'data');
const STORE_FILE = path.join(DATA_DIR, 'store.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// ----------------- In-Memory & File Store ----------------- //
function loadStore() {
  try {
    if (fs.existsSync(STORE_FILE)) {
      const data = JSON.parse(fs.readFileSync(STORE_FILE, 'utf-8'));
      return data;
    }
  } catch (err) {
    console.error('Error loading store, initializing default:', err.message);
  }

  // Initial Seed State
  return {
    clients: [
      {
        id: "client_the_sunya_01",
        name: "The Sunya",
        website: "https://thesunya.com",
        industry: "Premium Fashion & Apparel",
        currency: "INR",
        is_active: true,
        google_sheet_url: "https://docs.google.com/spreadsheets/d/1yulDW_Xm-pmawzXSqBtRmg1WojiP74FpuyN1T6sp-yQ/edit#gid=886192859",
        google_sheet_gid: "886192859",
        last_sheet_synced_at: null,
        created_at: new Date().toISOString()
      },
      {
        id: "client_apex_01",
        name: "Apex Global Direct",
        website: "https://apexglobal.example.com",
        industry: "eCommerce & Apparel",
        currency: "INR",
        is_active: true,
        google_sheet_url: "",
        google_sheet_gid: "0",
        last_sheet_synced_at: null,
        created_at: new Date().toISOString()
      },
      {
        id: "client_nexus_02",
        name: "Nexus Enterprise Cloud",
        website: "https://nexuscloud.example.com",
        industry: "B2B SaaS",
        currency: "INR",
        is_active: true,
        google_sheet_url: "",
        google_sheet_gid: "0",
        last_sheet_synced_at: null,
        created_at: new Date().toISOString()
      },
      {
        id: "client_zenith_03",
        name: "Zenith Health & Wellness",
        website: "https://zenithwellness.example.com",
        industry: "D2C Consumer Brands",
        currency: "INR",
        is_active: true,
        google_sheet_url: "",
        google_sheet_gid: "0",
        last_sheet_synced_at: null,
        created_at: new Date().toISOString()
      }
    ],
    users: [
      {
        id: "user_admin_01",
        email: "admin@thinkgrowmedia.com",
        password_hash: hashPassword("tgmAdmin2026!"),
        name: "TGM Executive Admin",
        role: "admin",
        assigned_client_ids: ["*"],
        created_at: new Date().toISOString()
      }
    ],
    sessions: {},
    share_links: {
      "client_the_sunya_01": {
        token: "tgm_live_thesunya_88619",
        client_id: "client_the_sunya_01",
        client_name: "The Sunya",
        created_at: new Date().toISOString()
      }
    },
    settings: {
      looker_embed_url: ""
    },
    records: []
  };
}

let STORE = loadStore();

function saveStore() {
  try {
    fs.writeFileSync(STORE_FILE, JSON.stringify(STORE, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error saving store:', err.message);
  }
}

// ----------------- Password & Crypto Helpers ----------------- //
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.pbkdf2Sync(password, salt, 10000, 32, 'sha256').toString('hex');
  return `${salt}$${hash}`;
}

function verifyPassword(storedHash, password) {
  try {
    const [salt, hash] = storedHash.split('$');
    const verify = crypto.pbkdf2Sync(password, salt, 10000, 32, 'sha256').toString('hex');
    return hash === verify;
  } catch (e) {
    return false;
  }
}

// ----------------- Nomenclature & KPI Math ----------------- //
function parseFunnelStage(text = "") {
  const t = text.toLowerCase();
  if (t.includes("asc") || t.includes("advantage+") || t.includes("advantage_plus")) return "Advantage+ Shopping Campaign";
  if (t.includes("tof") || t.includes("tofu") || t.includes("cold") || t.includes("prospecting")) return "Top of Funnel (Cold Prospecting)";
  if (t.includes("mof") || t.includes("mofu") || t.includes("engager") || t.includes("consideration")) return "Middle of Funnel (Engagers/Consideration)";
  if (t.includes("bof") || t.includes("bofu") || t.includes("retarget") || t.includes("cart") || t.includes("visitor")) return "Bottom of Funnel (Cart Abandoners/Web Visitors)";
  return "Top of Funnel (Cold Prospecting)";
}

function parseCategory(text = "") {
  const t = text.toLowerCase();
  if (t.includes("polo")) return "Polo";
  if (t.includes("t-shirt") || t.includes("tshirt") || t.includes("tee")) return "T-Shirts";
  if (t.includes("shirt")) return "Shirts";
  if (t.includes("hoodie") || t.includes("sweatshirt")) return "Hoodies & Sweatshirts";
  return "Catalog-Wide / Storewide";
}

function parseProductName(text = "", category = "") {
  const t = text.toLowerCase();
  if (t.includes("leaf print")) return "Leaf Print Polo - Slate Color";
  if (t.includes("black")) return "Classic Polo - Solid Black";
  if (t.includes("royal blue")) return "Royal Blue Solid Polo";
  if (t.includes("bundle") || t.includes("pack")) return "Multiple Products / Bundle";
  return `${category} Signature Edition`;
}

function parseSaleOffer(text = "") {
  const t = text.toLowerCase();
  if (t.includes("black friday") || t.includes("bfcm")) return "Black Friday / 20% Off";
  if (t.includes("eoss") || t.includes("bogo") || t.includes("buy 2")) return "End of Season / Buy 2 Get 1";
  if (t.includes("spring") || t.includes("500 off") || t.includes("discount")) return "Spring Sale / Flat ₹500 Off";
  return "Evergreen / Regular Pricing / BAU";
}

function parseAudienceType(text = "") {
  const t = text.toLowerCase();
  if (t.includes("broad") || t.includes("open")) return "Broad";
  if (t.includes("lookalike") || t.includes("lal")) return "Lookalike Audience";
  if (t.includes("interest") || t.includes("affinity")) return "Interest-Based Targeting";
  if (t.includes("retarget") || t.includes("dpa")) return "Dynamic Retargeting";
  return "Broad";
}

function parseConceptAngleHook(text = "") {
  const t = text.toLowerCase();
  if (t.includes("review") || t.includes("unboxing") || t.includes("ugc")) return "Customer Video Review / Unboxing";
  if (t.includes("price") || t.includes("discount") || t.includes("deal")) return "Price Anchor / Offer-led Hook";
  if (t.includes("vs") || t.includes("comparison")) return "Comparison Chart / Competitor Angle";
  if (t.includes("shrink") || t.includes("problem") || t.includes("sweat")) return "Problem-Agitation Hook (e.g., No Shrinkage)";
  return "Product Feature / Material Focus";
}

function parseFormat(text = "") {
  const t = text.toLowerCase();
  if (t.includes("reel") || t.includes("video") || t.includes("tiktok") || t.includes("9:16")) return "Reel/Video";
  if (t.includes("carousel")) return "Carousel";
  if (t.includes("gif") || t.includes("motion")) return "Short Animated GIF / Motion Graphic";
  return "Single Image";
}

function parseLandingPage(text = "") {
  const t = text.toLowerCase();
  if (t.includes("collection") || t.includes("shop-all")) return "Collection Landing Page";
  if (t.includes("pdp") || t.includes("detail")) return "Product Detail Page";
  if (t.includes("home")) return "Homepage";
  return "Product Detail Page";
}

function cleanRecord(raw, clientId, clientName) {
  const spend = Math.max(0, parseFloat(raw.spend || 0) || 0);
  const revenue = Math.max(0, parseFloat(raw.purchases_conversion_value || 0) || 0);
  const purchases = Math.max(0, parseFloat(raw.purchases || 0) || 0);
  const lpv = Math.max(0, parseInt(raw.landing_page_views || 0, 10) || 0);
  const reach = Math.max(0, parseInt(raw.reach || 0, 10) || 0);
  const impressions = Math.max(0, parseInt(raw.impressions || 0, 10) || 0);
  const linkClicks = Math.max(0, parseInt(raw.link_clicks || 0, 10) || 0);
  const video3s = Math.max(0, parseInt(raw.video_plays_3s || 0, 10) || 0);
  const thruplays = Math.max(0, parseInt(raw.thruplays_15s || 0, 10) || 0);
  const atc = Math.max(0, parseInt(raw.adds_to_cart || 0, 10) || 0);
  const ic = Math.max(0, parseInt(raw.checkouts_initiated || 0, 10) || 0);

  const campaign = raw.campaign_name || "Campaign";
  const adset = raw.adset_name || "AdSet";
  const ad = raw.ad_name || "Ad";
  const context = `${campaign} ${adset} ${ad}`;

  const category = parseCategory(context);

  return {
    record_id: raw.record_id || `rec_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
    date: raw.date || new Date().toISOString().split('T')[0],
    client_id: clientId,
    client_name: clientName,
    platform: raw.platform || "Meta",
    campaign_name: campaign,
    adset_name: adset,
    ad_name: ad,
    currency: raw.currency || "INR",
    category_collection: category,
    product_name: parseProductName(context, category),
    funnel: parseFunnelStage(campaign),
    sale_offer: parseSaleOffer(context),
    audience_type: parseAudienceType(adset),
    concept_angle_hook: parseConceptAngleHook(ad),
    format: parseFormat(ad),
    landing_page: parseLandingPage(context),
    spend: Math.round(spend * 100) / 100,
    purchases_conversion_value: Math.round(revenue * 100) / 100,
    purchases: purchases,
    landing_page_views: lpv,
    reach: reach,
    impressions: impressions,
    link_clicks: linkClicks,
    video_plays_3s: video3s,
    thruplays_15s: thruplays,
    adds_to_cart: atc,
    checkouts_initiated: ic,
    purchase_roas: spend > 0 ? Math.round((revenue / spend) * 100) / 100 : 0,
    cost_per_purchase: purchases > 0 ? Math.round((spend / purchases) * 100) / 100 : 0,
    avg_purchase_conversion_value: purchases > 0 ? Math.round((revenue / purchases) * 100) / 100 : 0,
    purchase_rate_per_lpv: lpv > 0 ? Math.round((purchases / lpv) * 10000) / 100 : 0,
    cost_per_lpv: lpv > 0 ? Math.round((spend / lpv) * 100) / 100 : 0,
    lpv_rate_per_link_clicks: linkClicks > 0 ? Math.round((lpv / linkClicks) * 10000) / 100 : 0,
    frequency: reach > 0 ? Math.round((impressions / reach) * 100) / 100 : 1,
    cpm: impressions > 0 ? Math.round((spend / impressions) * 100000) / 100 : 0,
    cpc: linkClicks > 0 ? Math.round((spend / linkClicks) * 100) / 100 : 0,
    ctr: impressions > 0 ? Math.round((linkClicks / impressions) * 10000) / 100 : 0,
    video_plays_3s_rate_per_impressions: impressions > 0 ? Math.round((video3s / impressions) * 10000) / 100 : 0,
    cost_per_video_play_3s: video3s > 0 ? Math.round((spend / video3s) * 1000) / 1000 : 0,
    cost_per_thruplay_15s: thruplays > 0 ? Math.round((spend / thruplays) * 1000) / 1000 : 0,
    cost_per_add_to_cart: atc > 0 ? Math.round((spend / atc) * 100) / 100 : 0,
    add_to_cart_pct: lpv > 0 ? Math.round((atc / lpv) * 10000) / 100 : 0,
    cost_per_checkout_initiated: ic > 0 ? Math.round((spend / ic) * 100) / 100 : 0,
    checkout_initiated_pct: lpv > 0 ? Math.round((ic / lpv) * 10000) / 100 : 0
  };
}

// ----------------- Google Sheet Downloader & Parser ----------------- //
function fetchSheetCsv(sheetUrl, gid = "0") {
  return new Promise((resolve, reject) => {
    let sheetId = sheetUrl;
    const match = sheetUrl.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (match) sheetId = match[1];

    const gidMatch = sheetUrl.match(/[#&?]gid=([0-9]+)/);
    if (gidMatch) gid = gidMatch[1];

    const exportUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=csv&gid=${gid}`;
    https.get(exportUrl, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        https.get(res.headers.location, (redirectRes) => {
          let data = '';
          redirectRes.on('data', chunk => data += chunk);
          redirectRes.on('end', () => resolve(data));
        }).on('error', reject);
        return;
      }
      if (res.statusCode !== 200) {
        return reject(new Error(`Google Sheet returned HTTP status ${res.statusCode}`));
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

function parseCsv(csvText) {
  const lines = csvText.split(/\r?\n/).filter(l => l.trim().length > 0);
  if (lines.length === 0) return [];

  // Simple CSV Splitter respecting quotes
  function parseLine(line) {
    const result = [];
    let insideQuotes = false;
    let current = '';
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        insideQuotes = !insideQuotes;
      } else if (char === ',' && !insideQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    result.push(current.trim());
    return result;
  }

  // Find header row in first 5 lines
  let headerIdx = 0;
  for (let i = 0; i < Math.min(5, lines.length); i++) {
    const lower = lines[i].toLowerCase();
    if (lower.includes('spend') || lower.includes('cost') || lower.includes('impressions') || lower.includes('clicks')) {
      headerIdx = i;
      break;
    }
  }

  const headers = parseLine(lines[headerIdx]).map(h => h.toLowerCase().replace(/[^a-z0-9]/g, '_'));
  const rows = [];

  for (let i = headerIdx + 1; i < lines.length; i++) {
    const values = parseLine(lines[i]);
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = values[idx] || "";
    });

    // Map common aliases
    const spendKey = Object.keys(row).find(k => k.includes('spend') || k.includes('cost') || k.includes('amount'));
    const revKey = Object.keys(row).find(k => k.includes('conversion_value') || k.includes('revenue') || k.includes('sales'));
    const dateKey = Object.keys(row).find(k => k.includes('date') || k.includes('day'));
    const campKey = Object.keys(row).find(k => k.includes('campaign'));

    row.spend = row[spendKey] || "0";
    row.purchases_conversion_value = row[revKey] || "0";
    row.date = row[dateKey] || new Date().toISOString().split('T')[0];
    row.campaign_name = row[campKey] || "Campaign";

    rows.push(row);
  }

  return rows;
}

// ----------------- Request Handlers ----------------- //
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        resolve({});
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-session-token',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
  });
  res.end(JSON.stringify(data));
}

function getAuthUser(req) {
  const authHeader = req.headers['authorization'] || '';
  let token = '';
  if (authHeader.startsWith('Bearer ')) {
    token = authHeader.split(' ')[1];
  } else if (req.headers['x-session-token']) {
    token = req.headers['x-session-token'];
  }
  if (!token) return null;
  return STORE.sessions[token] || null;
}

// ----------------- Static File Server ----------------- //
const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

function serveStatic(req, res, pathname) {
  let filePath = '';
  if (pathname === '/' || pathname === '/index.html') {
    filePath = path.join(FRONTEND_DIR, 'index.html');
  } else if (pathname === '/portal' || pathname.startsWith('/portal/')) {
    filePath = path.join(FRONTEND_DIR, 'portal.html');
  } else {
    filePath = path.join(FRONTEND_DIR, pathname);
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': contentType });
    fs.createReadStream(filePath).pipe(res);
  });
}

// ----------------- Main HTTP Server ----------------- //
const server = http.createServer(async (req, res) => {
  // CORS Preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-session-token',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
    });
    res.end();
    return;
  }

  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const query = parsedUrl.query;

  // ----------------- API ROUTES ----------------- //

  // Health
  if (pathname === '/api/health') {
    return sendJson(res, 200, {
      status: "healthy",
      service: "TGM Reporting Studio (Node.js Live Engine)",
      timestamp: new Date().toISOString()
    });
  }

  // Auth: Login
  if (pathname === '/api/auth/login' && req.method === 'POST') {
    const body = await parseBody(req);
    const user = STORE.users.find(u => u.email.toLowerCase() === (body.email || '').trim().toLowerCase());
    if (!user || !verifyPassword(user.password_hash, body.password || '')) {
      return sendJson(res, 401, { detail: "Invalid email or password." });
    }
    const token = `tgm_sess_${crypto.randomBytes(24).toString('hex')}`;
    const userProfile = {
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      assigned_client_ids: user.assigned_client_ids
    };
    STORE.sessions[token] = userProfile;
    saveStore();
    return sendJson(res, 200, { success: true, token, user: userProfile });
  }

  // Auth: Me
  if (pathname === '/api/auth/me' && req.method === 'GET') {
    const user = getAuthUser(req);
    if (!user) return sendJson(res, 401, { detail: "Authentication required." });
    return sendJson(res, 200, user);
  }

  // Auth: Logout
  if (pathname === '/api/auth/logout' && req.method === 'POST') {
    const token = (req.headers['authorization'] || '').replace('Bearer ', '') || req.headers['x-session-token'];
    if (token && STORE.sessions[token]) {
      delete STORE.sessions[token];
      saveStore();
    }
    return sendJson(res, 200, { success: true, message: "Logged out successfully." });
  }

  // Clients: List & Add
  if (pathname === '/api/clients' && req.method === 'GET') {
    const user = getAuthUser(req);
    let list = STORE.clients;
    if (user && user.role !== 'admin' && !user.assigned_client_ids.includes('*')) {
      list = list.filter(c => user.assigned_client_ids.includes(c.id));
    }
    return sendJson(res, 200, list);
  }

  if (pathname === '/api/clients' && req.method === 'POST') {
    const user = getAuthUser(req);
    if (user && user.role !== 'admin') return sendJson(res, 403, { detail: "Admin privileges required." });
    const body = await parseBody(req);
    const newClient = {
      id: body.id || `client_${Date.now()}`,
      name: body.name || "New Client",
      website: body.website || "",
      industry: body.industry || "",
      currency: body.currency || "INR",
      is_active: true,
      google_sheet_url: body.google_sheet_url || "",
      google_sheet_gid: body.google_sheet_gid || "0",
      last_sheet_synced_at: null,
      created_at: new Date().toISOString()
    };
    STORE.clients.push(newClient);
    saveStore();
    return sendJson(res, 200, newClient);
  }

  // Client Update / Delete
  const clientMatch = pathname.match(/^\/api\/clients\/([a-zA-Z0-9_-]+)$/);
  if (clientMatch && req.method === 'PUT') {
    const clientId = clientMatch[1];
    const body = await parseBody(req);
    const client = STORE.clients.find(c => c.id === clientId);
    if (!client) return sendJson(res, 404, { detail: "Client not found." });
    Object.assign(client, body, { updated_at: new Date().toISOString() });
    saveStore();
    return sendJson(res, 200, client);
  }

  if (clientMatch && req.method === 'DELETE') {
    const clientId = clientMatch[1];
    STORE.clients = STORE.clients.filter(c => c.id !== clientId);
    STORE.records = STORE.records.filter(r => r.client_id !== clientId);
    saveStore();
    return sendJson(res, 200, { success: true, message: "Client deleted." });
  }

  // Client Sheet Config
  const sheetConfigMatch = pathname.match(/^\/api\/clients\/([a-zA-Z0-9_-]+)\/sheet-config$/);
  if (sheetConfigMatch && req.method === 'POST') {
    const clientId = sheetConfigMatch[1];
    const body = await parseBody(req);
    const client = STORE.clients.find(c => c.id === clientId);
    if (!client) return sendJson(res, 404, { detail: "Client not found." });
    client.google_sheet_url = body.google_sheet_url || client.google_sheet_url;
    client.google_sheet_gid = body.google_sheet_gid || client.google_sheet_gid;
    saveStore();
    return sendJson(res, 200, { success: true, client });
  }

  // Client Sheet Sync
  const syncSheetMatch = pathname.match(/^\/api\/clients\/([a-zA-Z0-9_-]+)\/sync-sheet$/);
  if (syncSheetMatch && req.method === 'POST') {
    const clientId = syncSheetMatch[1];
    const client = STORE.clients.find(c => c.id === clientId);
    if (!client) return sendJson(res, 404, { detail: "Client not found." });
    if (!client.google_sheet_url) return sendJson(res, 400, { detail: "No Google Sheet URL configured." });

    try {
      const csvData = await fetchSheetCsv(client.google_sheet_url, client.google_sheet_gid);
      const parsedRows = parseCsv(csvData);
      
      // Clean and isolate client records
      const cleaned = parsedRows.map(r => cleanRecord(r, client.id, client.name));
      STORE.records = STORE.records.filter(r => r.client_id !== client.id).concat(cleaned);
      client.last_sheet_synced_at = new Date().toISOString();
      saveStore();

      return sendJson(res, 200, {
        success: true,
        message: `Successfully synced ${cleaned.length} records for ${client.name}`,
        records_synced: cleaned.length
      });
    } catch (err) {
      console.error('Sheet Sync Error:', err);
      return sendJson(res, 400, { detail: `Sheet sync failed: ${err.message}` });
    }
  }

  // Client Clear Data
  const clearDataMatch = pathname.match(/^\/api\/clients\/([a-zA-Z0-9_-]+)\/clear-data$/);
  if (clearDataMatch && req.method === 'POST') {
    const clientId = clearDataMatch[1];
    const beforeCount = STORE.records.length;
    STORE.records = STORE.records.filter(r => r.client_id !== clientId);
    saveStore();
    return sendJson(res, 200, {
      success: true,
      message: `Cleared ${beforeCount - STORE.records.length} records.`,
      deleted_count: beforeCount - STORE.records.length
    });
  }

  // Client Share Link
  const shareLinkMatch = pathname.match(/^\/api\/clients\/([a-zA-Z0-9_-]+)\/share-link$/);
  if (shareLinkMatch && req.method === 'GET') {
    const clientId = shareLinkMatch[1];
    const client = STORE.clients.find(c => c.id === clientId);
    if (!client) return sendJson(res, 404, { detail: "Client not found." });

    if (!STORE.share_links[clientId]) {
      STORE.share_links[clientId] = {
        token: `tgm_live_${crypto.randomBytes(12).toString('hex')}`,
        client_id: client.id,
        client_name: client.name,
        created_at: new Date().toISOString()
      };
      saveStore();
    }
    const token = STORE.share_links[clientId].token;
    return sendJson(res, 200, {
      client_id: client.id,
      client_name: client.name,
      token: token,
      share_url: `/portal?token=${token}`
    });
  }

  const regenLinkMatch = pathname.match(/^\/api\/clients\/([a-zA-Z0-9_-]+)\/share-link\/regenerate$/);
  if (regenLinkMatch && req.method === 'POST') {
    const clientId = regenLinkMatch[1];
    const client = STORE.clients.find(c => c.id === clientId);
    if (!client) return sendJson(res, 404, { detail: "Client not found." });
    STORE.share_links[clientId] = {
      token: `tgm_live_${crypto.randomBytes(12).toString('hex')}`,
      client_id: client.id,
      client_name: client.name,
      created_at: new Date().toISOString()
    };
    saveStore();
    const token = STORE.share_links[clientId].token;
    return sendJson(res, 200, {
      client_id: client.id,
      client_name: client.name,
      token: token,
      share_url: `/portal?token=${token}`
    });
  }

  // Portal Public Info
  const portalInfoMatch = pathname.match(/^\/api\/portal\/([a-zA-Z0-9_-]+)\/info$/);
  if (portalInfoMatch && req.method === 'GET') {
    const token = portalInfoMatch[1];
    const link = Object.values(STORE.share_links).find(l => l.token === token);
    if (!link) return sendJson(res, 404, { detail: "Invalid or expired share link." });
    const client = STORE.clients.find(c => c.id === link.client_id) || { name: link.client_name, id: link.client_id };
    return sendJson(res, 200, { client_id: client.id, name: client.name, currency: client.currency || "INR" });
  }

  // Portal Public Summary
  const portalSummaryMatch = pathname.match(/^\/api\/portal\/([a-zA-Z0-9_-]+)\/summary$/);
  if (portalSummaryMatch && req.method === 'GET') {
    const token = portalSummaryMatch[1];
    const link = Object.values(STORE.share_links).find(l => l.token === token);
    if (!link) return sendJson(res, 404, { detail: "Invalid share link." });

    const summary = computePerformanceSummary(link.client_id, query.start_date, query.end_date);
    return sendJson(res, 200, {
      client: { client_id: link.client_id, name: link.client_name },
      summary: summary
    });
  }

  // Portal Public Nomenclature
  const portalNomMatch = pathname.match(/^\/api\/portal\/([a-zA-Z0-9_-]+)\/nomenclature$/);
  if (portalNomMatch && req.method === 'GET') {
    const token = portalNomMatch[1];
    const link = Object.values(STORE.share_links).find(l => l.token === token);
    if (!link) return sendJson(res, 404, { detail: "Invalid share link." });

    const dimension = query.dimension || "category";
    const table = computeNomenclatureTable(dimension, link.client_id, query.start_date, query.end_date);
    return sendJson(res, 200, {
      client: { client_id: link.client_id, name: link.client_name },
      dimension: dimension,
      records: table
    });
  }

  // Analytics: Summary
  if (pathname === '/api/data/summary' && req.method === 'GET') {
    const clientId = query.client_id || (STORE.clients[0] ? STORE.clients[0].id : "");
    const summary = computePerformanceSummary(clientId, query.start_date, query.end_date);
    return sendJson(res, 200, summary);
  }

  // Analytics: Nomenclature Weekly
  if (pathname === '/api/data/nomenclature/weekly' && req.method === 'GET') {
    const dimension = query.dimension || "category";
    const clientId = query.client_id || (STORE.clients[0] ? STORE.clients[0].id : "");
    const table = computeNomenclatureTable(dimension, clientId, query.start_date, query.end_date);
    return sendJson(res, 200, table);
  }

  // Analytics: Records List
  if (pathname === '/api/data/records' && req.method === 'GET') {
    const clientId = query.client_id;
    let filtered = STORE.records;
    if (clientId) filtered = filtered.filter(r => r.client_id === clientId);
    if (query.start_date) filtered = filtered.filter(r => r.date >= query.start_date);
    if (query.end_date) filtered = filtered.filter(r => r.date <= query.end_date);
    if (query.platform) filtered = filtered.filter(r => r.platform.toLowerCase() === query.platform.toLowerCase());

    const limit = parseInt(query.limit || '50', 10);
    const offset = parseInt(query.offset || '0', 10);
    return sendJson(res, 200, {
      total: filtered.length,
      limit: limit,
      offset: offset,
      records: filtered.slice(offset, offset + limit)
    });
  }

  // Team Users
  if (pathname === '/api/team/users' && req.method === 'GET') {
    return sendJson(res, 200, STORE.users.map(u => ({
      id: u.id, email: u.email, name: u.name, role: u.role, assigned_client_ids: u.assigned_client_ids
    })));
  }

  // BigQuery & Looker
  if (pathname === '/api/bigquery/config') {
    return sendJson(res, 200, { project_id: "", dataset_id: "tgm_reporting", table_name: "cleaned_records_v2", is_configured: false });
  }

  if (pathname === '/api/looker/embed-url' && req.method === 'GET') {
    return sendJson(res, 200, { embed_url: STORE.settings.looker_embed_url || "" });
  }

  if (pathname === '/api/looker/embed-url' && req.method === 'POST') {
    const body = await parseBody(req);
    STORE.settings.looker_embed_url = body.embed_url || "";
    saveStore();
    return sendJson(res, 200, { success: true, embed_url: STORE.settings.looker_embed_url });
  }

  // Fallback to static files
  return serveStatic(req, res, pathname);
});

// ----------------- Analytics Calculation Engines ----------------- //
function computePerformanceSummary(clientId, startDate, endDate) {
  let records = STORE.records;
  if (clientId) records = records.filter(r => r.client_id === clientId);
  if (startDate) records = records.filter(r => r.date >= startDate);
  if (endDate) records = records.filter(r => r.date <= endDate);

  const totals = records.reduce((acc, r) => {
    acc.spend += r.spend || 0;
    acc.revenue += r.purchases_conversion_value || 0;
    acc.purchases += r.purchases || 0;
    acc.impressions += r.impressions || 0;
    acc.link_clicks += r.link_clicks || 0;
    acc.landing_page_views += r.landing_page_views || 0;
    acc.reach += r.reach || 0;
    acc.adds_to_cart += r.adds_to_cart || 0;
    acc.checkouts_initiated += r.checkouts_initiated || 0;
    acc.video_plays_3s += r.video_plays_3s || 0;
    acc.thruplays_15s += r.thruplays_15s || 0;
    return acc;
  }, {
    spend: 0, revenue: 0, purchases: 0, impressions: 0, link_clicks: 0,
    landing_page_views: 0, reach: 0, adds_to_cart: 0, checkouts_initiated: 0,
    video_plays_3s: 0, thruplays_15s: 0
  });

  const overall_roas = totals.spend > 0 ? Math.round((totals.revenue / totals.spend) * 100) / 100 : 0;
  const cpa = totals.purchases > 0 ? Math.round((totals.spend / totals.purchases) * 100) / 100 : 0;
  const ctr = totals.impressions > 0 ? Math.round((totals.link_clicks / totals.impressions) * 10000) / 100 : 0;
  const cpc = totals.link_clicks > 0 ? Math.round((totals.spend / totals.link_clicks) * 100) / 100 : 0;
  const cpm = totals.impressions > 0 ? Math.round((totals.spend / totals.impressions) * 100000) / 100 : 0;

  // Group by Date for Trends
  const trendMap = {};
  records.forEach(r => {
    if (!trendMap[r.date]) {
      trendMap[r.date] = { date: r.date, spend: 0, revenue: 0, purchases: 0, impressions: 0, link_clicks: 0 };
    }
    trendMap[r.date].spend += r.spend || 0;
    trendMap[r.date].revenue += r.purchases_conversion_value || 0;
    trendMap[r.date].purchases += r.purchases || 0;
    trendMap[r.date].impressions += r.impressions || 0;
    trendMap[r.date].link_clicks += r.link_clicks || 0;
  });

  const daily_trends = Object.values(trendMap).sort((a, b) => a.date.localeCompare(b.date)).map(d => ({
    date: d.date,
    spend: Math.round(d.spend * 100) / 100,
    revenue: Math.round(d.revenue * 100) / 100,
    purchases: d.purchases,
    roas: d.spend > 0 ? Math.round((d.revenue / d.spend) * 100) / 100 : 0,
    cpa: d.purchases > 0 ? Math.round((d.spend / d.purchases) * 100) / 100 : 0,
    impressions: d.impressions,
    clicks: d.link_clicks
  }));

  // Platform Breakdown
  const platformMap = {};
  records.forEach(r => {
    const p = r.platform || 'Meta';
    if (!platformMap[p]) platformMap[p] = { platform: p, spend: 0, revenue: 0, purchases: 0, impressions: 0 };
    platformMap[p].spend += r.spend || 0;
    platformMap[p].revenue += r.purchases_conversion_value || 0;
    platformMap[p].purchases += r.purchases || 0;
    platformMap[p].impressions += r.impressions || 0;
  });

  const platform_breakdown = Object.values(platformMap).map(p => ({
    platform: p.platform,
    spend: Math.round(p.spend * 100) / 100,
    revenue: Math.round(p.revenue * 100) / 100,
    roas: p.spend > 0 ? Math.round((p.revenue / p.spend) * 100) / 100 : 0
  }));

  return {
    totals: {
      total_spend: Math.round(totals.spend * 100) / 100,
      total_revenue: Math.round(totals.revenue * 100) / 100,
      total_purchases: totals.purchases,
      overall_roas: overall_roas,
      cpa: cpa,
      ctr: ctr,
      cpc: cpc,
      cpm: cpm,
      total_impressions: totals.impressions,
      total_link_clicks: totals.link_clicks,
      total_landing_page_views: totals.landing_page_views,
      total_adds_to_cart: totals.adds_to_cart,
      total_checkouts_initiated: totals.checkouts_initiated
    },
    daily_trends: daily_trends,
    platform_breakdown: platform_breakdown,
    total_records: records.length
  };
}

function computeNomenclatureTable(dimension, clientId, startDate, endDate) {
  let records = STORE.records;
  if (clientId) records = records.filter(r => r.client_id === clientId);
  if (startDate) records = records.filter(r => r.date >= startDate);
  if (endDate) records = records.filter(r => r.date <= endDate);

  const dimFieldMap = {
    category: "category_collection",
    product: "product_name",
    funnel: "funnel",
    offer: "sale_offer",
    audience: "audience_type",
    hook: "concept_angle_hook",
    format: "format",
    landing_page: "landing_page"
  };

  const field = dimFieldMap[dimension] || "category_collection";
  const group = {};

  records.forEach(r => {
    const val = r[field] || "Unknown";
    if (!group[val]) {
      group[val] = {
        dimension_value: val,
        spend: 0,
        revenue: 0,
        purchases: 0,
        lpv: 0,
        impressions: 0,
        clicks: 0,
        atc: 0,
        ic: 0
      };
    }
    group[val].spend += r.spend || 0;
    group[val].revenue += r.purchases_conversion_value || 0;
    group[val].purchases += r.purchases || 0;
    group[val].lpv += r.landing_page_views || 0;
    group[val].impressions += r.impressions || 0;
    group[val].clicks += r.link_clicks || 0;
    group[val].atc += r.adds_to_cart || 0;
    group[val].ic += r.checkouts_initiated || 0;
  });

  return Object.values(group).map(g => ({
    dimension_value: g.dimension_value,
    spend: Math.round(g.spend * 100) / 100,
    purchases_conversion_value: Math.round(g.revenue * 100) / 100,
    purchases: g.purchases,
    purchase_roas: g.spend > 0 ? Math.round((g.revenue / g.spend) * 100) / 100 : 0,
    cost_per_purchase: g.purchases > 0 ? Math.round((g.spend / g.purchases) * 100) / 100 : 0,
    landing_page_views: g.lpv,
    adds_to_cart: g.atc,
    checkouts_initiated: g.ic,
    ctr: g.impressions > 0 ? Math.round((g.clicks / g.impressions) * 10000) / 100 : 0,
    cpc: g.clicks > 0 ? Math.round((g.spend / g.clicks) * 100) / 100 : 0
  })).sort((a, b) => b.spend - a.spend);
}

// ----------------- Auto-Sync The Sunya on Startup if empty ----------------- //
async function autoSeedSheet() {
  if (STORE.records.length === 0) {
    const sunya = STORE.clients.find(c => c.name === "The Sunya");
    if (sunya && sunya.google_sheet_url) {
      console.log('Fetching initial Google Sheet data for The Sunya...');
      try {
        const csvData = await fetchSheetCsv(sunya.google_sheet_url, sunya.google_sheet_gid);
        const parsedRows = parseCsv(csvData);
        STORE.records = parsedRows.map(r => cleanRecord(r, sunya.id, sunya.name));
        sunya.last_sheet_synced_at = new Date().toISOString();
        saveStore();
        console.log(`Auto-seeded ${STORE.records.length} records for The Sunya.`);
      } catch (err) {
        console.warn('Auto-seed note:', err.message);
      }
    }
  }
}

// ----------------- Start Server ----------------- //
server.listen(PORT, '0.0.0.0', () => {
  console.log(`====================================================`);
  console.log(` TGM Reporting Studio LIVE Node.js Server`);
  console.log(` Port: ${PORT}`);
  console.log(` Environment: ${process.env.NODE_ENV || 'production'}`);
  console.log(` Health: http://localhost:${PORT}/api/health`);
  console.log(` Portal: http://localhost:${PORT}`);
  console.log(`====================================================`);
  autoSeedSheet();
});
