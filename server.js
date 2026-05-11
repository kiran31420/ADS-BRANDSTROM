require('dotenv').config();
const express = require('express');
const path    = require('path');
const fetch   = require('node-fetch');

const app      = express();
const TOKEN    = process.env.FB_ACCESS_TOKEN || '';
const ACCOUNTS = (process.env.FB_AD_ACCOUNTS || '').split(',').map(s => s.trim()).filter(Boolean);
const FB_VER   = 'v21.0';
const FB_BASE  = `https://graph.facebook.com/${FB_VER}`;

const AD_FORMATS = [
  { key: 'DESKTOP_FEED_STANDARD', label: '🖥️ Feed Desktop' },
  { key: 'MOBILE_FEED_STANDARD',  label: '📱 Feed Mobile'  },
  { key: 'INSTAGRAM_STANDARD',    label: '📸 IG Feed'      },
  { key: 'INSTAGRAM_STORY',       label: '📖 IG Story'     },
  { key: 'FACEBOOK_STORY_MOBILE', label: '📖 FB Story'     },
  { key: 'INSTAGRAM_REELS',       label: '🎬 Reels'        },
];

app.use(express.json());
app.use(express.static(path.join(__dirname, 'static')));

async function fbGet(url, params = {}) {
  const qs  = new URLSearchParams({ access_token: TOKEN, ...params });
  const res = await fetch(`${url}?${qs}`);
  return res.json();
}

// ── GET /api/accounts ─────────────────────────────────────
app.get('/api/accounts', async (req, res) => {
  if (!TOKEN || !ACCOUNTS.length)
    return res.status(500).json({ error: 'ยังไม่ได้ตั้งค่า FB_ACCESS_TOKEN หรือ FB_AD_ACCOUNTS ใน Variables' });

  const accounts = await Promise.all(ACCOUNTS.map(async id => {
    const data = await fbGet(`${FB_BASE}/act_${id}`, { fields: 'id,name,account_status' });
    if (data.error) return { id, name: `act_${id}`, active: false };
    return { id, name: data.name || `act_${id}`, active: data.account_status === 1 };
  }));
  res.json({ accounts });
});

// ── GET /api/search ───────────────────────────────────────
app.get('/api/search', async (req, res) => {
  const { q, search_type = 'ad', account_id } = req.query;
  if (!q || !account_id) return res.status(400).json({ error: 'q และ account_id จำเป็น' });

  const filtering = JSON.stringify([{ field: 'name', operator: 'CONTAIN', value: q }]);
  const endpoint  = search_type === 'campaign' ? 'campaigns' : 'ads';
  const fields    = search_type === 'campaign' ? 'id,name,status,objective' : 'id,name,status';

  const data = await fbGet(`${FB_BASE}/act_${account_id}/${endpoint}`, { fields, filtering, limit: 25 });
  if (data.error) return res.status(400).json({ detail: data.error.message });

  res.json({
    results: (data.data || []).map(item => ({
      id: item.id, name: item.name,
      status: item.status || '', type: search_type,
    }))
  });
});

// ── GET /api/campaign-ads/:id ─────────────────────────────
app.get('/api/campaign-ads/:id', async (req, res) => {
  const data = await fbGet(`${FB_BASE}/${req.params.id}/ads`, { fields: 'id,name,status', limit: 25 });
  if (data.error) return res.status(400).json({ detail: data.error.message });
  res.json({ results: data.data || [] });
});

// ── GET /api/preview/:ad_id ───────────────────────────────
app.get('/api/preview/:ad_id', async (req, res) => {
  const previews = [];
  for (const fmt of AD_FORMATS) {
    const data = await fbGet(`${FB_BASE}/${req.params.ad_id}/previews`, { ad_format: fmt.key });
    if (data.data && data.data[0]) {
      const body = data.data[0].body;
      const m    = body.match(/src="([^"]+)"/);
      const src  = m ? m[1].replace(/&amp;/g, '&') : '';
      previews.push({ format: fmt.key, label: fmt.label, body, src });
    }
  }
  res.json({ previews });
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => console.log(`✅ Server running on port ${PORT}`));
