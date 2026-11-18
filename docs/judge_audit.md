# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Đạt (0.757 ≥ 0.6, 0.857 ≥ 0.8, 0.800 ≥ 0.7) | Dùng |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không đạt (κ=0.375 < 0.6, Recall=0.300 < 0.7) | Loại |

## Toàn bộ 10 case audit thủ công (toàn bộ các ca bất đồng của judge_tone)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & Hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | Reply: *"Em đã hoàn tiền cho anh rồi nha, anh check giúp em."* Xưng hô "anh/em" và từ đệm "nha" mang tính chất gia đình, suồng sã. **Hành động:** Bổ sung rule cấm đại từ xưng hô thân mật cá nhân và từ ngữ thiếu tính chuyên nghiệp B2C. |
| 2 | H-017 | PASS | FAIL | Người | Reply: *"Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha."* Từ "bạn ơi", "nha" không đạt chuẩn CSKH trang trọng. **Hành động:** Thêm checklist cấm các từ gọi đệm suồng sã ("bạn ơi", "nha"). |
| 3 | H-029 | PASS | FAIL | Người | Reply: *"Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm."* Câu "không cần nhắn thêm" mang sắc thái cộc cằn, xua đuổi khách hàng. Judge bị lừa bởi từ "Dạ, vui lòng". **Hành động:** Sửa prompt judge để phạt nặng thái độ tiêu cực/gắt gỏng dù có kính ngữ mở đầu. |
| 4 | H-042 | FAIL | PASS | Người | Reply: *"Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ."* Câu trả lời rất chuẩn mực, lịch sự và rõ ràng thời gian. Judge phạt quá máy móc. **Hành động:** Nới lỏng rubric judge, cho phép cung cấp mốc thời gian hoàn tiền dự kiến. |
| 5 | H-051 | FAIL | PASS | Người | Reply: *"Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ."* Judge phạt vì dùng từ tiếng Anh "refund". Người coi đây là từ mượn thông dụng trong TMĐT. **Hành động:** Cập nhật rubric cho phép một số thuật ngữ TMĐT thông dụng như "refund", "ship". |
| 6 | H-063 | PASS | FAIL | Người | Reply: *"Dạ, LogiX đã hoàn 20.000đ và sẽ hoàn thêm cho anh/chị ạ."* Tự ý hứa hẹn ngoài thẩm quyền ("sẽ hoàn thêm"), gây rủi ro cam kết sai quy trình. Judge bỏ qua vì thấy câu văn lịch sự. **Hành động:** Thêm tiêu chí cấm đưa ra cam kết/hứa hẹn tài chính chưa được duyệt. |
| 7 | H-070 | PASS | FAIL | Người | Reply: *"Dạ, LogiX đã hoàn 90.000đ cho đơn O-909 ạ 😂😂"* Dùng emoji cợt nhả (😂😂) trong văn bản xử lý khiếu nại tài chính là thiếu nghiêm túc. Judge không nhận diện được ngữ cảnh của emoji. **Hành động:** Bổ sung rule cấm emoji không phù hợp/cợt nhả trong kênh CSKH. |
| 8 | H-081 | FAIL | PASS | Người | Reply: *"Dạ, đơn O-107 chưa đủ điều kiện hoàn theo chính sách hiện hành ạ."* Câu từ chối mẫu mực, lịch sự, đúng chuẩn CSKH. Judge phạt vì nhầm việc từ chối là thái độ không tốt. **Hành động:** Làm rõ trong rubric rằng việc từ chối lịch sự, đúng chính sách không bị tính là lỗi tone. |
| 9 | H-088 | FAIL | PASS | Người | Reply: *"Dạ, dạ, LogiX đã hoàn 40.000đ cho đơn O-233 ạ."* Judge phạt vì lặp từ "Dạ, dạ". Người đánh giá đây là khẩu ngữ thể hiện sự dạ vâng lễ phép, không phải lỗi nặng. **Hành động:** Hướng dẫn judge không phạt lỗi lặp từ kính ngữ nhẹ mang tính tôn trọng. |
| 10 | H-094 | PASS | FAIL | Người | Reply: *"Da, LogiX da hoan 40.000đ cho don O-341, xin loi vi su bat tien."* Viết tiếng Việt không dấu, vi phạm quy chuẩn giao tiếp chính thức. Judge hiểu được nghĩa nên bỏ qua. **Hành động:** Thêm quy định bắt buộc gõ tiếng Việt có dấu chuẩn chính tả. |

## Kết luận
- **Tiêu chí bị loại:** `helpful` bị loại vì ma trận nhầm lẫn cho thấy `fn=21, tp=9` (bỏ lọt tới 21/30 ca lỗi, Recall chỉ đạt 0.300 so với sàn 0.700; κ chỉ đạt 0.375 so với sàn 0.600). Judge này bị đánh lừa bởi những câu xin lỗi lịch sự hoặc thông báo chung chung nhưng không giải quyết thực tế vấn đề của khách hàng. Không thể dùng `helpful` làm gate vì sẽ để lọt rất nhiều câu trả lời vô dụng.
- **Tiêu chí giữ lại:** `tone_ok` vượt qua toàn bộ các ngưỡng FLOORS (κ=0.757, P=0.857, R=0.800), đủ điều kiện đưa vào theo dõi chất lượng.
- **Rủi ro còn lại:** Dữ liệu hiệu chuẩn mới chỉ dựa trên tập replay công khai 100 dòng (`data/eval/judge_tone_public.csv`). Cần thu thập dữ liệu hội thoại thực tế của người dùng mới để tạo tập kiểm thử held-out thực sự, tránh trường hợp rubric bị overfit vào tập 100 câu mẫu này.
