# FUNCTIONAL OPERATION OVERVIEW

## 1. Purpose
نظام SDRE هو نظام تحويل مستندات يعتمد على JSON كمصدر رسمي للبيانات، ثم يمرّرها عبر مراحل تحقق (Validation) وتوليد Typst وبناء PDF، مع واجهة GUI تدعم التحرير اليدوي أو الاستيراد المباشر من JSON.

## 2. Main User Workflow
- تشغيل التطبيق عبر `python app.py`.
- إنشاء مشروع جديد أو فتح ملف مشروع JSON موجود.
- اختيار أسلوب العمل:
  - تعديل يدوي عبر النماذج (Forms).
  - أو لصق/تحميل JSON داخل تبويب `JSON Import` ثم `Validate JSON` ثم `Import JSON`.
- تنفيذ `Validate` للتأكد من سلامة البيانات.
- تنفيذ `Generate Typst Only` عند الحاجة لتوليد ملف Typst فقط.
- تنفيذ `Build Preview` أو `Build Strict` لبناء PDF.
- فتح النتائج من الواجهة: `Open Generated Typst` أو `Open Preview PDF` أو `Open Build Report` أو `Open Output Folder`.

## 3. Supported Working Modes
- **manual editing workflow**: تعديل `Subjects` و`Blocks` وحقول المحتوى مباشرة من الواجهة.
- **JSON-first workflow**: لصق/تحميل JSON ثم التحقق والاستيراد إلى الحالة الداخلية، ثم متابعة التحرير اختياريًا.
- **preview build**: بناء مرن قدر الإمكان؛ يحاول الاستمرار إذا أمكن.
- **strict build**: بناء صارم يتوقف عند أول أخطاء تحقق/توليد/قوالب.

## 4. Functional Input Model
- ملف `project JSON` بصيغة `ProjectFile` (الجذر يحتوي `project`).
- تعديلات المستخدم اليدوية داخل GUI (مثل العناوين، الفقرات، الجداول، الصور، placeholders).
- إعدادات المشروع عبر `Project Settings` (Meta + Theme).
- محتوى `blocks` و`inline content` مثل `paragraph`, `code_block`, `image`, `image_placeholder`, `ltr`, `inline_math`.

## 5. Validation Flow
- عند الضغط على `Validate`، يتم فحص حالة المشروع الحالية (من الملف أو من الحالة الداخلية).
- الفحص وظيفيًا يشمل:
  - صحة JSON (تحميل/Parsing).
  - التوافق مع `schema/project.schema.json`.
  - التحقق النموذجي (Model validation) عبر Pydantic.
- يفشل التحقق عند أخطاء الصياغة أو مخالفة Schema أو مخالفة قيود النماذج.
- النتيجة تظهر في الـLog/Status كـ `ok` أو `failed` مع `stage` وتفاصيل الأخطاء (`path`, `message`, `hint`، وخط/عمود عند أخطاء parsing).

## 6. Generation Flow
- عند `Generate Typst Only`:
  - يتم التحقق أولًا من صحة البيانات.
  - يُولَّد الملف `build/generated_content.typ`.
- هذا الملف هو المحتوى المولّد من بيانات المشروع.
- الملف `templates/main.typ` يقوم بتحميل القوالب من `templates/macros.typ` ثم تضمين `generated_content.typ`.

## 7. PDF Build Flow
- عند `Build Preview` أو `Build Strict`:
  - تحميل بيانات المشروع.
  - التحقق (JSON/Schema/Model) وفق نمط التشغيل.
  - توليد `generated_content.typ`.
  - التحقق من وجود القوالب.
  - استدعاء Typst لبناء PDF.
- الملفات الناتجة تُكتب في مجلد `build/`.
- النظام يعتمد على وجود `typst` في البيئة التشغيلية، ويسجل المخرجات في تقرير البناء.

## 8. GUI Functional Areas
- **Subjects**: إدارة المواد/الأقسام العليا (إضافة، حذف، ترتيب، تعديل بيانات الموضوع).
- **Blocks**: إدارة كتل المحتوى داخل الموضوع المختار.
- **Dynamic editor**: نموذج تحرير ديناميكي يتغير حسب نوع الـBlock.
- **JSON Import**: مساحة إدخال JSON خام مع أزرار `Validate JSON`, `Import JSON`, `Pretty Format JSON`, `Clear`, `Load JSON From File`.
- **Project Settings**: تعديل بيانات `meta` و`theme`.
- **Log/status area**: عرض الحالة التشغيلية والتقارير والرسائل.

## 9. Main Output Artifacts
- `build/generated_content.typ`: المحتوى المولّد من JSON.
- `build/output.pdf`: ملف PDF الناتج من Typst.
- `build/build.log`: سجل نصّي مختصر لمجريات البناء والأخطاء.
- `build/build_report.json`: تقرير مفصل منظم عن مراحل البناء والنتيجة.

## 10. Error Behavior
- **JSON errors**: تظهر عند parsing مع توصيف واضح، وقد تتضمن `line/column`.
- **schema/model errors**: تظهر مع `stage` المناسب ومسار الحقل `path` ورسالة الخطأ.
- **build errors**: مثل فشل التوليد أو غياب Typst أو فشل compile، وتُسجل في `build_report.json` و`build.log`.
- للمستخدم، الأخطاء تظهر في الـLog/Status، وبعض الحالات تُعرض أيضًا عبر نوافذ تنبيه.

## 11. Practical Usage Notes
- مسارات الصور في `image.src` يجب أن تكون صحيحة وقابلة للوصول أثناء البناء.
- الخطوط تعتمد على ما هو مثبت في نظام التشغيل؛ اختلاف البيئة قد يسبب تحذيرات خطوط.
- `image_placeholder` مخصص للحجز البصري للمكان، بينما `image` يعرض ملف صورة فعلي.
- JSON يبقى المصدر الرسمي للحقيقة، والواجهة هي طبقة إدخال/تعديل لهذا المصدر.

## 12. Short Operational Summary
تشغيليًا: المستخدم يُدخل بيانات مشروع (يدويًا أو عبر JSON)، النظام يتحقق منها، يولّد `generated_content.typ`، ثم يبني PDF عبر Typst، ويعرض النتائج والتقارير من مجلد `build/` مع رسائل حالة واضحة عند النجاح أو الفشل.
