# Copilot Instructions for CYD Bitcoin Project

## Project Overview
CYD Bitcoin Information & Mining Display - an educational Bitcoin mining interface on the Cheap Yellow Display (CYD) ESP32 board.

**Goal**: Build a Bitcoin mining education system in phases:
- **Phase 1 (MVP)**: Real-time Bitcoin price, current block info, last block hash, timing, difficulty
- **Phase 2+**: Mining simulation and actual mining capability with our own code (no copied internet code)

**Hardware**: Cheap Yellow Display (CYD) ESP32 board with integrated 320x240 LCD display
**Language**: Python (CircuitPython/MicroPython)
**Philosophy**: Learn, build simple, build fast, no code duplication from internet sources

## Getting Started

### Hardware Setup
- **Board**: Cheap Yellow Display (CYD) ESP32 with 320x240 LCD
- **Display Driver**: ILI9341 (typically via SPI)
- **Touch Input**: XPT2046 (optional, can be added later)
- **Communication**: WiFi (ESP32 built-in)

### Software Stack
- **Language**: Python (CircuitPython or MicroPython)
- **Display Library**: LVGL (Light and Versatile Graphics Library) or custom drivers
- **HTTP Client**: `urequests` (for API calls)
- **Data Sources**:
  - Bitcoin Price: CoinGecko API (free, no key required)
  - Block Info: Blockchain.com API or Bitcoin Core RPC (if running local node)
  - Difficulty: Bitcoin blockchain APIs

### Python Environment
```bash
# For local development/testing before deploying to ESP32:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Device Setup** (when ready):
- Flash CircuitPython or MicroPython to ESP32
- Copy Python files to device filesystem
- Configure WiFi credentials in `config.py` (never commit secrets)

## Development Workflow

### Phase 1: Bitcoin Information Display (MVP)
**Goal**: Display real-time data with minimal latency and clear loading states

**Core Requirements**:
1. **Bitcoin Price** - Current USD/ZAR price (refresh every 60s)
2. **Current Block Info** - Block number, timestamp, transaction count
3. **Last Block Hash** - Full hex hash from most recent block
4. **Block Difficulty** - Current network difficulty (for mining reference)
5. **Timing Display** - SAST local time + countdown since last block ended
6. **Network Status** - Loading indicator, connection status, last update time

**Display Layout** (320x240 screen):
```
┌──────────────────────────────────┐
│ ⚡ BTC: $45,320.50 | SAST: 14:32│
├──────────────────────────────────┤
│ Block #863,452                   │
│ Mined: 2.5 min ago (Δ 2:34)     │
│ Difficulty: 84.2T               │
├──────────────────────────────────┤
│ Hash (last block):               │
│ 0a3f7e2c... [COPY]              │
├──────────────────────────────────┤
│ Txns: 2,847  Fees: 125 BTC      │
│ [Loading...] [Refresh] [Menu]   │
└──────────────────────────────────┘
```

### Code Organization
```
cyd bitcoin/
├── .github/
│   └── copilot-instructions.md
├── src/
│   ├── main.py                 # Entry point
│   ├── config.py               # Settings (WiFi, API endpoints)
│   ├── bitcoin_api.py          # API calls (blockchain, price)
│   ├── display_manager.py      # Screen rendering
│   ├── ui_components.py        # Reusable UI elements
│   └── utils.py                # Helpers (time, formatting)
├── tests/
│   └── test_bitcoin_api.py     # Unit tests (run on PC)
├── firmware/                   # ESP32 binaries and config
├── docs/
│   ├── ARCHITECTURE.md         # Phase breakdown
│   ├── API_REFERENCE.md        # Data sources
│   └── CONVENTIONS.md          # Code standards
├── requirements.txt            # PC-side dependencies
├── config.example.py           # Template (commit this, not config.py)
└── notes.md                    # Project decisions
```

### Coding Principles for This Project
1. **Performance First**: Minimal RAM usage, efficient network calls
2. **No Internet Code Duplication**: Write custom implementations (even if slower initially)
3. **Modular Design**: Each component (API, display, logic) is independently testable
4. **Graceful Degradation**: Show what we have, load more as it arrives
5. **Comments for Understanding**: Only explain WHY, not WHAT (code should be clear)

## Key Bitcoin Mining Concepts

### For Phase 1 (Information Display)
Your approach is **correct for the foundation**. You need:

| Data | Purpose | Source | Refresh Rate |
|------|---------|--------|--------------|
| **Block Hash** | Starting point for mining next block | Blockchain API | Every new block (~10min) |
| **Difficulty** | Proof-of-Work target (hash must be < this) | Blockchain API | Every 2016 blocks (~2 weeks) |
| **Block Header** | Data to hash when mining | Blockchain API | Every new block |
| **Merkle Root** | Transaction tree root (part of header) | Blockchain API | Every new block |
| **Timestamp** | Current block time (for validation) | Blockchain API | Every new block |
| **Previous Block Hash** | Chain linkage (in next block header) | Blockchain API | Every new block |
| **Coinbase Reward** | 6.25 BTC + fees (for motivation) | Blockchain API | Every new block |
| **Network Hashrate** | Billions of GH/s (perspective) | Blockchain API | Every new block |

### Additional Data for Future Phases
**Phase 2 (Mining Simulation)**:
- Merkle tree construction from transactions
- Block header structure and serialization
- SHA256 implementation (or use built-in)
- Nonce iteration strategy
- Difficulty target conversion

**Phase 3 (Real Mining)**:
- Mempool monitoring (pending transactions)
- Mining pool protocols (Stratum, etc.)
- ASIC/GPU optimization strategies
- Hash rate monitoring and optimization

### Critical Understanding
**Bitcoin Mining = Finding a valid nonce that makes the block hash < difficulty target**

```
Block Header = version + prevBlockHash + merkleRoot + timestamp + difficulty + nonce
Hash = SHA256(SHA256(Block Header))

Mining: Increment nonce until Hash < Difficulty_Target
```

For ESP32 educational mining:
- You'll get millions of hashes per second (not billions like ASICs)
- Very unlikely to find a valid block solo (probability ~1 in 2^192 currently)
- Pool mining is realistic; solo mining is for learning only

### Recommended First Data Sources
1. **CoinGecko API** (free, no auth)
   - `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`
   
2. **Blockchain.com API** (free, public)
   - Latest block: `https://blockchain.info/latestblock?format=json`
   
3. **BlockCypher** (free tier)
   - Block details and difficulty
   
4. **Bitcoin Core RPC** (if running local node)
   - Most reliable, but requires setup

## Code Conventions & Best Practices

### Python Style
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Line Length**: Max 100 characters (tight for ESP32 memory)
- **Type Hints**: Not required but helpful for documentation
- **Docstrings**: Brief one-liners for functions, explain non-obvious logic

### ESP32-Specific Optimization
- Minimize imports (memory constrained)
- Pre-compile regular strings to save memory
- Use constants for static data
- Avoid deep recursion (stack limited)
- Cache API responses locally
- Implement connection timeout/retry logic

### Testing Strategy
- **PC Tests**: Mock API calls, test formatting and calculations
- **Device Tests**: Limited testing on ESP32 (use print debugging)
- Run tests: `python -m pytest tests/`
- Run single test: `pytest tests/test_bitcoin_api.py::test_function_name`

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

Relates to: <phase/block>
```
Examples:
- `feat(display): add bitcoin price widget to main screen`
- `fix(api): handle blockchain.com rate limiting`
- `docs(architecture): explain mining phases and data flow`

- Keep [notes.md](../notes.md) updated with architectural decisions and project milestones
- Add docstrings to all public functions and classes
- Maintain a CONTRIBUTING.md when the project is ready for external contributors

## CI/CD & Deployment

Currently not set up. To be configured when project reaches alpha stage:
- GitHub Actions workflows for testing and linting
- Release strategy and versioning (semantic versioning recommended)
- Deployment procedures

## AI Assistant Guidelines

When working with Copilot or other AI assistants in this repository:
1. Refer back to [notes.md](../notes.md) for context
2. Ensure generated code matches the conventions established in this file
3. Add tests when asking for new features or refactoring
4. Update this file as conventions are solidified
5. Keep all Python code compatible with the target Python version

## Next Steps for Project Setup

As the project grows, expand this file with:
- Specific Python version requirement
- Build/test/lint command details
- Architecture documentation
- Database/external service setup (if applicable)
- Known issues or technical debt
- Team-specific conventions
