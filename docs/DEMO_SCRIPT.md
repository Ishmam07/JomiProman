# 90-second demo script

Reset first so deed numbers match: `make reset-demo`. Use a phone-width browser window only if you show QR scanning. Record at 1080p, one take per scene, then trim.

| Time | On screen | Say (Bangla or English) |
|---|---|---|
| 0:00 | Home page, hero sketch | "জাল দলিল আর একই জমি দুইবার বিক্রি, এই দুটোই জমির মামলার বড় কারণ। জমি প্রমাণ এটা আগেই ধরে ফেলে।" |
| 0:10 | **Register**: করিম → রফিক, 6 → *Try to register* | "সাব-রেজিস্ট্রার দলিল তুললেন। সব যাচাই পাস, দলিল হ্যাশ-শিকলে যুক্ত, ডিজিটাল সই হলো, QR কোড তৈরি।" (show QR, deed **D-0003**) |
| 0:28 | Change buyer to সালমা, area **7** → *Try to register* | "একই বিক্রেতা আরও ৭ শতাংশ বিক্রি করতে চাইলেন। তার হাতে আছে মাত্র ৪। সিস্টেম লাল সংকেত দিয়ে দলিল আটকে দিল।" (red banner, AI explanation) |
| 0:45 | **Verify → paper copy**: *Load correct values*, verify (green); change the buyer name, verify again | "কাগজের কপিতে কেউ ক্রেতার নাম বদলালে ফলাফল লাল। ঠিক কোন তথ্য বদলেছে সেটাও দেখা যায়।" (red + changed-fields table) |
| 1:05 | **Check before you buy**: রহিমপুর / ৪১২ | "ক্রেতা টাকা দেওয়ার আগে দেখলেন: কার হাতে কত জমি, ইতিহাস, আটকানো দলিল।" Ask the chat: "এই জমি কেনা কি নিরাপদ?" |
| 1:20 | Click `শ্যামপুর / ৫৫` (khas) or `রহিমপুর / ৪১৩` (bank lien) | "খাস জমি, ব্যাংক বন্ধক বা মামলা থাকলেও একই ভাবে ধরা পড়ে। ফলাফল নির্ধারিত নিয়মে, AI শুধু সহজ ভাষায় ব্যাখ্যা দেয়।" |
| 1:28 | Home | "জমি প্রমাণ: যাচাইযোগ্য, স্বচ্ছ, সারা দেশে ব্যবহারযোগ্য।" |

## Optional extra (if you have time, not for the 90 s video)
Show the database refusing to rewrite history:
```bash
docker compose exec mysql mysql -ujomi -pjomi_pass jomiproman \
  -e "UPDATE deeds SET buyer='X' WHERE deed_no='D-0001'"
```
Expected: `ERROR 1644 (45000): Ledger is append-only: signed deed records cannot be changed or deleted`.

## Checklist before recording
- `docker compose ps` shows all four services healthy.
- `GROQ_API_KEY` set if you want the badge to read "AI · llama-3.3-70b-versatile" (otherwise it reads "স্বয়ংক্রিয় ব্যাখ্যা", which is fine).
- Browser zoom 110–125 % so the text is readable in the video.
