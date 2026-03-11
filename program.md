# Atlas Program — Autonomous Intelligence Research

*This file is the "research org code" for Atlas. Agents read this to understand what to research, how to grade results, and how to improve over time. Inspired by Karpathy's autoresearch pattern.*

---

## Mission
Produce weekly-grade competitive intelligence for Phoenix clients using overnight compute. Each run should surface something NEW — not repackage what we already know.

## Clients (Active)
- **Pharaoh** — DEX/AMM on Avalanche (pharaoh.exchange). Competitors: Trader Joe, Pangolin, Camelot
  - **Search strings**: `pharaoh.exchange`, `"pharaoh exchange" avalanche`, `@pharaoh_xyz`, `pharaoh DEX TVL`
  - **DeFiLlama**: https://defillama.com/protocol/pharaoh-exchange
- **Benqi** — Lending protocol on Avalanche (benqi.fi). Competitors: Aave, Compound, Radiant Capital
  - **Search strings**: `benqi.fi`, `"benqi" lending avalanche`, `@BenqiFinance`
  - **DeFiLlama**: https://defillama.com/protocol/benqi
- **Magic Eden** — NFT/token marketplace (magiceden.io). Competitors: Tensor, OpenSea, Blur
  - **Search strings**: `magiceden.io`, `"magic eden" marketplace NFT 2026`, `@MagicEden`, `magic eden volume`, `magic eden bitcoin ordinals`
  - **DeFiLlama**: https://defillama.com/protocol/magic-eden
- **Bullet** — Perpetuals DEX on Solana L2 (formerly Zeta Markets — rebrand). Competitors: Jupiter Perps, Drift Protocol, Mango Markets
  - **Search strings**: `"Bullet perps" solana`, `bullet-xyz perps DEX`, `@bulletdex`, `bullet perpetuals solana`
  - **Focus intel**: funding rates, OI, new trading pairs, liquidations, TVL changes, competitor protocol upgrades
  - **DeFiLlama**: https://defillama.com/protocol/bullet
- **Pro Rata/Gist** — (TBD)

---

## Research Pipeline (Priority Order)

### Tier 0 — DeFiLlama TVL Signals (check FIRST for DeFi clients)
- Check DeFiLlama protocol pages for TVL changes
- **Any TVL change >5% in 7 days = Tier 1 intel** regardless of announcements
- This is a HIGH confidence signal that should be checked before standard news search

### Tier 1 — Client News (always check first)
For DeFi clients, use site-specific and exact searches:
- `[ClientName].fi` or `[ClientName].io` or `[ClientName].exchange` (site-specific)
- `"[Client Name]" [category] [year]` — always use full name in quotes
- `[ClientName] [category]` — e.g., "benqi lending", "pharaoh exchange", "magic eden NFT"
- Twitter: search `@[Handle]` specifically for official account
Sources: Twitter/X, their official Discord, their blog/medium
**Threshold**: Any post with >50 engagements in last 48h counts as news.

**Client-specific search rules:**
- **Pharaoh**: NEVER search just "Pharaoh" — always append "exchange", "avalanche", or "DEX"
- **Magic Eden**: ALWAYS use "magic eden" in quotes OR their domain — never standalone
- **Benqi**: Always append "avalanche" or "lending" to disambiguate from the Japanese name
- **Bullet**: Search "Bullet perps" (not just "Bullet") to avoid noise

### Tier 2 — Competitor Intel (if no client news)
For each competitor:
- What did they ship or announce in last 7 days?
- Any community reaction (positive or negative)?
- Token price or TVL movement >10%?

**Competitor search strings:**
- **Pharaoh competitors**: `"trader joe" avalanche`, `"pangolin" avalanche DEX`, `camelot DEX`
- **Benqi competitors**: `"aave" avalanche`, `radiant capital`, `compound finance`
- **Magic Eden competitors**: `tensor.trade`, `blur.io NFT`, `opensea volume`
- **Bullet competitors**: `jupiter perps solana`, `drift protocol`, `mango markets` (NOTE: Zeta Markets = Bullet's former name, NOT a competitor)

**Output**: "Competitor did X. Client should respond/capitalize by Y."

### Tier 3 — Platform Trends (if no competitor news)
Check what's performing on the client's primary platforms:
- Twitter: What content format is trending? (threads, charts, hot takes, tutorials)
- Discord: What questions/topics are active in similar communities?
**Output**: "Articles/threads/X are getting 2x engagement this week. Recommend client post [format] on [topic]."

### Tier 4 — SEO/AEO Audit (weekly cadence, rotate by client)
Run a surface-level audit on client's website:
- Are they capturing their primary keywords?
- Any obvious gaps vs competitors in search?
- AI answer engine presence (would their site appear in an LLM answer about their category?)
**Output**: Top 3 SEO/AEO gaps with recommended actions.

---

## Novelty Filter (Critical)

Before surfacing any intel, compare against `intel-log.json`:
- Has this finding appeared in a report in the last 14 days?
- If YES → skip unless there's new development
- If NO → include with confidence score

**Confidence scoring:**
- `HIGH`: Primary source (official announcement, their own tweet)
- `MEDIUM`: Secondary source (news article, community discussion)
- `LOW`: Inferred (price movement, activity pattern)

---

## Output Format

Save to: `reports/YYYY-MM-DD-[client]-intel.md`
Post summary to: Discord #research-center (1475882687754670153) and #inbox (1475882688559845541)

```
## Atlas Intel — [Client] — [Date]
**Tier**: [1/2/3/4] | **Confidence**: [HIGH/MEDIUM/LOW] | **Novel**: [YES/NO]

### Finding
[What was found]

### Why It Matters
[For Phoenix: what does this mean for content/strategy?]

### Recommended Action
[Specific next step for Phoenix team]
```

---

## Self-Improvement Loop

After each run, update `intel-log.json`:
```json
{
  "date": "YYYY-MM-DD",
  "client": "Pharaoh",
  "tier_reached": 2,
  "sources_checked": ["twitter", "discord", "coinmarketcap"],
  "novel_findings": 1,
  "sources_that_returned_nothing": ["blog"],
  "confidence": "MEDIUM"
}
```

Over time, the log reveals:
- Which sources consistently find intel → prioritize those
- Which sources return nothing → deprioritize or remove
- Which clients need Tier 3/4 most → they're in "quiet periods"
- Best research cadence per client

**Weekly review**: Every Sunday, agent reads last 7 days of intel-log.json and updates this program.md with source priority adjustments. This is the self-improvement step.

---

## Data Sources (Approved)
- **DeFiLlama** (https://defillama.com) — TVL data, protocol metrics. ALWAYS check first for DeFi clients.
- web_search (Brave API) — primary
- Twitter/X search via RapidAPI endpoint (when available)
- Discord community scraping (for public servers)
- CoinGecko for token metrics
- n8n webhook (future: automated feed routing)

---

## Twitter Handles to Monitor

### Benqi
- @BenqiFinance (official)
- @0xBread (founder)
- @avalancheavax (ecosystem)

### Pharaoh
- @pharaoh_xyz (official)
- @pharaoh_exchange (check both)
- @avalancheavax (ecosystem)

### Magic Eden
- @MagicEden (official)
- @amirsole1 (CEO)

### Bullet
- @bulletdex (official - verify handle)
- @solana (ecosystem)

---

*Last updated: 2026-03-10 | Next review: 2026-03-17*
