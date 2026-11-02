# Analytics Engineering Internship Reflection
## Customer 360 & Multi-Touch Marketing Attribution Platform
**Intern Name**: Sujal Verma 
**Track**: Data Analytics & Analytics Engineering  
**Evaluation Period**: October 2026 – November 2026  
**Outcome Goal**: Full-Time Conversion (Analytics Engineer / Marketing Data Scientist)

---

### 1. Executive Summary & Project Ownership
During this project, my mandate was not simply to assemble a set of SQL queries or build another basic dashboard. My goal was to **own an end-to-end enterprise data product** that solves one of the most painful, expensive challenges in digital commerce: **the attribution blindspot and customer fragmentation caused by cookie deprecation.**

I owned the platform architecture from ingestion to executive presentation:
1. **Data Ingestion & Synthesis**: Engineered a high-fidelity synthetic data generator that replicates Google BigQuery's `ga4_obfuscated_sample_ecommerce` event streams, combined with multi-device user journeys, transactional CRM backends, and ad spend tables across Google, Meta, and TikTok.
2. **Graph-Based Identity Resolution**: Implemented a Disjoint Set Union (DSU) connected components algorithm in Python and designed its equivalent in native BigQuery recursive SQL CTEs to resolve anonymous cookies (`user_pseudo_id`), hashed emails, and authenticated CRM IDs into canonical customer clusters.
3. **dbt Warehouse Modeling**: Architected a production dbt project adhering to Medallion principles (Staging views, Intermediate graph and session models, and materialized Gold business marts for Customer 360 and Attribution).
4. **Attribution Modeling Engine**: Implemented and quantitatively evaluated 5 attribution models (First Touch, Last Touch, Linear, 7-day Time-Decay, and U-Shaped Position-Based), establishing mathematical invariants to guarantee 100% revenue conservation.
5. **Customer 360 & Predictive CLV**: Developed an automated RFM quintile scoring engine and projected 12-month forward CLV incorporating retention probabilities.
6. **Algorithmic Budget Optimization**: Formulated a diminishing marginal returns optimizer (Hill/Power-Law curve) to prescribe the exact dollar reallocation needed to unlock +$58,843 in projected net revenue lift without increasing overall ad spend.
7. **Production Visualizations**: Developed an interactive Streamlit BI platform and generated Tableau data sources, calculated fields, and executive dashboard blueprints.
8. **Engineering Quality Assurance**: Authored 13 automated unit tests with 100% pass rate, coupled with 5 custom dbt data quality assertions.

---

### 2. Key Technical Learnings

#### A. Identity Resolution is a Graph Problem, Not a SQL Join
Prior to this project, I viewed identity resolution as simple `LEFT JOIN ... ON email` queries. Building this system taught me that modern customer identity is inherently a **graph connectivity problem**:
- User A visits on an iPhone cookie ($C_1$).
- User A browses on a Mac cookie ($C_2$).
- User A enters their email ($E_1$) on the Mac.
- User A completes an order with customer ID ($U_1$) on the iPhone.
A simple relational join fails because $C_1$ never directly co-occurred with $E_1$ in the same row. By modeling cookies, emails, and CRM IDs as nodes and session co-occurrences as edges in an undirected graph, connected components algorithms transitively resolve all four identifiers into one canonical customer ID. Learning to implement Disjoint Set Union with near-constant time complexity $O(\alpha(N))$ and writing recursive SQL CTEs in BigQuery deepened my algorithmic thinking in data engineering.

#### B. The Law of Revenue Conservation in Attribution Modeling
In multi-touch attribution, fractional credit allocation introduces subtle floating-point discrepancies. A common failure in commercial attribution tools is that the sum of attributed channel revenue does not equal the actual bank ledger:
$$\sum_{i=1}^M \text{Attributed Revenue}_{i} \neq \text{Total Order Revenue}$$
To solve this, I enforced that attribution weights for every order must strictly normalize to $1.0$:
$$w_{\text{norm}, i} = \frac{w_i}{\sum_{j=1}^N w_j}$$
I built custom dbt assertions (`assert_attribution_revenue_conserved.sql`) that verify down to the cent that total order revenue ($760,082.10) is conserved across 1,900 orders. This gave our executive stakeholders unshakeable confidence in the numbers.

#### C. BigQuery GA4 Schema Nuances & SQL Substring Traps
Working with GA4 data revealed critical real-world data traps:
- In Google Analytics 4, parameters (`ga_session_id`, `utm_campaign`, `value`) are stored in nested `RECORD` arrays of key-value structs, requiring unnesting and surrogate key generation.
- During local testing, I diagnosed a subtle bug where `campaign LIKE '%brand%'` accidentally matched `nonbrand_category_intent`, incorrectly funneling Generic Search traffic into Brand Search. Catching this bug reinforced the importance of writing defensive data transformations and rigorous automated unit tests.

---

### 3. Business Impact: Unmasking the "Last-Touch Trap"

The most rewarding aspect of this project was discovering the profound divergence between legacy analytics and true multi-touch attribution:

1. **The Last-Touch Distortion**:
   - Under GA4 default Last-Touch Attribution, **TikTok Ads** showed an ROAS of **0.82x** (reported loss of $5,267) and a Customer Acquisition Cost of **$434.75**.
   - **Meta Prospecting** showed an ROAS of **0.57x** and a CAC of **$797.45**.
   - If our leadership followed legacy reports, they would have cancelled both campaigns.
2. **The Multi-Touch Reality**:
   - Under First-Touch Attribution, TikTok generated **$168,679** in discovery revenue at a **5.71x ROAS**.
   - Under Time-Decay Attribution, TikTok delivered **$87,932** in revenue at a **2.97x ROAS** with a true CPA of **$131.83**.
   - Meanwhile, Brand Search and Meta Retargeting's inflated ROAS figures (12.2x and 7.1x) were revealed to be capturing customers already acquired by top-of-funnel discovery.
3. **The Dollar Solution**:
   - Rather than giving descriptive commentary, I provided our CMO with an optimization model that shifts **$8,799** from saturated Meta Prospecting ad sets and reallocates into high-yield Brand Search, TikTok scale-up, and automated email flows, unlocking **+$58,843 in projected net revenue lift (+11.0%)** on the exact same budget.

---

### 4. Challenges Faced & Solutions Implemented

| Challenge | Root Cause | Solution Implemented |
|---|---|---|
| **Cross-Device Fragmentation** | Users switch from mobile Safari to desktop Chrome; cookies don't persist across devices. | Built Disjoint Set Union identity graph linking device cookies with SHA-256 hashed emails and CRM IDs. Identified that **55.4% of converted customers were multi-device users**. |
| **Flawed Campaign Matching** | Substring query `LIKE '%brand%'` matched `nonbrand_category_intent`. | Refactored dbt and Python logic to explicitly enforce `LIKE '%brand%' AND NOT LIKE '%nonbrand%'`. Added automated assertions. |
| **Attribution Revenue Drift** | Fractional weight rounding causing sum of channel revenue to deviate from order totals. | Implemented per-order weight normalization and added a custom dbt mathematical invariant test with tolerance $< \$0.05$. |
| **Ad Saturation Modeling** | Naive linear budget scaling assumes infinite ROAS at higher spend levels. | Formulated a power-law response curve ($R = \alpha \cdot S^{0.75}$) to model realistic diminishing marginal returns and cap budget increases within operational bounds. |

---

### 5. Why I Am Ready for a Full-Time Role
This project represents how I approach engineering and data science:
- **I don't wait for specifications; I define them**: When given the brief to analyze attribution, I expanded the scope to include automated graph identity resolution, RFM predictive CLV modeling, and mathematical budget optimization.
- **I test defensively**: I delivered 13 automated unit tests with 100% pass rate, ensuring no edge case (such as single-touchpoint journeys or zero-spend organic channels) could break production.
- **I translate technical depth into executive action**: Rather than presenting raw SQL or model metrics, I created an interactive BI dashboard and a 10-minute presentation deck answering the exact question executive leadership cares about: *"Where should we move our next dollar of marketing budget to maximize profit?"*

I am eager to bring this level of ownership, quantitative rigor, and business passion to a full-time role on the data team.
