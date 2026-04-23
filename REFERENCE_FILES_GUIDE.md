# REFERENCE FILES GUIDE

## 1. Purpose of This Guide
هذا الملف هو دليل ملاحة مرجعي سريع يوضح أهم ملفات المشروع، وظيفة كل ملف، ومتى يجب الرجوع إليه.

## 2. Primary Reference Files
| الاسم | المسار | النوع | الغرض | متى نرجع له | الجمهور |
|---|---|---|---|---|---|
| `README.md` | `README.md` | تشغيل/استخدام | نقطة البداية: تعريف النظام، أوامر التشغيل، أوضاع البناء، وملفات المخرجات | عند بدء العمل على المشروع أو تشغيله لأول مرة | المطور الجديد + المستخدم |
| `FUNCTIONAL_OPERATION_OVERVIEW.md` | `FUNCTIONAL_OPERATION_OVERVIEW.md` | توثيق وظيفي | شرح التشغيل العملي من إدخال JSON حتى إخراج PDF عبر GUI/CLI | عند الحاجة لفهم سير العمل الوظيفي بسرعة | المطور الجديد + المستخدم |
| `CODEBASE_ANALYSIS.md` | `CODEBASE_ANALYSIS.md` | تحليل الكود | تحليل شامل للطبقات، المسارات التشغيلية، ونقاط الربط بين المكونات | عند فهم أعمق للكود قبل التعديل أو التتبع | المطور |
| `SYSTEM_OVERVIEW.md` | `SYSTEM_OVERVIEW.md` | معمارية | **غير موجود حاليًا في المستودع** | لا يمكن الرجوع إليه حاليًا (إلا إذا أضيف لاحقًا) | — |
| `project schema` | `schema/project.schema.json` | عقدة بيانات | العقد الرسمي لبنية JSON (الحقول، القيود، الأنواع) | عند تفسير أخطاء schema أو التحقق من صحة شكل البيانات | المطور |
| `sample project` | `examples/sample_project.json` | مثال/مدخل | مثال مشروع كامل صالح للاختبار والتجربة | عند تجربة النظام بسرعة أو فهم شكل الإدخال الواقعي | المطور الجديد + المستخدم |
| `Typst entry template` | `templates/main.typ` | قالب | نقطة دخول Typst الثابتة التي تضمّن المحتوى المولّد | عند تتبع ربط `generated_content.typ` بالقالب النهائي | المطور |
| `Typst macros` | `templates/macros.typ` | قالب | تعريف ماكروز العرض (العناوين، الفقرات، الكود، الجداول، الصور) | عند تتبع سلوك التنسيق والإخراج البصري | المطور |

## 3. Recommended Reading Order
1. `README.md`
2. `FUNCTIONAL_OPERATION_OVERVIEW.md`
3. `CODEBASE_ANALYSIS.md`
4. `schema/project.schema.json`
5. `examples/sample_project.json`
6. `templates/main.typ`
7. `templates/macros.typ`
8. `build/build_report.json` (عند تحليل نتيجة بناء فعلية)

> ملاحظة: `SYSTEM_OVERVIEW.md` غير موجود حاليًا، لذا ليس ضمن التسلسل الفعلي.

## 4. Reference Categories
- **تشغيل واستخدام**
  - `README.md`
- **فهم وظيفي**
  - `FUNCTIONAL_OPERATION_OVERVIEW.md`
- **فهم معماري**
  - `SYSTEM_OVERVIEW.md` (غير متوفر حاليًا)
- **تحليل الكود**
  - `CODEBASE_ANALYSIS.md`
- **عقدة البيانات**
  - `schema/project.schema.json`
- **قوالب الإخراج**
  - `templates/main.typ`
  - `templates/macros.typ`
- **أمثلة ومدخلات**
  - `examples/sample_project.json`
- **ملفات ناتجة Generated**
  - `build/generated_content.typ`
  - `build/output.pdf`
  - `build/build.log`
  - `build/build_report.json`
  - `build/_ui_snapshot.json` (ملف وسيط للحالة غير المحفوظة من GUI)

## 5. If You Need X, Read Y
- إذا أردت تشغيل النظام بسرعة → ابدأ بـ `README.md`.
- إذا أردت فهم الـworkflow الوظيفي من البداية للنهاية → `FUNCTIONAL_OPERATION_OVERVIEW.md`.
- إذا أردت فهم العلاقات بين الطبقات ومسارات التنفيذ → `CODEBASE_ANALYSIS.md`.
- إذا أردت فهم شكل JSON الصحيح وما هو إلزامي → `schema/project.schema.json`.
- إذا أردت مثال مشروع جاهز للاختبار → `examples/sample_project.json`.
- إذا أردت فهم كيف يتحول المحتوى إلى Typst → `templates/main.typ` ثم `templates/macros.typ`.
- إذا أردت فهم سبب فشل build معين → `build/build_report.json` ثم `build/build.log`.
- إذا أردت معرفة أين تعدّل سلوك Block معين في الكود → `src/models/blocks.py` ثم `src/generator/block_renderer.py` ثم `src/ui/forms/block_forms.py`.
- إذا أردت فهم تمثيل inline content مثل `ltr` و`inline_math` → `src/models/inlines.py` ثم `src/generator/inline_renderer.py`.

## 6. Source vs Reference vs Generated
- **Reference (Documentation/Analysis)**  
  `README.md`، `FUNCTIONAL_OPERATION_OVERVIEW.md`، `CODEBASE_ANALYSIS.md`، و`SYSTEM_OVERVIEW.md` (غير موجود حاليًا).
- **Source (تشغيلي/تعريفي)**  
  `src/`، `schema/project.schema.json`، `templates/main.typ`، `templates/macros.typ`، `examples/sample_project.json`.
- **Generated (ناتج تشغيل/بناء)**  
  كل ما داخل `build/` مثل `generated_content.typ` و`output.pdf` و`build_report.json`.

## 7. Minimal Starter Pack
للمهندس الجديد، الحد الأدنى المقترح للفهم السريع:
1. `README.md`
2. `FUNCTIONAL_OPERATION_OVERVIEW.md`
3. `schema/project.schema.json`
4. `examples/sample_project.json`
5. `templates/main.typ` + `templates/macros.typ`

## 8. Final Practical Note
هذا الملف دليل تنقّل مرجعي؛ ويُستخدم لتحديد أين تقرأ أولًا، وليس بديلًا عن قراءة الملفات المرجعية نفسها.
