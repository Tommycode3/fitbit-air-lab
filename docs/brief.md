> Original design brief (translated from Italian). Written as instructions for an AI coding agent; phases 1-5 are plans, not implemented.

# Pulse — personal recovery/strain app for the Fitbit Air

> Brief for Claude Code. Read all of it before writing code. Work in phases, and at the end of each phase stop and show me what works.

## Goal

Turn my Google Fitbit Air into **my** wearable: my app, my metrics, my aesthetic, my rules on data and sampling rates. The end goal is to depend on Google as little as possible.

We do this aggressively, at increasing levels of control (see "Control strategy"). Each level must work on its own, so if one gets stuck we don't lose what we already have.

Functionally the app does what Whoop does, and more:
- daily recovery;
- daily and per-workout load;
- in-depth sleep analysis;
- trends and a journal to correlate habits and metrics;
- all at the frequency and with the metrics I decide.

## Control strategy

| Level | What I own | How | Dependence on Google |
|---|---|---|---|
| L1 — Data | My data, my metrics, my app | Google Health API + standard BLE Heart Rate | High: the band syncs with Google Health |
| L2 — Channel | The band → phone sync, without the Google app | Reverse engineering of the proprietary protocol + our own client | Low: Google is needed only for the initial pairing, if at all |
| L3 — Device | Firmware, sampling rates, raw signal (PPG, accelerometer, temperature) | Hardware access to the microcontroller, firmware dump and analysis, possibly our own firmware | None |
| Plan B | A band that is entirely mine | Open hardware with the same form factor, if L3 is blocked | None |

- L1 is built right away and is the foundation of the app (Phases 0–3).
- L2 and L3 proceed in parallel as research (Phase 4 and Phase 5).
- The app is designed with a **data-source abstraction layer**: adding L2 or L3 does not require rewriting metrics or UI, only adding a source.

Functional inspiration: the best of all wearables on the market (Whoop, Oura, Garmin, Apple Watch, Google Health), see "Feature catalog". Our own identity: no third-party product names, logos, colors, scales or copy. Metrics have our own names and formulas, documented.

## Platform constraints

- Phone: **iPhone** (decided 2026-09-25).
  - iPhone: native SwiftUI + CoreBluetooth app (reliable background BLE is required).
  - Android: Kotlin + Jetpack Compose.
  - No cross-platform frameworks, unless I ask otherwise.
- Lightweight backend, needed because the Google Health API is cloud-based: Python (FastAPI) + Postgres (Supabase is fine). It handles OAuth, webhooks, synchronization and metric computation.
- Lab tools in Python (`bleak`) to run on the Mac, to explore BLE before porting it into the app.

## Data sources (in priority order)

1. **Google Health API** (`health.googleapis.com/v4/`), via Google OAuth.
   - My own Google Cloud project, consent screen in testing mode, me as the only test user.
   - Data: sleep with stages, HRV, resting heart rate, respiratory rate, SpO2, temperature, steps, calories, workouts, intraday heart rate.
   - Use webhooks where available, otherwise incremental polling.
   - Verify the endpoints against the current documentation: the API is new and changing. Do not invent schemas.
2. **Standard BLE Heart Rate Service (0x180D)**, available when "Share heart rate / Always visible" is enabled on the Air.
   - Read characteristic 0x2A37 and fully parse the flags (uint8/uint16 format, sensor contact, energy expended, **RR intervals**).
   - Automatic reconnection: the connection is one-to-one and often drops at the end of a workout.
3. **Fitbit proprietary protocol** (research phase, see Phase 4). Only if the first two sources are not enough.

## Metrics (our names and formulas)

Each metric has a documented formula in `docs/metrics.md`, unit tests, and the ability to see "why" the number is what it is.

- **Readiness (0–100)**, composed of:
  - nightly HRV (rMSSD, deep-sleep window or last hours of sleep) relative to the 30-day personal baseline, as a z-score;
  - resting heart rate relative to baseline;
  - respiratory rate;
  - last night's sleep relative to need;
  - temperature deviation.

  Configurable weights. Computed only with at least 4 nights of baseline; before that, show "calibrating".
- **Load (cardiovascular load)**: zone-based TRIMP (Edwards or Banister) on intraday heart rate and, when available, the BLE stream. Zones based on personal max HR and resting HR. Two values: daily load and per-workout load.
- **Acute/chronic load**: 7/28-day ACWR, with the optimal band highlighted.
- **Sleep**:
  - duration, efficiency, stages, regularity (sleep regularity index), sleep debt;
  - need computed as baseline + extra tied to the day's load + debt repayment;
  - recommended bedtime.
- **Live mode**:
  - real-time heart rate and current zone;
  - live HRV (rMSSD over a sliding window) if RR intervals arrive;
  - breathing / HRV biofeedback sessions with recording.
- **Journal**:
  - quick evening check-in (caffeine, alcohol, late training, screens, stress, etc.), with customizable questions;
  - after 30+ days, an analysis shows which factors actually move Readiness and sleep (effect size + confidence interval, no correlations passed off as causation).

## Feature catalog

Goal: take the best feature in each category from each wearable and reimplement it on the Air's data. We replicate the idea, not the brand: no third-party trade names ("Body Battery", "Strain", "Resilience", etc.). Choose our own names, short and consistent.

Feasibility legend with the Air:
- ✅ doable with the available data (API + BLE)
- 🟡 approximation: must be validated and declared as an estimate in the UI
- ❓ depends on reverse engineering (Phase 4)
- ❌ requires a sensor the Air does not have. Not implemented and not simulated.

### Tier 1 — the core (MVP)

| Feature | Inspired by | Feasibility | Notes |
|---|---|---|---|
| Daily readiness | Whoop Recovery, Oura Readiness, Garmin Training Readiness, Apple Readiness | ✅ | Already defined above |
| Daily and per-workout load | Whoop Strain, Garmin Training Load, Apple Training Load | ✅ | Zone-based TRIMP |
| HRV status: 7-day average relative to the personal normal range | Garmin HRV Status | ✅ | Baseline ± deviation band |
| Sleep score + stages + efficiency + latency + regularity | Oura, Whoop, Garmin | ✅ | |
| Sleep need and recommended bedtime | Whoop Sleep Planner, Garmin Sleep Coach | ✅ | |
| Acute/chronic load and training status (productive, maintaining, overreaching, detraining) | Garmin Training Status | ✅ | ACWR + VO2max trend |
| Recommended recovery time after a workout | Garmin Recovery Time | 🟡 | From load + readiness |
| Journal and behavior impact | Whoop Journal, Oura Tags | ✅ | |
| Live HR + zones + live HRV | Whoop, Garmin | ✅ if RR intervals arrive via BLE | |
| Breathwork / HRV biofeedback | Whoop, Apple Mindfulness, Garmin | ✅ with RR | |

### Tier 2 — intelligence and trends

| Feature | Inspired by | Feasibility | Notes |
|---|---|---|---|
| Energy over the day (charges at night, drains with stress and activity) | Garmin Body Battery | 🟡 | Our own model on intraday HR, activity, sleep; declare that it is an estimate |
| Daytime stress | Garmin Stress, Whoop Stress Monitor | 🟡 | HR vs resting baseline, excluding movement. Better with live HRV |
| Resilience: ability to sustain load over 2–4 weeks | Oura Resilience | ✅ | Readiness + sleep + load trend |
| "Something's off" alert (temperature + resting HR + respiration abnormal together) | Oura Symptom/Health Radar, Apple Vitals | ✅ | Non-diagnostic language |
| Nightly vitals with personal range and highlighted outliers | Apple Vitals | ✅ | |
| Biological age / pace of aging from wearable metrics | Whoop Healthspan, Oura Cardiovascular Age | 🟡 | Only from VO2max, resting HR, HRV, sleep regularity, steps, zones. Documented formula, presented as an index, not as truth |
| Chronotype and ideal sleep window | Oura Chronotype | ✅ | From at least 3–4 weeks of data |
| Jet lag / circadian realignment | Oura, Whoop | ✅ | From phone time zone + calendar |
| Weekly and monthly report | Whoop, Oura, Garmin | ✅ | Dedicated view + notification |
| VO2max and fitness trend | Garmin, Apple, Google | ✅ | From the API. Our own estimate only for comparison |
| Training distribution (low/high aerobic, anaerobic) | Garmin Training Load Focus | ✅ | From time in zone |

### Tier 3 — coach and integrations

| Feature | Inspired by | Feasibility | Notes |
|---|---|---|---|
| AI coach that knows all my data | Whoop AI, Oura Advisor, Apple Workout Buddy, Google Health Coach | ✅ | LLM via API with tools that query the DB. Answers citing the data. No medical advice |
| Training plan adapted to readiness | Garmin Daily Suggested Workouts, Whoop | ✅ | |
| Strength logging (sets, reps, weight) + muscular load | Whoop Strength Trainer, Apple (iOS 27) | ✅ manual / 🟡 load | Quick input during the workout |
| Meals from photos + effect on sleep and readiness | Oura Meals | ✅ | Vision LLM. Correlations only after enough data |
| GPS for runs/rides | Garmin, Apple | 🟡 | The Air has no GPS: use the phone's during workouts |
| Import from other sources (scale, CGM, Apple Health/Health Connect) | Oura + Dexcom, Apple Health | ✅ | Optional |
| Smart alarm in the light-sleep phase | Whoop, Fitbit | ❓ | Requires controlling the Air's vibration (if it has one), or fall back to a phone alarm with live-estimated sleep |
| Inactivity reminders | Apple, Garmin | ✅ on the phone / ❓ on the band | |

### Excluded (missing hardware) — do not simulate

- ECG and our own AFib notifications: the Air has Google's AFib detection, but we do not build medical diagnostics.
- Blood pressure and hypertension notifications.
- Daylight exposure.
- Barometric altimeter and floors climbed, if the Air does not expose them.
- Anything requiring a screen or input on the band.

### Catalog rules

- Every feature is born with:
  - a short document in `docs/features/`: what it does, formula, required data, how we validate it;
  - a confidence indicator visible in the UI when it is 🟡.
- No medical or diagnostic claims. Where a feature touches health (nightly anomalies, biological age), the language is descriptive ("outside your usual range"), not clinical.
- If during development you find that a ✅ actually lacks the data, downgrade it and tell me.

## Design

Direction: minimalist, high-craft, technically dense. Taste references: Teenage Engineering, Nothing, Arc'teryx, Linear. It must not resemble Whoop.

- Dark mode first, light mode as polished as the other.
- Typography:
  - a strong grotesk for the interface;
  - a monospace for numbers (tabular figures);
  - hierarchy built with weight and size, not color.
- Palette:
  - nearly monochromatic;
  - a single accent color, used sparingly;
  - status colors (good/medium/low) are desaturated and never the only carrier of meaning.
- Home = one number, i.e. today's Readiness, large and with its "why" in one line. Then Load and Sleep. Everything else one tap away.
- Charts:
  - custom-drawn (Swift Charts / Compose Canvas), no default-library look;
  - thin grids, direct annotations instead of legends, scrub micro-interactions with haptics.
- Motion: short, physical transitions, no decorative animations.
- Home screen and lock screen widgets, Live Activity/persistent notification in live mode.
- Before writing UI, propose 2–3 visual directions as static mockups and wait for me to choose one.

## Phases

### Phase 0 — Setup and verification
- Repo scaffold: `app/`, `backend/`, `lab/` (Python scripts), `docs/`.
- `lab/ble_scan.py`: finds the Air, lists services and characteristics, dumps everything readable.
- `lab/hr_stream.py`: connects to 0x180D and saves timestamp, bpm and RR to CSV. Tell me whether RR intervals arrive: live HRV depends on this.
- **Exit criterion**: 10 minutes of recorded stream with no unhandled gaps.

### Phase 1 — Data pipeline
- Google Health OAuth in the backend.
- Historical sync (everything available) + incremental sync.
- Normalized data schema with the source and resolution of each sample.
- CSV/Parquet export script.
- **Exit criterion**: last 30 days in the DB, with a coverage report (which metrics, at what frequency, gaps).

### Phase 2 — Metrics engine
- Implement Readiness, Load, ACWR and Sleep in a pure, tested module, with personal baselines.
- Validation notebook: plots of the metrics on my real data, to judge them by eye.
- **Exit criterion**: stable and explainable metrics over 30 days.

### Phase 3 — App
- Design directions → choice → implementation.
- Tier 1 of the catalog first: Home, Sleep, Load, Trends, Journal, Live mode (BLE).
- Then Tier 2 and Tier 3, one feature at a time. Each feature is closed when it is validated on my data.
- The information architecture must not turn into a feature museum: at most 4–5 tabs. New features are integrated into existing views, they do not add random screens.
- Notifications:
  - morning: Readiness ready;
  - evening: recommended bedtime.

### Phase 4 — Reverse engineering the proprietary protocol (research)
Purpose: find out whether we can get from the band what sources 1–2 do not provide (e.g. higher-resolution data, accelerometer, cloud-free sync).

**Method**
1. Capture the traffic between the Air and the Google Health app:
   - Android: "Bluetooth HCI snoop log" in developer options + `adb bugreport`;
   - iPhone: Apple's Bluetooth logging profile + PacketLogger (Additional Tools for Xcode) on the Mac.
2. Record labeled sessions, one action at a time: sync, app open, workout start, settings change. Save them in `lab/captures/` with a log of what I did and when.
3. Analysis in Wireshark (filter `btatt`) + Python scripts to:
   - map proprietary services and characteristics;
   - identify framing, sequence numbers, checksums and compression;
   - distinguish commands from data.
4. First question to answer: **is the payload encrypted?** Look for handshakes, nonces and payload entropy.
   - If it is encrypted with per-device keys, stop. Document what you found and propose options to me with costs and risks, before going further.
5. If it is in plaintext or decodable: write a decoder in `lab/protocol/` with tests on the captures, then a `bleak` client that replicates the sync read-only.
6. Check work already done by others (Gadgetbridge, open-source Fitbit projects) before starting from scratch.

**Rules**
- Only on my device and read-only.
- No firmware writes and no commands that modify the band's state, unless I explicitly approve each one.
- No Google code, keys or assets copied into the repo.
- Everything documented in `docs/protocol.md`: what is certain, what is hypothesis, with references to the captures.
- **Deliverable**: a feasibility report (what we get, at what cost, how fragile it is to firmware updates) before integrating anything into the app.

**Outcome that unlocks L2**: a `bleak` client that syncs the Air's data read-only without opening the Google Health app. At that point the app depends on Google only for the initial pairing, and maybe not even for that.

### Phase 5 — Hardware and firmware access (research, parallel to Phase 4)
Purpose: get to the raw signal (PPG, accelerometer, temperature) and control the sampling rates. This is the level where you truly get "everything you want", and also the most uncertain. Treat it as exploration: it has value even if it stops, because it tells you what is inside.

**Steps, from least to most invasive**
1. **Reconnaissance, without opening anything.** Identify the Air's main chip and sensors from the FCC ID (FCC filings contain internal photos and schematics), public teardowns, and component datasheets. Many trackers use a well-known BLE SoC (Nordic nRF52 and similar). Knowing which one changes everything.
2. **Look for people who have already done it.** Alternative-firmware and reverse-engineering communities around similar trackers. Don't start from scratch if a dump exists.
3. **Debug interfaces.** Check whether the PCB exposes SWD/JTAG or UART. If so, try to read the firmware. On recent chips readout is almost always locked (readback protection): in that case, stop and document.
4. **Static firmware analysis,** if you obtain a dump: Ghidra to map how the sensors are read and how memory is structured.
5. **Custom firmware or app on the device:** only as the conclusion of everything else, never before, and only with my explicit approval.

**Hard rules**
- A single test device for L3, **never the band I wear every day**. Buy a second Air dedicated to the lab before opening anything. Hardware access can render it unusable (brick): this is an expected risk, not an accident.
- Every step that can modify or damage the device requires my explicit approval, one by one.
- Document everything in `docs/hardware.md`: chip, sensors, interfaces, what is readable, what is locked.
- If you are blocked at a level (protected chip, encrypted firmware), don't keep forcing it: write down what you found and we move to Plan B.

### Plan B — my own hardware (evaluation, not to be built now)
If L3 is a wall, the truly "all mine" path is a band with open hardware: same form factor, PPG sensor and accelerometer with public datasheets, a programmable nRF52/nRF53 SoC, our own firmware. The same app reads them without changes thanks to the data-source abstraction layer. For now Claude Code prepares only an **evaluation**: candidate components, cost, complexity, what is gained compared to the Air. Nothing is built until I decide. Treat it as a mini design review, not as a shopping list.

## Working rules

- No invented data or mocks shown as real: if data is missing, the UI says so.
- Secrets in `.env`, never in code.
- Health data stays in my backend: no third-party analytics services.
- Each phase closes with: what works, what doesn't, what you learned about the data, proposed next step.
- When the Google Health API documentation and actual behavior disagree, trust the actual behavior and note it.
