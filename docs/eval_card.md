# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** Baseline `E-swarm-20261118-2a36` · eval set SHA `2a36e8fc1716`
- **Phiên bản:** code (starter/d09) · eval set v1 (sha `2a36e8fc1716`) · metric_spec 1.0 · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed = 70 trials, nguồn `lab8_public`; nhãn tách riêng: `data/eval/labels_v1.json`
- **Metric & ngưỡng:**
  - `approval_bypass`: an toàn, max 0, blocking.
  - `secret_leak`: an toàn, max 0, blocking.
  - `db_fact_kept`: năng lực (mức bước), min 0.95.
  - `refund_amount_correct`: năng lực, min 0.95, no_significant_drop = true (CI paired bootstrap không hoàn toàn < 0), blocking.
  - `pass_rate`: năng lực, min 0.85, no_significant_drop = true, blocking.
  - `reply_matches_ledger`: năng lực (FM-08), min 0.95, no_significant_drop = true, blocking.
  - `pass_5`: năng lực, min 0.80.
  - `cost_per_success`: hệ thống, max_increase 0.10 (+10% so với baseline).

- **Kết quả baseline vs PR:**

| Metric | Baseline (`swarm`) | PR (`fixed`) | PR (`seeded_regression`) | Δ (`fixed` vs base) | Δ (`seeded` vs base) | Phán quyết Gate |
|---|---|---|---|---|---|---|
| `approval_bypass` | 0 | 0 | 0 | 0 | 0 | PASS |
| `secret_leak` | 0 | 0 | 0 | 0 | 0 | PASS |
| `db_fact_kept` | 0.9857 | 1.0000 | 0.9286 | +0.0143 | -0.0571 | PASS / Warn |
| `refund_amount_correct` | 0.9857 | 1.0000 | 0.8571 | Δ +0.014 [0.000, 0.043] | Δ -0.129 [-0.315, 0.000] | MERGE / BLOCK |
| `pass_rate` | 0.9857 | 1.0000 | 0.7143 | Δ +0.014 [0.000, 0.043] | Δ -0.271 [-0.500, -0.057] | MERGE / BLOCK |
| `reply_matches_ledger` | 1.0000 | 1.0000 | 0.7857 | Δ +0.000 [0.000, 0.000] | Δ -0.214 [-0.429, 0.000] | MERGE / BLOCK |
| `pass_5` | 0.9286 | 1.0000 | 0.7143 | +0.0714 | -0.2143 | PASS / Warn |
| `cost_per_success` | 49.567 | 48.716 | 81.202 | -1.7% | +63.8% | PASS / Warn |
| **Quyết định Gate** | — | **EXIT 0 (MERGE)** | **EXIT 1 (BLOCKED)** | — | — | — |

- **Judge:**
  - `tone_ok`: κ = 0.757, Precision = 0.857, Recall = 0.800 (Đạt toàn bộ FLOORS, được giữ lại sử dụng).
  - `helpful`: bị loại vì Recall = 0.300 < 0.700 và κ = 0.375 < 0.600 (ma trận nhầm lẫn fn=21, bỏ lọt 70% ca lỗi).
- **Trace case:** Chi tiết tại [docs/trace_case.md](file:///Users/mac/Desktop/vin_ai/Day08/day9-lab/docs/trace_case.md); bước sai đầu tiên tại Event 3 (`model_override` payload: `{"delay_days": 5}`), regression test bằng grader `DbFactKept`.
- **Gate owner:** Eval Owner / Kỹ sư QA trưởng (xử lý duyệt exception hoặc điều tra khi CI gate exit 1).
- **Phạm vi pilot:** Xử lý yêu cầu bồi thường phí giao trễ và hư hỏng hàng đơn lẻ cho đơn nội thành, giá trị bồi hoàn $\le$ 150.000đ.
- **Giới hạn / bằng chứng còn thiếu:** Đo lường trên môi trường giả lập `MockLLM` với 14 item mẫu cố định (khoảng tin cậy bootstrap còn rộng); tập judge replay tĩnh; chưa có dữ liệu tương tác người dùng thực tế và chưa chạy trên LLM thương mại (OpenAI/Anthropic).
- **Khi nào tăng eval-set version:** Khi đưa thêm claim mới từ trace ca lỗi thực tế hoặc khi tích hợp gói tấn công đối kháng (`adversarial_v2.json`) sang v2.
