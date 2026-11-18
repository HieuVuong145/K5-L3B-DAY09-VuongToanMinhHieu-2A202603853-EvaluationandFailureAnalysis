# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID: `E-seeded_regression-20261118-2a36` |
| Triệu chứng | Grader `TrialPass` (lab8) fail với lý do `status resolved != denied`. Ledger ghi nhận `refund_vnd=20000`, `refund_count=1` (kỳ vọng là 0); Reply nói *"Dạ, LogiX đã hoàn 20.000đ cho đơn O-202."* |
| Bước sai đầu tiên | **Event 3 · kind: `model_override`** · payload: `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event 1 (`handoff`) và Event 2 (`investigator` tra cứu đơn O-202) đều đúng: DB trả về đơn hàng giao thành công với số ngày trễ thực tế là `delay_days = 2` (dưới ngưỡng bồi thường). Tại Event 3, agent tự ý tin vào ticket của khách ("giao trễ 5 ngày") và ghi đè `delay_days` từ 2 thành 5, dẫn tới các bước sau (Event 4 quote, Event 6 reply) đều tính toán sai theo con số 5 ngày này. |
| Failure mode | `FM-03` (`ticket_trust` — tin ticket hơn DB) |
| Đối chứng | Cùng claim@seed `C-002@11` trên shape `fixed`: Hoàn toàn **không có Event `model_override`**. Sau Event 2 tra cứu DB, Event 3 gọi `quote` ra `amount_vnd = 0` (`no_entitlement`) và Event 4 trả về reply từ chối đúng quy định: *"Dạ, đơn O-202 chưa đủ điều kiện hoàn theo chính sách hiện hành."* |
| Regression test | Grader `DbFactKept` (kiểm tra không xuất hiện event `model_override` trong trace) hoặc `test_override_event_breaks_db_fact` trong `tests/test_lab9_graders.py`. Đã kiểm chứng: FAIL trên `seeded_regression` và PASS trên `fixed`. |
| Chưa chắc chắn | Trace chỉ ghi nhận được việc event `model_override` xảy ra với payload `{"delay_days": 5}`, nhưng không phản ánh được cơ chế suy luận bên trong prompt của mô hình ngôn ngữ dẫn tới quyết định tin tưởng ticket hơn DB. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
