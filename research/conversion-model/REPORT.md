# Empirical Swimming Course Conversion at Scale: 6.32 Million Races, Hybrid Lakehouse Architecture, and Pace-Curve Splines

**Status:** Shipped in `turnmark-core` (`turnmark-empirical-2026`) alongside `ncaa-2025-27` (default) and `colorado-teamunify-2026`  
**Evaluation Receipt:** [`evaluation-checkpoint-06.json`](./evaluation-checkpoint-06.json) · **Acquisition Receipt:** [`acquisition-checkpoint-06.json`](./acquisition-checkpoint-06.json)  
**Embedded Snapshot:** [`data/empirical.json`](../../data/empirical.json) (`10.4 KB`) · **Companion Essay:** [`bristanback.com/posts/what-six-million-swims-say-about-the-wall`](https://bristanback.com/posts/what-six-million-swims-say-about-the-wall/)

---

## 1. Executive Summary

Published swimming course-conversion systems reduce the transition between a 25-yard pool (`SCY`), a 25-meter pool (`SCM`), and a 50-meter pool (`LCM`) to a single static formula per event:

1. **NCAA Rule 3, Appendix B (`ncaa-2025-27`)** applies a constant multiplier $y = \operatorname{truncate}_{0.01}(x \cdot f_{d,e,g})$ tuned to collegiate championship standards.
2. **Colorado Timing / TeamUnify (`colorado-teamunify-2026`)** applies a linear affine rule $y = \operatorname{truncate}_{0.01}(x \cdot m_{d,e} + b_{d,e})$ with a fixed per-50-meter turn offset independent of swimmer speed or competition category.

When predicting a swimmer's performance in another pool from a single observed race, a constant multiplier tilts across pace: conditioning on a single noisy swim induces regression to the mean on the next swim, and wall count and stroke decay vary by event and course direction.

To test published conversion rules and train an empirical replacement without cloud runtime dependencies or athlete privacy leakage, we assembled a **6,320,277-race US competition dataset (`national-checkpoint-15`)** spanning **213,105 source-scoped swimmers** and **4,721 meets** (`2010–2026`) across 13 regional and national archives (from 11 frozen export collections), paired with the public facility and organizational catalog in [`team-directory/`](./team-directory/CATALOG.md) (**8,240 source-scoped facility records**, **1,295 separately described pool basins** including **948 deduplicated USA Swimming certified courses**, **20,306 program listings** across **17,697 organizations**, and **92.2% meet-to-facility locality resolution** across `4,357 / 4,724` parsed meet headers).

Across **25,855 held-out 30-day same-swimmer course transitions** (`3,223` disjoint test swimmers, zero athlete overlap with training or validation):

- **Turnmark Empirical (`turnmark-empirical-2026`, Tier 1 Huber Pace-Curve Core)** reduces overall Mean Absolute Error (MAE) from **2.9362s (NCAA)** and **3.5329s (Colorado)** to **2.6658s** — a **9.21% error reduction vs. NCAA** ($z = -15.57$, swimmer-clustered bootstrap 95% CI $[-0.3021\text{s}, -0.2338\text{s}]$) and a **24.54% error reduction vs. Colorado** ($z = -22.92$, 95% CI $[-0.9378\text{s}, -0.7969\text{s}]$). On the untrimmed test set (`25,960` pairs, before the 18% ratio-outlier hygiene filter), MAE drops from **3.0261s (NCAA)** and **3.6174s (Colorado)** to **2.7530s**.
- **Universal event dominance:** `turnmark-empirical-2026` achieves lower MAE and lower Median AE than both NCAA and Colorado across **all 14 out of 14 canonical events** and **all 6 out of 6 course directions** (`SCY↔LCM`, `SCY↔SCM`, `SCM↔LCM`).
- **Distance freestyle & specialty strokes:** Error reductions in seconds are largest in longer and turn-sensitive events (while in relative percentage, `100-BK` at `-15.1%` and `200-BR` at `-21.0%` also rank among the top gains):
  - **1000SCY ↔ 800m Freestyle (`800-FR`):** MAE drops from **16.04s (NCAA)** and **17.59s (Colorado)** to **14.16s** (**-1.88s / -11.7% vs. NCAA**, **-3.43s / -19.5% vs. Colorado**).
  - **1650SCY ↔ 1500m Freestyle (`1500-FR`):** MAE drops from **31.20s (NCAA)** and **47.61s (Colorado)** to **27.88s** (**-3.32s / -10.6% vs. NCAA**, **-19.73s / -41.4% vs. Colorado**), and Median AE drops from **28.80s** to **21.57s** (`n = 38` 30-day test pairs; on the 60-day test set of `n = 120` pairs, Empirical is `27.78s` vs. `27.84s` for NCAA).
  - **500SCY ↔ 400m Freestyle (`400-FR`):** MAE drops from **7.06s (NCAA)** and **10.11s (Colorado)** to **6.24s** (**-0.82s / -11.6% vs. NCAA**, **-3.87s / -38.3% vs. Colorado**).
  - **200 Butterfly (`200-FL`):** MAE drops from **4.61s (NCAA)** and **5.59s (Colorado)** to **3.98s** (**-0.63s / -13.7% vs. NCAA**, **-1.61s / -28.8% vs. Colorado**; **-20.6% vs. NCAA** on the 60-day holdout).
  - **400 Individual Medley (`400-IM`):** MAE drops from **6.90s (NCAA)** and **9.62s (Colorado)** to **6.07s** (**-0.83s / -12.0% vs. NCAA**, **-3.54s / -36.9% vs. Colorado**; **-16.6% vs. NCAA** on the 60-day holdout).
  - **200 Breaststroke (`200-BR`):** MAE drops from **4.94s (NCAA)** and **6.25s (Colorado)** to **3.90s** (**-1.04s / -21.0% vs. NCAA**, **-2.35s / -37.6% vs. Colorado**).
- **Flattening NCAA pace-quartile bias:** On held-out transitions, NCAA exhibits a monotonic signed bias slope across within-event speed quartiles ($\hat{y} - y$) — predicting faster than actual for the fastest 25% of entered swims (`Q1`, **-0.554s**) and slower than actual for the slowest 25% (`Q4`, **+0.587s**). A distribution-matching `quantile_equivalence` baseline shows nearly the same tilt (**-0.503s** on `Q1` and **+0.535s** on `Q4`), confirming that the slope across conditioned entry-time quartiles is largely regression to the mean on a noisy single swim. Fitting the conditional expectation via `turnmark-empirical-2026` reduces the bias to **-0.244s** on `Q1`, **-0.022s** on `Q2`, **-0.034s** on `Q3`, and **-0.048s** on `Q4`.
- **Same-facility vs. cross-facility & altitude cohorts:** When both meets in a 30-day pair resolve by postal code or city/state to the **same facility record** (`n = 5,925` held-out pairs across `946` swimmers), `turnmark-empirical-2026` reaches an MAE of **2.1942s** (Median AE **1.36s**, bias **+0.025s**) vs. **2.5308s** for NCAA (**-13.3%**) and **3.3224s** for Colorado (**-34.0%**). Pairs across different resolved facilities (`n = 17,836` across `2,472` swimmers) have **+0.632s** higher MAE (`2.8261s` vs. `2.1942s`), and transitions involving altitude meets (`n = 1,287` pairs across `166` swimmers) drop from **3.9100s** (NCAA) and **4.5720s** (Colorado) to **3.6674s** (`Tier 1`) and **3.6005s** (`Tier 2 Age`).

---

## 2. Dataset & Hybrid Lakehouse Architecture

### 2.1 Corpus Scope (`national-checkpoint-15`)

All race records were ingested from publicly linked USA Swimming Local Swimming Committee (LSC) and YMCA National Championship Standard Data Interchange Format (`.sd3`, `.cl2`, `.hy3`) meet exports into a gitignored local store (`research/conversion-model/data/national-checkpoint-15/`). As documented in [`COLLECTION_PLAN.md`](./COLLECTION_PLAN.md) and [`acquisition-checkpoint-06.json`](./acquisition-checkpoint-06.json), these 13 regional and national archives reflect public bulk Hy-Tek archive availability (`nationally_representative: false`), not a balanced national probability sample.

| Metric | Value | Notes |
| :--- | ---: | :--- |
| **Input race records** | `6,325,452` | Across 5,222 meet archive files in 11 frozen export collections (13 regional/national archives) |
| **Conflicting duplicates excluded** | `5,175` | Identical swimmer/meet/event/round key with conflicting clock strings |
| **Usable distinct individual finishes** | **`6,320,277`** | Official timed finals, prelims, and finals only (no seeds, relays, splits, or DQs) |
| **Source-scoped swimmers** | **`213,105`** | Keyed `HMAC-SHA256` pseudonymous IDs from full registration numbers |
| **Distinct meets** | **`4,721`** | Overall date span `2010–2026` (only `AD` and `PV` begin in `2010`; see per-archive spans below) |
| **NCAA-event best-of-meet swims** | **`4,374,133`** | Fastest clean round per `(source, swimmer_id, meet_id, course, distance, stroke, category)` |
| **30-day same-swimmer transition pairs** | **`177,010`** | `176,306` clean directional pairs across `21,970` swimmers (`88,505` undirected pairs) |
| **60-day same-swimmer transition pairs** | **`406,726`** | Used for window sensitivity and sparse-event training augmentation |

#### Breakdown by Course, Category, and Source Archive

| Cohort / Source | Usable Races | Share | Notes |
| :--- | ---: | ---: | :--- |
| **Course: SCY** (25 yards) | `4,308,587` | `68.17%` | Primary winter/spring competition course |
| **Course: LCM** (50 meters) | `1,975,192` | `31.25%` | Primary summer championship & Olympic-trials course |
| **Course: SCM** (25 meters) | `36,498` | `0.58%` | Autumn/invitational short-course meters (`709` SCY↔SCM & `1,372` SCM↔LCM clean 30d test pairs) |
| **Category: Women** | `3,483,810` | `55.12%` | Published women's / girls' competition category |
| **Category: Men** | `2,836,467` | `44.88%` | Published men's / boys' competition category |
| **North Carolina Swimming** (`NC`) | `1,661,892` | `26.29%` | 1,046 archives (`2020–2026`, including SCM & summer LCM) |
| **Pacific Swimming** (`PC`) | `1,626,633` | `25.74%` | 1,489 archives (`2013–2026`, including Northern Nevada/Tahoe altitude & SCM) |
| **Southeastern Swimming** (`SE`) | `1,012,591` | `16.02%` | 680 regional archives (`2013–2026`; `734` total files in `southeastern-exports` including `UT`/`MT`) |
| **Michigan Swimming** (`MI`) | `862,281` | `13.64%` | 736 archives (`2016–2026`) |
| **Adirondack Swimming** (`AD`) | `610,386` | `9.66%` | 575 archives (`2010–2026`) |
| **Potomac Valley Swimming** (`PV`) | `184,444` | `2.92%` | 329 archives (`2010–2026`) |
| **South Dakota Swimming** (`SD`) | `171,993` | `2.72%` | 144 archives (`2018–2026`, including Black Hills / Rapid City altitude) |
| **Midwestern Swimming** (`MW`) | `93,821` | `1.48%` | 137 archives (`2019–2026`) |
| **Kentucky Swimming** (`KY`) | `34,979` | `0.55%` | 21 archives (`2026`) |
| **Montana Swimming** (`MT`) | `28,078` | `0.44%` | 15 archives (`2021–2026`, mountain-west elevation) |
| **YMCA National Championships** | `17,668` | `0.28%` | 8 national championship archives (`2025–2026`, `SCY` & `LCM`) |
| **Utah Swimming** (`UT`) | `14,331` | `0.23%` | 39 Wasatch Front archives (`2020–2026`) |
| **South Texas Swimming** (`ST`) | `1,180` | `0.02%` | 3 archives (`2026`) |

### 2.2 Public Facility & Program Catalog and Meet-to-Venue Locality Join

To evaluate environmental and facility cohorts, we use the committed public reference catalog in [`research/conversion-model/team-directory/`](./team-directory/CATALOG.md):

1. **[`team-directory/catalog/facilities.csv`](./team-directory/catalog/facilities.csv) (`8,240` source-scoped facility records)** and **[`team-directory/catalog/pool_basins.csv`](./team-directory/catalog/pool_basins.csv) (`1,295` separately described pool basins):**
   - Aggregates `4,956` USA Swimming national club-finder facility IDs, `1,528` USMS nationwide Places-to-Swim location rows, LSC/LMSC venue directories, summer-league pool directories, and `948` deduplicated USA Swimming pool measurement certification records (`2020` and `2022` editions).
2. **[`team-directory/snapshot/programs.csv`](./team-directory/snapshot/programs.csv) (`20,306` source-scoped program listings)** across **[`team-directory/snapshot/organizations.csv`](./team-directory/snapshot/organizations.csv) (`17,697` organizational identities)**, **[`team-directory/catalog/program_facilities.csv`](./team-directory/catalog/program_facilities.csv) (`7,497` program-location links)**, and **[`team-directory/governing-bodies.csv`](./team-directory/governing-bodies.csv) (`161` governing-body starting points)**.
3. **Meet-to-Facility Locality Join (`local/build_meet_venue_join.py`):**
   - Extracts SDIF `B1` meet headers across the cached regional archives and joins each meet to `team-directory/catalog/facilities.csv` in **two deterministic passes**: 5-digit postal code first (`3,831` meets), then `(city, state)` (`526` meets), preferring USA Swimming pool-certification records when multiple facility entries share a locality.
   - In total, **`4,357 / 4,724` (`92.2%`) parsed meets** resolve to a facility record, with **`4,296` (`90.9%`) carrying locality coordinates** across 32 states + DC, **`405` meets** carrying positive `B1` altitude claims, and **`408` meets** unmatched.
   - **Interpretation limit:** Because SDIF `B1` headers provide city, state, postal code, and optional declared altitude rather than a verified basin ID, this locality join is a facility proxy rather than a physical basin survey. Two meets in the `same_facility_transition` cohort resolved to the same `facility_id` in the same ZIP/city, which cannot distinguish a competition pool from an adjacent warm-up tank or directly observe a bulkhead move.

### 2.3 Hybrid Local Data Architecture (`LAKEHOUSE.md`)

A dataset of 6.32 million swims exposes a storage tension between two opposite access patterns:
- **Point lookups** ("show every race swum by athlete $s$ in chronological order" or "inspect meet $m$") require a low-latency B-tree index on `(source, swimmer_id, race_date)`.
- **Longitudinal analytical joins** ("self-join 6.32 million swims by athlete, event, and 30-day window across 6 course directions") require columnar compression, vectorized predicate pushdown, and partition pruning.

While 6.32 million rows could fit in a single indexed PostgreSQL instance, [`research/conversion-model/lakehouse.py`](./lakehouse.py) materializes a **near-zero-cost-at-rest dual-store local lakehouse** (`target/lakehouse-national-15/`, modeled in [`docs/LAKEHOUSE_COST_MODEL.md`](../../docs/LAKEHOUSE_COST_MODEL.md)) from the canonical ingest store and verifies exact row parity between both representations:

```
Ingested SDIF Union (races.sqlite3, HMAC-SHA256 keyed)
   ├──► Hot Indexed SQLite Store (hot.sqlite3)
   │      • Composite B-tree: athlete_history(source, swimmer_id, race_date, meet_id, race_id)
   │      • Size: 5,127.6 MB (811.3 bytes/row)
   │      • Point lookup latency (in-process first / repeat median): 0.173 ms / 0.011 ms
   │
   └──► Analytical Parquet Warehouse (warehouse/races/course=*/year=*/category=*/*.parquet)
          • Iceberg-shaped Hive partitioning + Zstandard columnar encoding
          • Size: 272.8 MB (43.2 bytes/row — 18.8× smaller than hot SQLite)
          • Filtered DuckDB analytical scan (first / repeat median): 3.94 ms / 2.32 ms
          • Exact parity verified: 6,320,277 rows, 0 duplicates, history_matches_iceberg = true
```

---

## 3. Longitudinal Pairing, Hygiene, and Model Hierarchy

### 3.1 Pairing Protocol & Adaptive Sparse-Event Supplementation

1. **Plausibility screen & best-of-meet reduction (`deduplicate_best_of_meet`):** Individual swims in the 14 canonical NCAA-convertible events are screened against conservative physical floors and ceilings (`MIN_PLAUSIBLE_CS` / `MAX_PLAUSIBLE_CS`), and collapsed to the fastest valid finish per `(source, swimmer_id, meet_id, course, distance, stroke, category)` (`4,374,133` swims) so prelim/final doubles at the same meet do not overweight multi-round swimmers.
2. **Directional transition pairing (`build_directional_pairs`):** Within each swimmer and canonical event, best-of-meet swims across different courses (`SCY↔LCM`, `SCY↔SCM`, `SCM↔LCM`) within $|\Delta t| \le 30$ days are matched greedily one-to-one by nearest date (`177,010` directional pairs; `88,505` undirected pairs).
3. **Outlier hygiene (`is_pair_ratio_outlier`):** To prevent unflagged touch-pad malfunctions or mis-keyed manual watches from distorting training or squared-error metrics, pairs are flagged as outliers if the target time differs by more than **18%** from the NCAA conversion (`|target_cs - ncaa_pred_cs| / ncaa_pred_cs > 0.18`) or if a same-distance `LCM` swim is faster than its paired `SCY` swim (`704` pairs / `0.40%`), leaving **`176,306` clean 30-day directional pairs** across **`21,970` swimmers**. Because the 18% screen references NCAA, all models are evaluated on both `clean_test` and `untrimmed_test`.
4. **Swimmer-disjoint 70/15/15 split (`swimmer_partition`):** Swimmers are partitioned deterministically by hashing `json.dumps([source, swimmer_id])` with `SHA-256` (`int.from_bytes(digest[:8], "big") % 100` into `<70` train, `<85` validation, `>=85` test):
   - **Train:** `123,250` clean 30d pairs (`15,425` swimmers)
   - **Validation:** `27,201` clean 30d pairs (`3,310` swimmers)
   - **Test:** `25,855` clean 30d pairs (`3,223` swimmers; `25,960` untrimmed pairs across `3,235` swimmers)
   - Zero swimmer appears in more than one partition.
5. **Adaptive 31–60d training supplementation & composite weighting (`augment_sparse_training_pairs`, `compute_training_weights`):** Distance freestyle events (`800-FR`, `1500-FR`, `400-FR`), 200m/yd form strokes (`200-FL`, `200-BK`, `200-BR`), `400-IM`, and `SCM` directions are swum less frequently within 30-day windows than 50/100 sprints. For those cohorts **only inside the training swimmer partition**, we supplement the 30-day training pairs with `30,572` non-overlapping 31–60 day transitions (`153,822` total training pairs). Training pairs receive a normalized composite weight fitted on Train only:
   $$w_i \propto n_{\text{swimmer},d,e}^{-0.50} \cdot n_{d,\text{region}}^{-0.30} \cdot n_{d,e,g,\text{age\_band}}^{-0.25} \cdot \exp(-\Delta\text{days}_i / 21.0)$$
   Validation and test sets remain strictly un-augmented and unweighted.

### 3.2 Two-Tier Model Hierarchy

We evaluate five empirical models across two input tiers against the two published baselines:

- **Published Baselines:**
  - `ncaa_2025_27`: Published NCAA Rule 3 constant multipliers.
  - `colorado_2026`: Published Colorado Timing linear factor + per-50m stroke offset formulas (plus distance-freestyle multipliers/offsets).
- **Non-Parametric Distribution Benchmark (`quantile_equivalence`, `EmpiricalQuantileModel`):**
  - 101-knot empirical quantile mapping $F_{\text{to}}^{-1}(F_{\text{from}}(x))$ fitted on training pairs per `(direction, event_key, category, age_band)` (for cells with $n \ge 25$), falling back to `(direction, event_key, category, "all")` and then NCAA.
- **Tier 1 — Core Input Parity (`swim`, `to`, `table` only):**
  - **`tier1_huber_pace_core` (`turnmark-empirical-2026` — shipped in production, `HuberPaceModel(include_age=False)`):**
    Fits a quadratic residual curve in standardized source time $z$ on top of the NCAA base prediction for each of the `154` `(direction, event, category)` cells (with $n \ge 8$) using weighted Iteratively Reweighted Least Squares (IRLS, 8 iterations) with Huber loss ($\delta = \max(0.30\text{s}, 0.02\,\mu_{d,e,g})$) and L2 ridge regularization ($\lambda = 0.05 + 1.5/n$ on non-intercept coefficients):
    $$z = \operatorname{clip}\!\left(\frac{x - \mu_{d,e,g}}{\sigma_{d,e,g}}, -3.0, 3.0\right), \qquad \Delta\hat{y}(x) = \beta_0 + \beta_1 z + \beta_2 z^2$$
    $$\hat{y}(x) = \operatorname{truncate}_{0.01}\!\left(x \cdot f_{\text{NCAA}}(d, e, g) + \operatorname{round}_{0.01}\!\left(\Delta\hat{y}(x)\right)\right)$$
    where $\mu_{d,e,g}$ is the cell median source time and $\sigma_{d,e,g} = \max(1.0\text{s}, \operatorname{pstdev}(x))$. To prevent small-sample overfitting in sparse cells, coefficients are shrunk via empirical Bayes ($\lambda_n = \frac{n}{n + 20}$): $\beta_0$ toward the pooled `(direction, event)` median residual and $(\beta_1, \beta_2)$ toward zero. Slopes are bounded ($|\beta_1| + 6|\beta_2| \le 0.30\,\sigma_{d,e,g}$) so the unrounded curve rises monotonically with entered time across $z \in [-3, 3]$ (after rounding $\Delta\hat{y}$ to `0.01s` and truncating $\hat{y}$ to `0.01s`, inputs one hundredth apart can occasionally swap order by `0.01s`).
  - **`tier1_gbm_core` (`BoundedHistogramGBM(include_age=False)`):**
    A custom bounded-depth gradient-boosted regression tree ensemble implemented in [`evaluate_and_train.py`](./evaluate_and_train.py) (up to 40 depth-3 trees per direction, 16 quantile candidate thresholds per feature, learning rate `0.08`, L2 leaf regularization `10.0`, minimum child weight `25.0`, Huber-clipped gradients at `0.80s`, and validation early stopping) fit **on top of `tier1_huber_pace_core`'s predictions** over `[source_time_cs, ncaa_pred_cs, pace_per_100, source_distance, stroke_id, cat_id, event_code]` to test whether non-linear tree splits capture residual structure left behind by the per-cell quadratic curve.
- **Tier 2 — Age-Aware Extensions (`swim`, `to`, `table`, `age_years`):**
  - **`tier2_huber_pace_age` (`HuberPaceModel(include_age=True)`):** Extends the per-cell Huber basis with standardized age $a_z = (\operatorname{clip}(\text{age}, 8, 22) - 14.0) / 4.0$, a youth hinge $\max(0.0, 13.0 - \text{age}) / 4.0$, and a binary missing-age indicator $\mathbb{I}[\text{age missing}]$.
  - **`tier2_gbm_age` (`BoundedHistogramGBM(include_age=True)`):** Fits residual depth-3 trees on top of `tier2_huber_pace_age` with `age_years` and learned missing-value split routing (`nan_left`).

---

## 4. Empirical Results & Pressure Testing

### 4.1 Overall Swimmer-Disjoint Holdout (`n = 25,855` Clean Pairs, `3,223` Swimmers)

| Model | MAE (s) | Median AE (s) | RMSE (s) | P90 AE (s) | Signed Bias (s) | MAPE (%) | Within ±0.5% | Within ±1.0% | Within ±2.0% | Swimmer-Eq MAE (s) | Macro-Cohort MAE (s) | Untrimmed MAE (s) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Colorado Timing (`colorado-2026`)** | `3.5329` | `2.19` | `6.0363` | `7.96` | `-0.0771` | `3.31%` | `9.86%` | `20.09%` | `39.11%` | `3.3180` | `4.5210` | `3.6174` |
| **NCAA (`ncaa-2025-27`)** | `2.9362` | `1.76` | `4.8518` | `6.77` | `+0.0035` | `2.87%` | `12.46%` | `24.39%` | `45.70%` | `2.8344` | `3.8525` | `3.0261` |
| **Quantile Equivalence** | `2.7199` | `1.64` | `4.5531` | `6.25` | `+0.0199` | `2.64%` | `13.60%` | `26.31%` | `49.20%` | `2.6426` | `3.7229` | `2.8089` |
| **Tier 1 Huber Pace-Curve (`turnmark-empirical-2026`)** | **`2.6658`** | **`1.61`** | **`4.4109`** | **`6.17`** | `-0.0886` | **`2.61%`** | `13.54%` | **`26.84%`** | **`50.21%`** | **`2.5755`** | **`3.4820`** | **`2.7530`** |
| **Tier 1 Residual GBM (`tier1_gbm_core`)** | `2.6648` | `1.60` | `4.4104` | `6.18` | `-0.0932` | `2.61%` | `13.54%` | `26.95%` | `50.21%` | `2.5742` | `3.4807` | `2.7519` |
| **Tier 2 Huber Pace + Age** | `2.6273` | `1.56` | `4.3948` | `6.04` | `-0.0770` | `2.57%` | `13.85%` | `27.28%` | `50.62%` | `2.5484` | `3.4658` | `2.7137` |
| **Tier 2 Residual GBM + Age (`tier2_gbm_age`)** | **`2.6252`** | **`1.57`** | **`4.3922`** | **`6.03`** | `-0.0831` | **`2.57%`** | **`14.07%`** | `27.22%` | **`50.62%`** | **`2.5458`** | **`3.4647`** | **`2.7116`** |

*Note: `Within ±0.5%`, `Within ±1.0%`, and `Within ±2.0%` measure the share of holdout predictions whose relative absolute error $|\hat{y} - y| / y$ falls within $0.5\%$, $1.0\%$, and $2.0\%$ of actual target time.*

> [!IMPORTANT]
> **Why Tier 1 Huber Pace-Curve (`turnmark-empirical-2026`) is the production engine model:**  
> Look at rows 4 and 5: boosting depth-3 regression trees on top of the quadratic Huber curve (`tier1_gbm_core`, `2.6648s` MAE) improves on the closed-form 3-coefficient quadratic spline (`tier1_huber_pace_core`, `2.6658s` MAE) by **one one-thousandth of a second (`0.0010s`)**. Once conditioned on `(direction, event, category)`, five numbers per cell (`[refSeconds, scaleSeconds, b0, b1, b2]`) capture virtually all of the learnable signal with exact input parity (`swim`, `to`, `table` — no age prompt required) and ship inside `crates/turnmark-core` as a **10.4 KB (`10,620`-byte)** static JSON table (`154` cells plus `8` pooled fallbacks).

### 4.2 Swimmer-Clustered Paired Bootstrap Significance ($B = 200$ Replicates)

Because multiple transitions from the same swimmer are correlated, standard i.i.d. error bars overstate significance. We resample **entire swimmer clusters** ($B = 200$ replicates across `3,223` test swimmers):

| Cohort | Pairs ($n$) | Swimmers | `turnmark-empirical-2026` $\Delta\text{MAE}$ vs. NCAA | 95% Clustered CI vs. NCAA | $z$-score vs. NCAA | $\Delta\text{MAE}$ vs. Colorado | $z$-score vs. Colorado |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **All Events (`overall_clean_test`)** | `25,855` | `3,223` | **`-0.2704s (-9.21%)`** | `[-0.3021s, -0.2338s]` | **`-15.57`** | **`-0.8671s (-24.54%)`** | **`-22.92`** |
| **Sprints (`50/100` all strokes)** | `17,846` | `3,015` | **`-0.1827s (-8.92%)`** | `[-0.2061s, -0.1573s]` | **`-15.20`** | **`-0.4089s (-17.98%)`** | **`-25.33`** |
| **Middle Distance (`200/400 Free, 200 BK/BR/IM`)** | `6,951` | `1,654` | **`-0.3906s (-8.75%)`** | `[-0.4700s, -0.3169s]` | **`-10.15`** | **`-1.6856s (-29.27%)`** | **`-17.97`** |
| **Specialty (`200 Fly & 400 IM`)** | `886` | `291` | **`-0.7204s (-12.77%)`** | `[-1.0415s, -0.3842s]` | **`-4.27`** | **`-2.4797s (-33.52%)`** | **`-10.02`** |
| **Distance Freestyle (`800/1000 & 1500/1650 Free`)** | `172` | `63` | **`-2.1963s (-11.33%)`** | `[-3.9198s, -0.3684s]` | **`-2.43`** | **`-7.0309s (-29.03%)`** | **`-3.86`** |

### 4.3 Event-by-Event Holdout Performance (All 14 Canonical Events, 30-Day Test Set)

`turnmark-empirical-2026` beats both NCAA and Colorado on **every single event** in the sport:

| Event Key | Yards ↔ Meters Mapping | Test Pairs ($n$) | Test Swimmers | NCAA MAE (Med AE) | NCAA Bias | Colorado MAE (Bias) | **Turnmark Empirical MAE (Med AE)** | **Empirical Bias** | **Tier 2 Age MAE** | **Gain vs. NCAA / Col** |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`50-FR`** | 50 yd ↔ 50 m Free | `5,278` | `1,897` | `1.13s` (`0.72s`) | `+0.03s` | `1.04s` (`-0.01s`) | **`1.03s` (`0.64s`)** | `-0.05s` | `1.03s` | **`-8.3% / -1.2%`** |
| **`100-FR`** | 100 yd ↔ 100 m Free | `4,607` | `1,695` | `2.12s` (`1.41s`) | `+0.02s` | `2.17s` (`-0.03s`) | **`2.04s` (`1.37s`)** | `-0.08s` | `2.02s` | **`-3.7% / -6.0%`** |
| **`200-FR`** | 200 yd ↔ 200 m Free | `2,292` | `908` | `4.01s` (`3.01s`) | `-0.03s` | `4.34s` (`-0.12s`) | **`3.75s` (`2.74s`)** | `-0.11s` | `3.65s` | **`-6.3% / -13.6%`** |
| **`400-FR`** | 500 yd ↔ 400 m Free | `958` | `378` | `7.06s` (`5.28s`) | `+0.21s` | `10.11s` (`+0.47s`) | **`6.24s` (`4.64s`)** | `-0.16s` | `6.22s` | **`-11.6% / -38.3%`** |
| **`800-FR`** | 1000 yd ↔ 800 m Free | `134` | `55` | `16.04s` (`9.71s`) | `+0.42s` | `17.59s` (`+0.64s`) | **`14.16s` (`9.06s`)** | `-0.31s` | `14.63s` | **`-11.7% / -19.5%`** |
| **`1500-FR`** | 1650 yd ↔ 1500 m Free | `38` | `16` | `31.20s` (`28.80s`) | `-0.28s` | `47.61s` (`+0.08s`) | **`27.88s` (`21.57s`)** | `-1.68s` | `29.67s` | **`-10.6% / -41.4%`** |
| **`100-BK`** | 100 yd ↔ 100 m Back | `2,939` | `1,103` | `2.70s` (`1.94s`) | `+0.11s` | `3.30s` (`-0.12s`) | **`2.29s` (`1.67s`)** | `-0.07s` | `2.23s` | **`-15.1% / -30.6%`** |
| **`200-BK`** | 200 yd ↔ 200 m Back | `811` | `320` | `3.76s` (`2.89s`) | `+0.03s` | `6.27s` (`-0.25s`) | **`3.55s` (`2.74s`)** | `-0.07s` | `3.53s` | **`-5.4% / -43.3%`** |
| **`100-BR`** | 100 yd ↔ 100 m Breast | `2,786` | `1,029` | `2.71s` (`2.10s`) | `-0.05s` | `3.27s` (`-0.12s`) | **`2.44s` (`1.84s`)** | `-0.09s` | `2.40s` | **`-9.8% / -25.2%`** |
| **`200-BR`** | 200 yd ↔ 200 m Breast | `824` | `325` | `4.94s` (`4.00s`) | `-0.23s` | `6.25s` (`-0.29s`) | **`3.90s` (`2.89s`)** | `+0.03s` | `3.80s` | **`-21.0% / -37.6%`** |
| **`100-FL`** | 100 yd ↔ 100 m Fly | `2,236` | `831` | `2.40s` (`1.72s`) | `-0.08s` | `2.81s` (`-0.11s`) | **`2.20s` (`1.55s`)** | `-0.13s` | `2.17s` | **`-8.7% / -21.9%`** |
| **`200-FL`** | 200 yd ↔ 200 m Fly | `488` | `185` | `4.61s` (`3.48s`) | `-0.20s` | `5.59s` (`-0.25s`) | **`3.98s` (`2.81s`)** | `-0.19s` | `3.85s` | **`-13.7% / -28.8%`** |
| **`200-IM`** | 200 yd ↔ 200 m IM | `2,066` | `802` | `3.86s` (`3.00s`) | `+0.01s` | `4.91s` (`-0.19s`) | **`3.70s` (`2.89s`)** | `-0.09s` | `3.62s` | **`-4.1% / -24.8%`** |
| **`400-IM`** | 400 yd ↔ 400 m IM | `398` | `161` | `6.90s` (`5.46s`) | `-0.29s` | `9.62s` (`-0.45s`) | **`6.07s` (`4.47s`)** | `-0.25s` | `5.97s` | **`-12.0% / -36.9%`** |

### 4.4 Featured Events Deep Dive: 800/1000 Free, 1500/1650 Free, 500/400 Free, 200 Fly, & 400 IM

Because distance events and 200 Fly / 400 IM are swum less frequently than 50/100 sprints, we also evaluate them on the **60-day swimmer-disjoint test set** (`n = 59,690` total test pairs), which more than doubles the held-out test sample size for those events:

| Featured Event | Window | Total Corpus Pairs | Disjoint Test Pairs ($n$) | NCAA MAE (s) | Colorado MAE (s) | **Turnmark Empirical MAE (s)** | **Tier 2 Age MAE (s)** | Empirical Gain vs. NCAA | Empirical Gain vs. Colorado |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`800-FR` (1000y ↔ 800m)** | `30d` | `978` | `134` | `16.04s` | `17.59s` | **`14.16s`** | `14.63s` | **`-1.88s (-11.7%)`** | **`-3.43s (-19.5%)`** |
| **`800-FR` (1000y ↔ 800m)** | `60d` | `2,222` | `350` | `16.66s` | `19.73s` | **`14.83s`** | `14.95s` | **`-1.83s (-11.0%)`** | **`-4.90s (-24.8%)`** |
| **`1500-FR` (1650y ↔ 1500m)** | `30d` | `288` | `38` | `31.20s` | `47.61s` | **`27.88s`** | `29.67s` | **`-3.32s (-10.6%)`** | **`-19.73s (-41.4%)`** |
| **`1500-FR` (1650y ↔ 1500m)** | `60d` | `875` | `120` | `27.84s` | `39.22s` | **`27.78s`** | `28.36s` | **`-0.06s (-0.2%)`** | **`-11.43s (-29.2%)`** |
| **`400-FR` (500y ↔ 400m)** | `30d` | `6,586` | `958` | `7.06s` | `10.11s` | **`6.24s`** | **`6.22s`** | **`-0.82s (-11.6%)`** | **`-3.87s (-38.3%)`** |
| **`400-FR` (500y ↔ 400m)** | `60d` | `15,806` | `2,293` | `8.68s` | `11.37s` | **`7.45s`** | **`7.26s`** | **`-1.22s (-14.1%)`** | **`-3.92s (-34.4%)`** |
| **`200-FL` (200y ↔ 200m Fly)** | `30d` | `2,797` | `488` | `4.61s` | `5.59s` | **`3.98s`** | **`3.85s`** | **`-0.63s (-13.7%)`** | **`-1.61s (-28.8%)`** |
| **`200-FL` (200y ↔ 200m Fly)** | `60d` | `6,310` | `1,059` | `5.64s` | `6.80s` | **`4.48s`** | **`4.37s`** | **`-1.16s (-20.6%)`** | **`-2.33s (-34.2%)`** |
| **`400-IM` (400y ↔ 400m IM)** | `30d` | `2,602` | `398` | `6.90s` | `9.62s` | **`6.07s`** | **`5.97s`** | **`-0.83s (-12.0%)`** | **`-3.54s (-36.9%)`** |
| **`400-IM` (400y ↔ 400m IM)** | `60d` | `6,394` | `952` | `8.41s` | `11.17s` | **`7.01s`** | **`6.85s`** | **`-1.40s (-16.6%)`** | **`-4.16s (-37.2%)`** |

### 4.5 Performance by Course Direction, Speed Quartile, and Age Band

#### By Course Transition Direction (30-Day Test Set)

| Direction | Test Pairs ($n$) | NCAA MAE (Bias) | Colorado MAE (Bias) | **Turnmark Empirical MAE (Bias)** | **Tier 2 Age MAE** |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **`SCY -> LCM`** | `11,885` | `3.120s` (`-0.410s`) | `3.672s` (`-2.561s`) | **`2.777s` (`-0.287s`)** | **`2.777s`** |
| **`LCM -> SCY`** | `11,889` | `2.789s` (`+0.410s`) | `3.406s` (`+2.383s`) | **`2.562s` (`+0.109s`)** | **`2.483s`** |
| **`LCM -> SCM`** | `686` | `2.600s` (`-0.658s`) | `2.730s` (`+0.919s`) | **`2.500s` (`+0.130s`)** | **`2.449s`** |
| **`SCM -> LCM`** | `686` | `2.695s` (`+0.679s`) | `2.730s` (`-0.919s`) | **`2.506s` (`-0.335s`)** | **`2.500s`** |
| **`SCY -> SCM`** | `355` | `3.051s` (`-0.687s`) | `5.175s` (`+1.388s`) | **`3.013s` (`-0.266s`)** | **`2.975s`** |
| **`SCM -> SCY`** | `354` | `2.730s` (`+0.874s`) | `4.609s` (`-1.058s`) | **`2.691s` (`+0.160s`)** | **`2.686s`** |

#### By Within-Event Speed Quartile (30-Day Test Set)

| Speed Quartile | NCAA MAE (s) | **NCAA Signed Bias (s)** | Colorado MAE (s) | Colorado Bias (s) | Quantile Equiv Bias (s) | **Turnmark Empirical MAE (s)** | **Empirical Signed Bias (s)** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`Q1` (Fastest 25%)** | `2.021s` | **`-0.554s`** | `2.720s` | `-0.596s` | `-0.503s` | **`1.786s`** | `-0.244s` |
| **`Q2` (25% – 50%)** | `2.472s` | `-0.116s` | `3.204s` | `-0.171s` | `-0.055s` | **`2.254s`** | **`-0.022s`** |
| **`Q3` (50% – 75%)** | `2.841s` | `+0.104s` | `3.450s` | `+0.019s` | `+0.114s` | **`2.625s`** | **`-0.034s`** |
| **`Q4` (Slowest 25%)** | `4.301s` | **`+0.587s`** | `4.430s` | `+0.434s` | `+0.535s` | **`3.901s`** | **`-0.048s`** |

#### By Age Band (30-Day Test Set)

| Age Band | NCAA MAE (Bias) | Colorado MAE | **Turnmark Empirical MAE (Bias)** | **Tier 2 Age MAE (Bias)** |
| :--- | ---: | ---: | ---: | ---: |
| **`10u`** | `3.414s` (`+0.134s`) | `3.223s` | **`3.091s`** (`-0.336s`) | **`3.032s` (`-0.045s`)** |
| **`11-12`** | `2.814s` (`+0.031s`) | `3.067s` | **`2.497s`** (`-0.218s`) | **`2.497s` (`-0.040s`)** |
| **`13-14`** | `2.931s` (`-0.014s`) | `3.726s` | **`2.731s`** (`-0.105s`) | **`2.704s` (`-0.134s`)** |
| **`15-16`** | `2.850s` (`-0.050s`) | `3.851s` | **`2.570s`** (`+0.071s`) | **`2.504s` (`-0.050s`)** |
| **`17-18`** | `2.706s` (`-0.082s`) | `3.735s` | **`2.437s`** (`+0.187s`) | **`2.385s` (`-0.101s`)** |
| **`19+`** | `2.066s` (`-0.019s`) | `2.602s` | **`1.941s`** (`+0.230s`) | `1.993s` (`-0.220s`) |

### 4.6 Facility Transitions, Out-of-Time Holdout, and Split-Conformal Intervals

#### Same-Facility vs. Cross-Facility & Altitude Transitions

Joining meets to `team-directory/catalog/facilities.csv` splits test transitions by whether both meet headers resolved to the **same `facility_id`** (`same_facility_transition`) vs. different `facility_id`s (`different_facility_transition`), and by whether either meet is in the **altitude cohort** (`altitude_meet_involved`: any Utah or Montana meet, meets in mountain-west states `CO`/`UT`/`WY`/`NM`/`ID`/`MT`/`NV`, Reno/Tahoe or Black Hills high-altitude cities/ZIP3 prefixes `577`/`894`/`895`/`897`/`898`/`961`, or meets with a declared `B1` altitude $\ge 3,000\text{ ft}$):

| Venue Cohort | Test Pairs ($n$) | Swimmers | NCAA MAE (Med AE) | Colorado MAE (Med AE) | **Turnmark Empirical MAE (Med AE)** | **Tier 2 Age MAE (Med AE)** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Same Facility (`same_facility_transition`)** | `5,925` | `946` | `2.5308s` (`1.55s`) | `3.3224s` (`2.21s`) | **`2.1942s` (`1.36s`)** | **`2.1695s` (`1.33s`)** |
| **Different Facility (`different_facility_transition`)** | `17,836` | `2,472` | `3.0796s` (`1.86s`) | `3.6022s` (`2.20s`) | **`2.8261s` (`1.71s`)** | **`2.7868s` (`1.67s`)** |
| **Sea-Level Both Meets (`sea_level_both_meets`)** | `24,568` | `3,090` | `2.8852s` (`1.74s`) | `3.4785s` (`2.18s`) | **`2.6134s` (`1.58s`)** | **`2.5763s` (`1.54s`)** |
| **Altitude Meet Involved (`altitude_meet_involved`)** | `1,287` | `166` | `3.9100s` (`2.27s`) | `4.5720s` (`2.47s`) | **`3.6674s` (`2.15s`)** | **`3.6005s` (`2.12s`)** |

#### Temporal (`2026`), Leave-Regions-Out, and Pairing-Window Holdouts

| Holdout Protocol | Evaluated Pairs ($n$) | Swimmers | NCAA MAE (s) | Colorado MAE (s) | **Turnmark Empirical MAE (s)** | **Tier 2 Age MAE (s)** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Out-of-Time Holdout (`2026` trained on `≤2025`)** | `26,328` | `5,056` | `3.0461s` | `3.4940s` | **`2.7803s (-8.73%)`** | **`2.7224s (-10.63%)`** |
| **Leave-Regions-Out (`SE + AD + SD + PV + MW` held out)** | `23,352` | `3,723` | `3.2219s` | `3.5598s` | **`3.0762s (-4.52%)`** | `3.0835s (-4.30%)` |
| **14-Day Pairing Window Sensitivity (`14d`)** | `12,990` | `1,990` | `2.6317s` | `3.2207s` | **`2.4014s (-8.75%)`** | **`2.3626s (-10.23%)`** |
| **30-Day Primary Pairing Window (`30d`)** | `25,855` | `3,223` | `2.9362s` | `3.5329s` | **`2.6658s (-9.21%)`** | **`2.6273s (-10.52%)`** |
| **60-Day Pairing Window Sensitivity (`60d`)** | `59,690` | `5,358` | `3.3388s` | `3.9532s` | **`2.9938s (-10.33%)`** | **`2.9438s (-11.83%)`** |

#### Split-Conformal Prediction Intervals (`turnmark-empirical-2026`)

Calibrated on the disjoint validation partition (`27,201` pairs) using normalized absolute residuals $|y - \hat{y}| / \max(1.0\text{s}, \hat{y})$ per `(direction, event_key)` cell, finite-sample split-conformal intervals achieve near-exact nominal coverage on the held-out test partition (`25,855` pairs):

| Event | Test Pairs ($n$) | **50% Interval Coverage** | **50% Median Half-Width** | **80% Interval Coverage** | **80% Median Half-Width** | **90% Interval Coverage** | **90% Median Half-Width** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **All Events (`overall`)** | `25,855` | **`50.37%`** | **`±1.70s`** | **`79.13%`** | **`±3.34s`** | **`89.64%`** | **`±4.62s`** |
| **`50-FR`** | `5,278` | `49.83%` | `±0.63s` | `79.25%` | `±1.31s` | `89.16%` | `±1.85s` |
| **`100-FR`** | `4,607` | `48.90%` | `±1.33s` | `78.68%` | `±2.69s` | `89.21%` | `±3.78s` |
| **`200-FR`** | `2,292` | `49.87%` | `±2.76s` | `78.71%` | `±5.50s` | `89.62%` | `±7.38s` |
| **`400-FR` (500y/400m)** | `958` | `58.66%` | `±5.45s` | `84.13%` | `±10.50s` | `90.81%` | `±14.41s` |
| **`800-FR` (1000y/800m)** | `134` | `50.00%` | `±9.33s` | `74.63%` | `±17.28s` | `79.85%` | `±21.72s` |
| **`1500-FR` (1650y/1500m)** | `38` | `50.00%` | `±19.22s` | `57.89%` | `±35.73s` | `78.95%` | `±43.88s` |
| **`100-BK`** | `2,939` | `50.22%` | `±1.67s` | `78.63%` | `±3.23s` | `89.52%` | `±4.38s` |
| **`200-BK`** | `811` | `48.83%` | `±2.64s` | `79.78%` | `±5.33s` | `92.60%` | `±7.39s` |
| **`100-BR`** | `2,786` | `51.79%` | `±1.90s` | `78.79%` | `±3.56s` | `89.88%` | `±4.87s` |
| **`200-BR`** | `824` | `53.28%` | `±3.16s` | `79.98%` | `±6.14s` | `89.44%` | `±8.33s` |
| **`100-FL`** | `2,236` | `49.15%` | `±1.51s` | `79.92%` | `±3.16s` | `90.92%` | `±4.49s` |
| **`200-FL`** | `488` | `52.05%` | `±2.94s` | `78.07%` | `±5.80s` | `84.84%` | `±7.42s` |
| **`200-IM`** | `2,066` | `50.92%` | `±2.92s` | `79.09%` | `±5.60s` | `90.56%` | `±7.64s` |
| **`400-IM`** | `398` | `47.99%` | `±4.23s` | `76.38%` | `±8.54s` | `89.95%` | `±12.29s` |

---

## 5. Production Integration in `turnmark-core`

Rather than deploying a server-side Python inference service, `evaluate_and_train.py --export-empirical-json data/empirical.json` exports the fitted Tier 1 Huber Pace-Curve snapshot (`154` five-number cell arrays `[refSeconds, scaleSeconds, b0, b1, b2]` plus `8` pooled `(direction, event)` fallback offsets and SHA-256 provenance metadata) directly into [`data/empirical.json`](../../data/empirical.json) (`10.4 KB` / `10,620` bytes).

1. **Rust Authoritative Core (`crates/turnmark-core`):**
   - `ConversionMethod::Empirical` (`"turnmark-empirical-2026"`) is embedded at compile time via `include_str!("../../../data/empirical.json")`.
   - Evaluates `empirical_offset(&event, distance, to, table, seconds)` in [`crates/turnmark-core/src/engine.rs`](../../crates/turnmark-core/src/engine.rs), rounds the offset to hundredths (`offset_seconds`), adds it to `seconds * factor`, and truncates to hundredths (`ConversionKind::Derived`).
   - Preserves Turnmark's altitude ordering contract: when pool elevation is supplied, the sea-level deduction (`usa-swimming-altitude-2026` or `ncaa-altitude-2026-27-d1`) is deducted from the original swim before evaluating the pace-curve conversion.
2. **Cross-Platform SDK & Consumers:**
   - **JavaScript / Wasm (`@turnmark/sdk`):** Exports `empiricalMethod = "turnmark-empirical-2026"`, `empiricalSource`, and includes `"Turnmark Empirical"` in `conversionMethods`.
   - **Web App (`src/`), Embed Widget (`apps/embed/`), Native iOS (`apps/ios/`), Native Android (`apps/android/`), and MCP (`packages/mcp/`):** Expose `"Turnmark Empirical"` in Calculation Options and compare all three methods side-by-side (`NCAA`, `Colorado Timing`, and `Turnmark Empirical`) with course/turn geometry, formula decomposition, and pace-sensitivity visualization while keeping `NCAA (default)` as the default rule.

---

## 6. Reproducibility Commands

```bash
# 1. Run research unit test suite (78 tests across pairing, shrinkage, monotonicity, conformal, and catalog)
python3 -m unittest discover -s research/conversion-model -v

# 2. Rebuild local meet-to-facility locality resolution join (requires local SDIF cache)
python3 research/conversion-model/local/build_meet_venue_join.py

# 3. Materialize & probe the hybrid SQLite + Parquet lakehouse
target/lakehouse-venv/bin/python research/conversion-model/lakehouse.py build \
  --input research/conversion-model/data/national-checkpoint-15/races.sqlite3 \
  --output target/lakehouse-national-15
target/lakehouse-venv/bin/python research/conversion-model/lakehouse.py probe \
  target/lakehouse-national-15

# 4. Train models, run holdout/bootstrap/conformal evaluations, and export data/empirical.json
target/lakehouse-venv/bin/python research/conversion-model/evaluate_and_train.py \
  --duckdb target/lakehouse-national-15/queries.duckdb \
  --input-label local-lakehouse-national-checkpoint-15 \
  --venues-csv research/conversion-model/data/national-checkpoint-15/meet_venues.csv \
  --output-dir research/conversion-model/data/national-checkpoint-15 \
  --public-summary research/conversion-model/evaluation-checkpoint-06.json \
  --export-empirical-json data/empirical.json
```
