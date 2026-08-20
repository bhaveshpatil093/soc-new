# Top-100 August Anomalies Report

*Generated on 2026-08-20T18:07:20.728365+00:00*

## [1] Timestamp: 2025-08-01T05:33:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 500 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [PCA (Evidence 1.00)]: recon_error: f_volume=0.0014, f_latency=0.0005, f_cpu=39.0768, f_mem=39.0738

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 500.00 | 10.00 | 50.00x |
| f_volume | 5000.00 | 47.95 | 104.27x |
| f_latency | 97.38 | 33.87 | 2.88x |
| f_cpu | 99.00 | 30.05 | 3.29x |
| f_mem | 43.51 | 45.10 | 0.96x |

---

## [2] Timestamp: 2025-08-01T05:33:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `charlie`, Host: `web-02`
- **Related Events:** 500 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Statistical, Autoencoder, LSTM
- **Top Features:** [PCA (Evidence 1.00)]: recon_error: f_volume=0.0012, f_latency=0.0004, f_cpu=34.2362, f_mem=34.2336

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 500.00 | 10.00 | 50.00x |
| f_volume | 5000.00 | 47.95 | 104.27x |
| f_latency | 131.05 | 33.87 | 3.87x |
| f_cpu | 99.00 | 30.05 | 3.29x |
| f_mem | 49.72 | 45.10 | 1.10x |

---

## [3] Timestamp: 2025-08-01T05:33:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `charlie`, Host: `web-02`
- **Related Events:** 500 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Statistical, Autoencoder, LSTM
- **Top Features:** [PCA (Evidence 1.00)]: recon_error: f_volume=0.0013, f_latency=0.0004, f_cpu=36.3747, f_mem=36.3720

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 500.00 | 10.00 | 50.00x |
| f_volume | 5000.00 | 47.95 | 104.27x |
| f_latency | 32.04 | 33.87 | 0.95x |
| f_cpu | 99.00 | 30.05 | 3.29x |
| f_mem | 46.88 | 45.10 | 1.04x |

---

## [4] Timestamp: 2025-08-01T05:23:55+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 70.32 | 47.95 | 1.47x |
| f_latency | 79.80 | 33.87 | 2.36x |
| f_cpu | 17.06 | 30.05 | 0.57x |
| f_mem | 22.30 | 45.10 | 0.49x |

---

## [5] Timestamp: 2025-08-01T04:28:05+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 80.27 | 47.95 | 1.67x |
| f_latency | 9.29 | 33.87 | 0.27x |
| f_cpu | 42.26 | 30.05 | 1.41x |
| f_mem | 60.57 | 45.10 | 1.34x |

---

## [6] Timestamp: 2025-08-01T01:40:00+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `bob`, Host: `web-02`
- **Related Events:** 10 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Statistical, Autoencoder, LSTM
- **Top Features:** [PCA (Evidence 1.00)]: recon_error: f_volume=0.0027, f_latency=0.0009, f_cpu=77.3745, f_mem=77.3687

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 10.00 | 10.00 | 1.00x |
| f_volume | 48.69 | 47.95 | 1.02x |
| f_latency | 92.26 | 33.87 | 2.72x |
| f_cpu | 95.00 | 30.05 | 3.16x |
| f_mem | 10.00 | 45.10 | 0.22x |

---

## [7] Timestamp: 2025-08-01T01:51:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 15 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 15.00 | 10.00 | 1.50x |
| f_volume | 83.78 | 47.95 | 1.75x |
| f_latency | 125.46 | 33.87 | 3.70x |
| f_cpu | 37.21 | 30.05 | 1.24x |
| f_mem | 51.51 | 45.10 | 1.14x |

---

## [8] Timestamp: 2025-08-01T00:41:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** statistical_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `charlie`, Host: `web-02`
- **Related Events:** 11 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Autoencoder, LSTM
- **Top Features:** [Statistical (Evidence 1.00)]: Driven by f_latency (Robust Z-Score: 209.02)

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 11.00 | 10.00 | 1.10x |
| f_volume | 45.64 | 47.95 | 0.95x |
| f_latency | 5000.00 | 33.87 | 147.64x |
| f_cpu | 31.05 | 30.05 | 1.03x |
| f_mem | 46.53 | 45.10 | 1.03x |

---

## [9] Timestamp: 2025-08-01T01:37:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 49.08 | 47.95 | 1.02x |
| f_latency | 202.53 | 33.87 | 5.98x |
| f_cpu | 31.01 | 30.05 | 1.03x |
| f_mem | 49.18 | 45.10 | 1.09x |

---

## [10] Timestamp: 2025-08-01T02:27:05+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 16 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 16.00 | 10.00 | 1.60x |
| f_volume | 91.22 | 47.95 | 1.90x |
| f_latency | 121.56 | 33.87 | 3.59x |
| f_cpu | 28.87 | 30.05 | 0.96x |
| f_mem | 39.17 | 45.10 | 0.87x |

---

## [11] Timestamp: 2025-08-01T02:29:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 26.68 | 47.95 | 0.56x |
| f_latency | 227.18 | 33.87 | 6.71x |
| f_cpu | 30.90 | 30.05 | 1.03x |
| f_mem | 44.78 | 45.10 | 0.99x |

---

## [12] Timestamp: 2025-08-01T01:20:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `db-01`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 57.46 | 47.95 | 1.20x |
| f_latency | 76.85 | 33.87 | 2.27x |
| f_cpu | 41.56 | 30.05 | 1.38x |
| f_mem | 59.93 | 45.10 | 1.33x |

---

## [13] Timestamp: 2025-08-01T04:28:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, PCA, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 63.76 | 47.95 | 1.33x |
| f_latency | 101.70 | 33.87 | 3.00x |
| f_cpu | 40.67 | 30.05 | 1.35x |
| f_mem | 56.97 | 45.10 | 1.26x |

---

## [14] Timestamp: 2025-08-01T03:32:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 18 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 18.00 | 10.00 | 1.80x |
| f_volume | 106.98 | 47.95 | 2.23x |
| f_latency | 11.07 | 33.87 | 0.33x |
| f_cpu | 17.90 | 30.05 | 0.60x |
| f_mem | 27.51 | 45.10 | 0.61x |

---

## [15] Timestamp: 2025-08-01T02:17:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `charlie`, Host: `web-02`
- **Related Events:** 5 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Autoencoder, LSTM
- **Top Features:** [IForest (Evidence 1.00)]: Explanation deferred.

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 5.00 | 10.00 | 0.50x |
| f_volume | 31.53 | 47.95 | 0.66x |
| f_latency | 225.83 | 33.87 | 6.67x |
| f_cpu | 16.55 | 30.05 | 0.55x |
| f_mem | 22.23 | 45.10 | 0.49x |

---

## [16] Timestamp: 2025-08-01T05:49:55+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 2 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** PCA, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 2.00 | 10.00 | 0.20x |
| f_volume | 7.68 | 47.95 | 0.16x |
| f_latency | 5.14 | 33.87 | 0.15x |
| f_cpu | 30.98 | 30.05 | 1.03x |
| f_mem | 52.50 | 45.10 | 1.16x |

---

## [17] Timestamp: 2025-08-01T02:54:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 15 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** PCA, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 15.00 | 10.00 | 1.50x |
| f_volume | 95.64 | 47.95 | 1.99x |
| f_latency | 18.96 | 33.87 | 0.56x |
| f_cpu | 30.57 | 30.05 | 1.02x |
| f_mem | 49.89 | 45.10 | 1.11x |

---

## [18] Timestamp: 2025-08-01T05:37:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `david`, Host: `web-01`
- **Related Events:** 18 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Autoencoder, LSTM
- **Top Features:** [IForest (Evidence 1.00)]: Explanation deferred.

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 18.00 | 10.00 | 1.80x |
| f_volume | 116.04 | 47.95 | 2.42x |
| f_latency | 193.80 | 33.87 | 5.72x |
| f_cpu | 20.51 | 30.05 | 0.68x |
| f_mem | 28.85 | 45.10 | 0.64x |

---

## [19] Timestamp: 2025-08-01T04:05:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `db-01`
- **Related Events:** 17 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 17.00 | 10.00 | 1.70x |
| f_volume | 110.74 | 47.95 | 2.31x |
| f_latency | 1.11 | 33.87 | 0.03x |
| f_cpu | 24.19 | 30.05 | 0.81x |
| f_mem | 36.94 | 45.10 | 0.82x |

---

## [20] Timestamp: 2025-08-01T01:10:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 10 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 10.00 | 10.00 | 1.00x |
| f_volume | 77.15 | 47.95 | 1.61x |
| f_latency | 137.30 | 33.87 | 4.05x |
| f_cpu | 33.73 | 30.05 | 1.12x |
| f_mem | 53.25 | 45.10 | 1.18x |

---

## [21] Timestamp: 2025-08-01T05:45:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 10 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity, Autoencoder
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 10.00 | 10.00 | 1.00x |
| f_volume | 61.87 | 47.95 | 1.29x |
| f_latency | 179.10 | 33.87 | 5.29x |
| f_cpu | 26.95 | 30.05 | 0.90x |
| f_mem | 42.18 | 45.10 | 0.94x |

---

## [22] Timestamp: 2025-08-01T01:31:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 40.86 | 47.95 | 0.85x |
| f_latency | 191.61 | 33.87 | 5.66x |
| f_cpu | 23.45 | 30.05 | 0.78x |
| f_mem | 36.08 | 45.10 | 0.80x |

---

## [23] Timestamp: 2025-08-01T03:16:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 17 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 17.00 | 10.00 | 1.70x |
| f_volume | 100.99 | 47.95 | 2.11x |
| f_latency | 8.06 | 33.87 | 0.24x |
| f_cpu | 28.89 | 30.05 | 0.96x |
| f_mem | 41.11 | 45.10 | 0.91x |

---

## [24] Timestamp: 2025-08-01T03:36:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 81.00 | 47.95 | 1.69x |
| f_latency | 114.30 | 33.87 | 3.38x |
| f_cpu | 35.89 | 30.05 | 1.19x |
| f_mem | 51.60 | 45.10 | 1.14x |

---

## [25] Timestamp: 2025-08-01T04:19:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 7 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** PCA, Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 7.00 | 10.00 | 0.70x |
| f_volume | 34.44 | 47.95 | 0.72x |
| f_latency | 137.84 | 33.87 | 4.07x |
| f_cpu | 29.39 | 30.05 | 0.98x |
| f_mem | 39.57 | 45.10 | 0.88x |

---

## [26] Timestamp: 2025-08-01T00:29:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 17 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 17.00 | 10.00 | 1.70x |
| f_volume | 77.99 | 47.95 | 1.63x |
| f_latency | 34.01 | 33.87 | 1.00x |
| f_cpu | 10.72 | 30.05 | 0.36x |
| f_mem | 14.45 | 45.10 | 0.32x |

---

## [27] Timestamp: 2025-08-01T02:17:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 18 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 18.00 | 10.00 | 1.80x |
| f_volume | 88.58 | 47.95 | 1.85x |
| f_latency | 9.37 | 33.87 | 0.28x |
| f_cpu | 34.65 | 30.05 | 1.15x |
| f_mem | 54.62 | 45.10 | 1.21x |

---

## [28] Timestamp: 2025-08-01T02:07:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `db-01`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 51.72 | 47.95 | 1.08x |
| f_latency | 156.95 | 33.87 | 4.63x |
| f_cpu | 38.03 | 30.05 | 1.27x |
| f_mem | 58.55 | 45.10 | 1.30x |

---

## [29] Timestamp: 2025-08-01T03:49:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 53.92 | 47.95 | 1.12x |
| f_latency | 292.39 | 33.87 | 8.63x |
| f_cpu | 24.31 | 30.05 | 0.81x |
| f_mem | 36.58 | 45.10 | 0.81x |

---

## [30] Timestamp: 2025-08-01T06:01:05+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 51.08 | 47.95 | 1.07x |
| f_latency | 335.97 | 33.87 | 9.92x |
| f_cpu | 27.35 | 30.05 | 0.91x |
| f_mem | 41.22 | 45.10 | 0.91x |

---

## [31] Timestamp: 2025-08-01T05:04:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** PCA, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 46.76 | 47.95 | 0.98x |
| f_latency | 67.17 | 33.87 | 1.98x |
| f_cpu | 37.04 | 30.05 | 1.23x |
| f_mem | 59.97 | 45.10 | 1.33x |

---

## [32] Timestamp: 2025-08-01T04:17:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `charlie`, Host: `db-01`
- **Related Events:** 19 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [IForest (Evidence 1.00)]: Explanation deferred.

### Novel Relationships
- User: charlie | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 19.00 | 10.00 | 1.90x |
| f_volume | 96.10 | 47.95 | 2.00x |
| f_latency | 325.96 | 33.87 | 9.63x |
| f_cpu | 21.28 | 30.05 | 0.71x |
| f_mem | 31.27 | 45.10 | 0.69x |

---

## [33] Timestamp: 2025-08-01T03:50:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 7 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 7.00 | 10.00 | 0.70x |
| f_volume | 34.20 | 47.95 | 0.71x |
| f_latency | 109.60 | 33.87 | 3.24x |
| f_cpu | 38.16 | 30.05 | 1.27x |
| f_mem | 59.28 | 45.10 | 1.31x |

---

## [34] Timestamp: 2025-08-01T00:32:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 16 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 16.00 | 10.00 | 1.60x |
| f_volume | 94.06 | 47.95 | 1.96x |
| f_latency | 61.85 | 33.87 | 1.83x |
| f_cpu | 30.93 | 30.05 | 1.03x |
| f_mem | 48.62 | 45.10 | 1.08x |

---

## [35] Timestamp: 2025-08-01T05:50:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 65.79 | 47.95 | 1.37x |
| f_latency | 109.51 | 33.87 | 3.23x |
| f_cpu | 38.51 | 30.05 | 1.28x |
| f_mem | 56.40 | 45.10 | 1.25x |

---

## [36] Timestamp: 2025-08-01T00:41:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 42.71 | 47.95 | 0.89x |
| f_latency | 114.92 | 33.87 | 3.39x |
| f_cpu | 41.96 | 30.05 | 1.40x |
| f_mem | 63.09 | 45.10 | 1.40x |

---

## [37] Timestamp: 2025-08-01T03:52:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 11 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 11.00 | 10.00 | 1.10x |
| f_volume | 48.57 | 47.95 | 1.01x |
| f_latency | 183.92 | 33.87 | 5.43x |
| f_cpu | 29.22 | 30.05 | 0.97x |
| f_mem | 44.95 | 45.10 | 1.00x |

---

## [38] Timestamp: 2025-08-01T04:39:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 11 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 11.00 | 10.00 | 1.10x |
| f_volume | 57.99 | 47.95 | 1.21x |
| f_latency | 28.60 | 33.87 | 0.84x |
| f_cpu | 21.02 | 30.05 | 0.70x |
| f_mem | 29.29 | 45.10 | 0.65x |

---

## [39] Timestamp: 2025-08-01T06:29:55+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 32.50 | 47.95 | 0.68x |
| f_latency | 152.61 | 33.87 | 4.51x |
| f_cpu | 35.82 | 30.05 | 1.19x |
| f_mem | 55.05 | 45.10 | 1.22x |

---

## [40] Timestamp: 2025-08-01T01:21:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 83.49 | 47.95 | 1.74x |
| f_latency | 162.06 | 33.87 | 4.79x |
| f_cpu | 32.08 | 30.05 | 1.07x |
| f_mem | 47.51 | 45.10 | 1.05x |

---

## [41] Timestamp: 2025-08-01T06:31:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `db-01`
- **Related Events:** 11 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 11.00 | 10.00 | 1.10x |
| f_volume | 51.25 | 47.95 | 1.07x |
| f_latency | 133.66 | 33.87 | 3.95x |
| f_cpu | 36.19 | 30.05 | 1.20x |
| f_mem | 52.45 | 45.10 | 1.16x |

---

## [42] Timestamp: 2025-08-01T01:01:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 18 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 18.00 | 10.00 | 1.80x |
| f_volume | 90.98 | 47.95 | 1.90x |
| f_latency | 100.41 | 33.87 | 2.96x |
| f_cpu | 35.54 | 30.05 | 1.18x |
| f_mem | 52.40 | 45.10 | 1.16x |

---

## [43] Timestamp: 2025-08-01T06:51:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `db-01`
- **Related Events:** 4 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 4.00 | 10.00 | 0.40x |
| f_volume | 12.34 | 47.95 | 0.26x |
| f_latency | 1.50 | 33.87 | 0.04x |
| f_cpu | 33.49 | 30.05 | 1.11x |
| f_mem | 52.62 | 45.10 | 1.17x |

---

## [44] Timestamp: 2025-08-01T06:48:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 52.43 | 47.95 | 1.09x |
| f_latency | 46.50 | 33.87 | 1.37x |
| f_cpu | 20.48 | 30.05 | 0.68x |
| f_mem | 32.54 | 45.10 | 0.72x |

---

## [45] Timestamp: 2025-08-01T05:51:55+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 3 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 3.00 | 10.00 | 0.30x |
| f_volume | 16.52 | 47.95 | 0.34x |
| f_latency | 12.67 | 33.87 | 0.37x |
| f_cpu | 38.32 | 30.05 | 1.28x |
| f_mem | 56.48 | 45.10 | 1.25x |

---

## [46] Timestamp: 2025-08-01T02:15:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 37.06 | 47.95 | 0.77x |
| f_latency | 183.18 | 33.87 | 5.41x |
| f_cpu | 34.65 | 30.05 | 1.15x |
| f_mem | 52.86 | 45.10 | 1.17x |

---

## [47] Timestamp: 2025-08-01T01:08:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 89.12 | 47.95 | 1.86x |
| f_latency | 103.31 | 33.87 | 3.05x |
| f_cpu | 30.87 | 30.05 | 1.03x |
| f_mem | 44.54 | 45.10 | 0.99x |

---

## [48] Timestamp: 2025-08-01T06:11:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 36.51 | 47.95 | 0.76x |
| f_latency | 222.19 | 33.87 | 6.56x |
| f_cpu | 31.54 | 30.05 | 1.05x |
| f_mem | 47.49 | 45.10 | 1.05x |

---

## [49] Timestamp: 2025-08-01T03:46:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 81.06 | 47.95 | 1.69x |
| f_latency | 8.01 | 33.87 | 0.24x |
| f_cpu | 21.37 | 30.05 | 0.71x |
| f_mem | 32.58 | 45.10 | 0.72x |

---

## [50] Timestamp: 2025-08-01T05:42:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 3 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 3.00 | 10.00 | 0.30x |
| f_volume | 15.02 | 47.95 | 0.31x |
| f_latency | 60.66 | 33.87 | 1.79x |
| f_cpu | 26.18 | 30.05 | 0.87x |
| f_mem | 36.84 | 45.10 | 0.82x |

---

## [51] Timestamp: 2025-08-01T05:10:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 11 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 11.00 | 10.00 | 1.10x |
| f_volume | 46.34 | 47.95 | 0.97x |
| f_latency | 171.58 | 33.87 | 5.07x |
| f_cpu | 27.46 | 30.05 | 0.91x |
| f_mem | 42.05 | 45.10 | 0.93x |

---

## [52] Timestamp: 2025-08-01T01:22:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 31.12 | 47.95 | 0.65x |
| f_latency | 46.66 | 33.87 | 1.38x |
| f_cpu | 22.08 | 30.05 | 0.73x |
| f_mem | 31.15 | 45.10 | 0.69x |

---

## [53] Timestamp: 2025-08-01T04:32:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 41.38 | 47.95 | 0.86x |
| f_latency | 154.50 | 33.87 | 4.56x |
| f_cpu | 31.61 | 30.05 | 1.05x |
| f_mem | 49.14 | 45.10 | 1.09x |

---

## [54] Timestamp: 2025-08-01T02:24:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 42.04 | 47.95 | 0.88x |
| f_latency | 14.22 | 33.87 | 0.42x |
| f_cpu | 39.68 | 30.05 | 1.32x |
| f_mem | 61.05 | 45.10 | 1.35x |

---

## [55] Timestamp: 2025-08-01T04:31:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 93.49 | 47.95 | 1.95x |
| f_latency | 71.57 | 33.87 | 2.11x |
| f_cpu | 23.63 | 30.05 | 0.79x |
| f_mem | 34.58 | 45.10 | 0.77x |

---

## [56] Timestamp: 2025-08-01T05:24:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Statistical, Rarity, Autoencoder, LSTM
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 51.00 | 47.95 | 1.06x |
| f_latency | 159.17 | 33.87 | 4.70x |
| f_cpu | 38.33 | 30.05 | 1.28x |
| f_mem | 57.97 | 45.10 | 1.29x |

---

## [57] Timestamp: 2025-08-01T01:05:00+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** IForest, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 88.55 | 47.95 | 1.85x |
| f_latency | 92.80 | 33.87 | 2.74x |
| f_cpu | 25.16 | 30.05 | 0.84x |
| f_mem | 38.27 | 45.10 | 0.85x |

---

## [58] Timestamp: 2025-08-01T02:39:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 3 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 3.00 | 10.00 | 0.30x |
| f_volume | 12.66 | 47.95 | 0.26x |
| f_latency | 18.61 | 33.87 | 0.55x |
| f_cpu | 31.23 | 30.05 | 1.04x |
| f_mem | 49.68 | 45.10 | 1.10x |

---

## [59] Timestamp: 2025-08-01T03:04:55+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 5 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 5.00 | 10.00 | 0.50x |
| f_volume | 27.21 | 47.95 | 0.57x |
| f_latency | 5.54 | 33.87 | 0.16x |
| f_cpu | 21.19 | 30.05 | 0.71x |
| f_mem | 32.37 | 45.10 | 0.72x |

---

## [60] Timestamp: 2025-08-01T00:03:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 15 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 15.00 | 10.00 | 1.50x |
| f_volume | 87.82 | 47.95 | 1.83x |
| f_latency | 68.35 | 33.87 | 2.02x |
| f_cpu | 34.09 | 30.05 | 1.13x |
| f_mem | 52.73 | 45.10 | 1.17x |

---

## [61] Timestamp: 2025-08-01T02:17:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 3 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 3.00 | 10.00 | 0.30x |
| f_volume | 11.62 | 47.95 | 0.24x |
| f_latency | 30.56 | 33.87 | 0.90x |
| f_cpu | 27.94 | 30.05 | 0.93x |
| f_mem | 39.78 | 45.10 | 0.88x |

---

## [62] Timestamp: 2025-08-01T06:28:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 42.98 | 47.95 | 0.90x |
| f_latency | 29.52 | 33.87 | 0.87x |
| f_cpu | 38.97 | 30.05 | 1.30x |
| f_mem | 56.70 | 45.10 | 1.26x |

---

## [63] Timestamp: 2025-08-01T06:38:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 16.38 | 47.95 | 0.34x |
| f_latency | 103.75 | 33.87 | 3.06x |
| f_cpu | 30.04 | 30.05 | 1.00x |
| f_mem | 43.44 | 45.10 | 0.96x |

---

## [64] Timestamp: 2025-08-01T00:07:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 47.59 | 47.95 | 0.99x |
| f_latency | 45.60 | 33.87 | 1.35x |
| f_cpu | 20.35 | 30.05 | 0.68x |
| f_mem | 30.83 | 45.10 | 0.68x |

---

## [65] Timestamp: 2025-08-01T01:22:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 6 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 6.00 | 10.00 | 0.60x |
| f_volume | 27.28 | 47.95 | 0.57x |
| f_latency | 51.88 | 33.87 | 1.53x |
| f_cpu | 24.18 | 30.05 | 0.80x |
| f_mem | 33.69 | 45.10 | 0.75x |

---

## [66] Timestamp: 2025-08-01T00:29:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 5 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 5.00 | 10.00 | 0.50x |
| f_volume | 26.68 | 47.95 | 0.56x |
| f_latency | 4.30 | 33.87 | 0.13x |
| f_cpu | 25.09 | 30.05 | 0.84x |
| f_mem | 34.72 | 45.10 | 0.77x |

---

## [67] Timestamp: 2025-08-01T02:45:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 16 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 16.00 | 10.00 | 1.60x |
| f_volume | 91.85 | 47.95 | 1.92x |
| f_latency | 54.86 | 33.87 | 1.62x |
| f_cpu | 25.01 | 30.05 | 0.83x |
| f_mem | 37.56 | 45.10 | 0.83x |

---

## [68] Timestamp: 2025-08-01T02:07:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 68.30 | 47.95 | 1.42x |
| f_latency | 38.60 | 33.87 | 1.14x |
| f_cpu | 36.12 | 30.05 | 1.20x |
| f_mem | 57.21 | 45.10 | 1.27x |

---

## [69] Timestamp: 2025-08-01T05:05:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 54.92 | 47.95 | 1.15x |
| f_latency | 9.80 | 33.87 | 0.29x |
| f_cpu | 22.51 | 30.05 | 0.75x |
| f_mem | 31.96 | 45.10 | 0.71x |

---

## [70] Timestamp: 2025-08-01T05:48:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Statistical, Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 51.94 | 47.95 | 1.08x |
| f_latency | 141.51 | 33.87 | 4.18x |
| f_cpu | 31.90 | 30.05 | 1.06x |
| f_mem | 49.26 | 45.10 | 1.09x |

---

## [71] Timestamp: 2025-08-01T05:26:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 59.29 | 47.95 | 1.24x |
| f_latency | 52.68 | 33.87 | 1.56x |
| f_cpu | 22.33 | 30.05 | 0.74x |
| f_mem | 31.96 | 45.10 | 0.71x |

---

## [72] Timestamp: 2025-08-01T05:45:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 72.21 | 47.95 | 1.51x |
| f_latency | 13.18 | 33.87 | 0.39x |
| f_cpu | 36.78 | 30.05 | 1.22x |
| f_mem | 52.74 | 45.10 | 1.17x |

---

## [73] Timestamp: 2025-08-01T00:02:05+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 13 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 78.59 | 47.95 | 1.64x |
| f_latency | 10.88 | 33.87 | 0.32x |
| f_cpu | 23.44 | 30.05 | 0.78x |
| f_mem | 35.72 | 45.10 | 0.79x |

---

## [74] Timestamp: 2025-08-01T03:54:15+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 10 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 10.00 | 10.00 | 1.00x |
| f_volume | 42.32 | 47.95 | 0.88x |
| f_latency | 9.57 | 33.87 | 0.28x |
| f_cpu | 38.01 | 30.05 | 1.26x |
| f_mem | 55.08 | 45.10 | 1.22x |

---

## [75] Timestamp: 2025-08-01T03:24:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 6 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 6.00 | 10.00 | 0.60x |
| f_volume | 32.98 | 47.95 | 0.69x |
| f_latency | 51.41 | 33.87 | 1.52x |
| f_cpu | 38.51 | 30.05 | 1.28x |
| f_mem | 58.88 | 45.10 | 1.31x |

---

## [76] Timestamp: 2025-08-01T04:26:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 6 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 6.00 | 10.00 | 0.60x |
| f_volume | 22.41 | 47.95 | 0.47x |
| f_latency | 24.59 | 33.87 | 0.73x |
| f_cpu | 24.49 | 30.05 | 0.82x |
| f_mem | 38.72 | 45.10 | 0.86x |

---

## [77] Timestamp: 2025-08-01T00:56:50+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 38.53 | 47.95 | 0.80x |
| f_latency | 33.42 | 33.87 | 0.99x |
| f_cpu | 38.57 | 30.05 | 1.28x |
| f_mem | 59.10 | 45.10 | 1.31x |

---

## [78] Timestamp: 2025-08-01T06:30:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 15 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 15.00 | 10.00 | 1.50x |
| f_volume | 84.76 | 47.95 | 1.77x |
| f_latency | 47.26 | 33.87 | 1.40x |
| f_cpu | 26.43 | 30.05 | 0.88x |
| f_mem | 40.75 | 45.10 | 0.90x |

---

## [79] Timestamp: 2025-08-01T00:27:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 6 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 6.00 | 10.00 | 0.60x |
| f_volume | 18.46 | 47.95 | 0.38x |
| f_latency | 37.74 | 33.87 | 1.11x |
| f_cpu | 27.16 | 30.05 | 0.90x |
| f_mem | 38.45 | 45.10 | 0.85x |

---

## [80] Timestamp: 2025-08-01T03:15:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 75.71 | 47.95 | 1.58x |
| f_latency | 10.06 | 33.87 | 0.30x |
| f_cpu | 23.74 | 30.05 | 0.79x |
| f_mem | 34.13 | 45.10 | 0.76x |

---

## [81] Timestamp: 2025-08-01T02:42:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 57.63 | 47.95 | 1.20x |
| f_latency | 1.26 | 33.87 | 0.04x |
| f_cpu | 38.24 | 30.05 | 1.27x |
| f_mem | 58.42 | 45.10 | 1.30x |

---

## [82] Timestamp: 2025-08-01T05:50:05+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 20.05 | 47.95 | 0.42x |
| f_latency | 9.97 | 33.87 | 0.29x |
| f_cpu | 34.23 | 30.05 | 1.14x |
| f_mem | 52.99 | 45.10 | 1.17x |

---

## [83] Timestamp: 2025-08-01T05:53:00+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** behavioural_anomaly
- **Duration:** 5s
- **Affected Entities:** User: `bob`, Host: `web-02`
- **Related Events:** 13 events
- **Model-Only Candidate:** True
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** PCA
- **Top Features:** [PCA (Evidence 1.00)]: recon_error: f_volume=0.0000, f_latency=0.0000, f_cpu=0.2611, f_mem=0.2610

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 13.00 | 10.00 | 1.30x |
| f_volume | 56.91 | 47.95 | 1.19x |
| f_latency | 18.48 | 33.87 | 0.55x |
| f_cpu | 21.27 | 30.05 | 0.71x |
| f_mem | 39.28 | 45.10 | 0.87x |

---

## [84] Timestamp: 2025-08-01T02:37:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 8 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 8.00 | 10.00 | 0.80x |
| f_volume | 23.83 | 47.95 | 0.50x |
| f_latency | 115.57 | 33.87 | 3.41x |
| f_cpu | 27.89 | 30.05 | 0.93x |
| f_mem | 41.22 | 45.10 | 0.91x |

---

## [85] Timestamp: 2025-08-01T03:22:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 7 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 7.00 | 10.00 | 0.70x |
| f_volume | 32.88 | 47.95 | 0.69x |
| f_latency | 97.16 | 33.87 | 2.87x |
| f_cpu | 24.41 | 30.05 | 0.81x |
| f_mem | 37.55 | 45.10 | 0.83x |

---

## [86] Timestamp: 2025-08-01T01:19:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 48.14 | 47.95 | 1.00x |
| f_latency | 24.24 | 33.87 | 0.72x |
| f_cpu | 21.07 | 30.05 | 0.70x |
| f_mem | 30.94 | 45.10 | 0.69x |

---

## [87] Timestamp: 2025-08-01T00:22:25+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 6 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 6.00 | 10.00 | 0.60x |
| f_volume | 20.84 | 47.95 | 0.43x |
| f_latency | 47.26 | 33.87 | 1.40x |
| f_cpu | 34.91 | 30.05 | 1.16x |
| f_mem | 50.84 | 45.10 | 1.13x |

---

## [88] Timestamp: 2025-08-01T05:53:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 11 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 11.00 | 10.00 | 1.10x |
| f_volume | 75.12 | 47.95 | 1.57x |
| f_latency | 13.46 | 33.87 | 0.40x |
| f_cpu | 26.51 | 30.05 | 0.88x |
| f_mem | 36.84 | 45.10 | 0.82x |

---

## [89] Timestamp: 2025-08-01T00:17:35+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 7 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 7.00 | 10.00 | 0.70x |
| f_volume | 32.40 | 47.95 | 0.68x |
| f_latency | 31.54 | 33.87 | 0.93x |
| f_cpu | 38.52 | 30.05 | 1.28x |
| f_mem | 57.85 | 45.10 | 1.28x |

---

## [90] Timestamp: 2025-08-01T02:43:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 36.72 | 47.95 | 0.77x |
| f_latency | 112.51 | 33.87 | 3.32x |
| f_cpu | 32.17 | 30.05 | 1.07x |
| f_mem | 50.41 | 45.10 | 1.12x |

---

## [91] Timestamp: 2025-08-01T06:41:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 60.17 | 47.95 | 1.25x |
| f_latency | 50.15 | 33.87 | 1.48x |
| f_cpu | 37.44 | 30.05 | 1.25x |
| f_mem | 53.60 | 45.10 | 1.19x |

---

## [92] Timestamp: 2025-08-01T06:10:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 73.21 | 47.95 | 1.53x |
| f_latency | 56.31 | 33.87 | 1.66x |
| f_cpu | 24.29 | 30.05 | 0.81x |
| f_mem | 34.51 | 45.10 | 0.77x |

---

## [93] Timestamp: 2025-08-01T03:11:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 16 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 16.00 | 10.00 | 1.60x |
| f_volume | 54.64 | 47.95 | 1.14x |
| f_latency | 46.81 | 33.87 | 1.38x |
| f_cpu | 22.38 | 30.05 | 0.74x |
| f_mem | 34.61 | 45.10 | 0.77x |

---

## [94] Timestamp: 2025-08-01T06:21:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `db-01`
- **Related Events:** 14 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: db-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 14.00 | 10.00 | 1.40x |
| f_volume | 78.81 | 47.95 | 1.64x |
| f_latency | 47.57 | 33.87 | 1.40x |
| f_cpu | 30.45 | 30.05 | 1.01x |
| f_mem | 42.53 | 45.10 | 0.94x |

---

## [95] Timestamp: 2025-08-01T01:41:40+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 12 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 12.00 | 10.00 | 1.20x |
| f_volume | 37.73 | 47.95 | 0.79x |
| f_latency | 101.03 | 33.87 | 2.98x |
| f_cpu | 28.98 | 30.05 | 0.96x |
| f_mem | 40.53 | 45.10 | 0.90x |

---

## [96] Timestamp: 2025-08-01T01:24:45+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-02`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-02

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 37.77 | 47.95 | 0.79x |
| f_latency | 20.28 | 33.87 | 0.60x |
| f_cpu | 35.52 | 30.05 | 1.18x |
| f_mem | 55.77 | 45.10 | 1.24x |

---

## [97] Timestamp: 2025-08-01T01:31:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 7 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 7.00 | 10.00 | 0.70x |
| f_volume | 26.05 | 47.95 | 0.54x |
| f_latency | 28.76 | 33.87 | 0.85x |
| f_cpu | 25.46 | 30.05 | 0.85x |
| f_mem | 36.14 | 45.10 | 0.80x |

---

## [98] Timestamp: 2025-08-01T05:09:10+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 7 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 7.00 | 10.00 | 0.70x |
| f_volume | 34.89 | 47.95 | 0.73x |
| f_latency | 44.44 | 33.87 | 1.31x |
| f_cpu | 23.85 | 30.05 | 0.79x |
| f_mem | 34.19 | 45.10 | 0.76x |

---

## [99] Timestamp: 2025-08-01T03:57:20+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 9 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 9.00 | 10.00 | 0.90x |
| f_volume | 39.72 | 47.95 | 0.83x |
| f_latency | 107.67 | 33.87 | 3.18x |
| f_cpu | 24.98 | 30.05 | 0.83x |
| f_mem | 36.80 | 45.10 | 0.82x |

---

## [100] Timestamp: 2025-08-01T01:05:30+00:00
- **Ensemble Evidence:** 1.0000
- **Category:** novel_relationship
- **Duration:** 5s
- **Affected Entities:** User: `eve`, Host: `web-01`
- **Related Events:** 10 events
- **Model-Only Candidate:** False
- **Analyst Status:** Pending

### Detection Profile
- **Detectors Agreed:** Rarity
- **Top Features:** [Rarity (Evidence 1.00)]: Driven by user='eve' [RARE (Surprisal: 3.00)]

### Novel Relationships
- User: eve | Host: web-01

### July Baseline Comparison
| Feature | Value | July Median | Ratio |
|---------|-------|-------------|-------|
| event_count | 10.00 | 10.00 | 1.00x |
| f_volume | 37.30 | 47.95 | 0.78x |
| f_latency | 23.00 | 33.87 | 0.68x |
| f_cpu | 37.81 | 30.05 | 1.26x |
| f_mem | 56.51 | 45.10 | 1.25x |

---

