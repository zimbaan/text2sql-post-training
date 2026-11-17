| Run | Execution acc. | vs base | SQL errors | group / order | join | nested / set ops | single table |
|---|---|---|---|---|---|---|---|
| Base model (no training) | **45.5%** |  | 37.6% | 56.9% | 30.5% | 25.8% | 62.5% |
| SFT, 25% of data | **56.0%** | +10.5 pts | 26.0% | 69.2% | 37.5% | 38.4% | 74.5% |
| SFT, full SFT split | **58.3%** | +12.9 pts | 21.1% | 65.9% | 42.3% | 46.5% | 75.1% |
| SFT, SFT split + DPO questions (control) | **59.4%** | +13.9 pts | 20.7% | 70.6% | 43.8% | 46.5% | 73.9% |
| SFT + DPO (execution-verified pairs) | **61.3%** | +15.9 pts | 16.5% | 67.3% | 48.6% | 47.2% | 76.9% |

Spider dev, 1034 questions (group / order: 211, join: 331, nested / set ops: 159, single table: 333).
