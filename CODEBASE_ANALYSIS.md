# CODEBASE ANALYSIS

## 1. Executive Summary
هذا المستودع يحقق نظام SDRE كـ “سلسلة صارمة” تبدأ من ملف JSON (مصدر الحقيقة)، ثم تمر عبر طبقة تحقق ثنائية (JSON Schema ثم Pydantic models)، ثم تتحول إلى مصدر Typst (`build/generated_content.typ`) ويتم تجميعها إلى PDF (`build/output.pdf`). فوق ذلك توجد واجهة سطح مكتب (CustomTkinter) لتحرير نفس البيانات بشكل form-based (بدون WYSIWYG) مع دمج إجراءات Validate/Build داخل الواجهة.

الطبقات الأساسية:
- **Models (`src/models/`)**: تعريف العقدة المعتمدة للملف، مع صرامة (strict + extra forbid) وتحقق علاقات مهم (unique ids).
- **Validation (`src/validation/`)**: تحميل JSON ثم التحقق مقابل Schema ثم مقابل `ProjectFile`.
- **Generator (`src/generator/`)**: تحويل `ProjectFile` إلى Typst source (content فقط).
- **Templates (`templates/`)**: Typst shell/macros ثابتة، والمحتوى الديناميكي في `build/generated_content.typ`.
- **Build Service (`src/services/`)**: orchestration (validate + generate + typst compile) وكتابة report/log.
- **GUI (`src/ui/`)**: محرر form-based يستدعي الخدمات السابقة ولا يكرر منطقها.

## 2. Runtime Entry Flow
مسار التشغيل الفعلي (GUI):
1. `app.py` يستورد `MainWindow` من `src.ui.main_window`.
2. `MainWindow` ينشئ `AppController` (مخزن الحالة + عمليات IO + ربط backend).
3. `AppController` يبدأ بـ `project_state.new_project_file()` كحالة افتراضية في الذاكرة.
4. أحداث القائمة (Open/Save/Validate/Build/Settings…) تستدعي methods في `MainWindow` والتي تستدعي بدورها `AppController` ثم backend services/validation/generator.

مسارات تشغيل CLI المستقلة:
- Validation: `python -m src.validation.cli validate <file.json>`
- Generation (content فقط): `python -m src.generator.engine <file.json>`
- Build PDF: `python -m src.services.build_service build <file.json> --mode strict|preview`

## 3. Core Architecture Map
خريطة معمارية نصية (علاقات “يعتمد على”):

```
JSON file (examples/*.json)
  └─ schema/project.schema.json  (Draft 2020-12)
      └─ src/validation/schema_layer.py
          └─ src/validation/engine.py  (load_json -> schema -> model)
              └─ src/models/project.py (ProjectFile root)
                  ├─ src/models/meta.py
                  ├─ src/models/theme.py
                  ├─ src/models/subject.py
                  ├─ src/models/blocks.py
                  └─ src/models/inlines.py

ProjectFile (validated model)
  └─ src/generator/*_renderer.py
      └─ build/generated_content.typ
          └─ templates/main.typ + templates/macros.typ
              └─ typst compile
                  └─ build/output.pdf

GUI
  └─ src/ui/main_window.py
      └─ src/ui/controllers/app_controller.py
          ├─ src/ui/state/project_state.py (in-memory ops + save/load)
          ├─ src/validation/engine.py (Validate)
          └─ src/services/build_service.py (Build -> typst_runner)
```

## 4. Key Files by Layer

### Entry
**`app.py`**
- المسار: `app.py`
- الدور: نقطة تشغيل الواجهة الرسومية.
- يعتمد على: `src.ui.main_window.MainWindow`, `customtkinter`.
- ما يعتمد عليه لاحقًا: يبدأ سلسلة UI بالكامل.
- نرجع إليه عند: تغيير طريقة تشغيل التطبيق أو إعدادات theme العامة للـ CustomTkinter.

### Models
**`src/models/_base.py`**
- الدور: أساس الصرامة عبر `SDREModel` (`extra="forbid"`, `strict=True`, `validate_assignment=True`).
- يعتمد على: `pydantic`.
- ما يعتمد عليه لاحقًا: كل النماذج في `src/models/`.
- نرجع إليه عند: تغيير سياسة الصرامة أو سلوك التحقق العام لكل الموديلات.

**`src/models/types.py`**
- الدور: أنواع مشتركة (Identifier/LangTag/ColorHex/DateTimeStr) بقيود regex.
- يعتمد على: `pydantic.StringConstraints`.
- ما يعتمد عليه لاحقًا: `Meta`, `Subject`, `Blocks`… إلخ.
- نرجع إليه عند: تغيير قواعد التسمية (id patterns) أو تنسيق timestamps أو قيود الألوان/اللغة.

**`src/models/project.py`**
- الدور: الموديل الجذري:
  - `ProjectFile` (root wrapper) يحتوي `project: Project`.
  - `Project` يحتوي `meta/theme/subjects`.
  - يفرض علاقات مهمة: uniqueness لـ `Subject.id` و uniqueness لـ `Block.id` داخل كل Subject.
- يعتمد على: `Meta`, `Theme`, `Subject`, `Block`, `SDREModel`.
- ما يعتمد عليه لاحقًا: validation model layer, generator, GUI state/IO.
- نرجع إليه عند: تغيير شكل root أو قواعد العلاقات (unique ids).

**`src/models/subject.py`**
- الدور: تعريف `Subject` (id/title/description/blocks).
- يعتمد على: `Block` (forward reference)، `Identifier`.
- ما يعتمد عليه لاحقًا: `Project.subjects`.
- نرجع إليه عند: تعديل بيانات subject أو بنية الحاوية.

**`src/models/blocks.py`**
- الدور: تعريف جميع أنواع الـ blocks المعتمدة (14 نوع) عبر discriminated union `Block`.
- قيود مهمة:
  - `BlockBase.id` إلزامي.
  - `BlockImagePlaceholder` يفرض شرط (reserve_height_mm أو aspect_ratio) عبر `model_validator`.
- يعتمد على: `InlineNode`, `Identifier`.
- ما يعتمد عليه لاحقًا: schema alignment, generator block rendering, GUI block forms.
- نرجع إليه عند: إضافة/تعديل block type أو تغيير حقوله.

**`src/models/inlines.py`**
- الدور: Inline nodes (`text`, `ltr`, `inline_math`, `inline_code`) عبر discriminated union `InlineNode`.
- يعتمد على: `SDREModel`.
- ما يعتمد عليه لاحقًا: paragraph content, lists/table cells captions, generator inline rendering, GUI inline editor.
- نرجع إليه عند: تعديل inline types أو حقولها (مثل `ltr.style` أو `inline_math.value`).

**`src/models/meta.py`**
- الدور: `Meta` (id/title/subtitle/author/language/direction/version/created_at/updated_at).
- يعتمد على: `Identifier`, `LangTag`, `DateTimeStr`.
- ما يعتمد عليه لاحقًا: schema validation + typst document shell (meta.language/meta.direction).
- نرجع إليه عند: تعديل حقول meta أو قيودها.

**`src/models/theme.py`**
- الدور: `Theme` وهيكلية theme الأساسية (page/fonts/colors/text + optional groups).
- يعتمد على: `ColorHex`, `SDREModel`.
- ما يعتمد عليه لاحقًا: Typst macros (page/text/color) + Project Settings UI.
- نرجع إليه عند: تغيير هيكل theme أو قيود المقاسات/الألوان.

### Validation
**`schema/project.schema.json`**
- المسار: `schema/project.schema.json`
- الدور: المصدر الرسمي لقواعد JSON على مستوى schema (Draft 2020-12).
- يعتمد على: JSON Schema Draft 2020-12.
- ما يعتمد عليه لاحقًا: `src/validation/schema_layer.py`, generator engine (validation قبل توليد).
- نرجع إليه عند: أي تغيير في العقدة المعتمدة أو قيود الحقول على مستوى JSON.

**`src/validation/engine.py`**
- الدور: orchestrator للـ validation (load_json → schema → model).
- يعتمد على: `schema_layer`, `model_layer`, `ValidationReport`.
- ما يعتمد عليه لاحقًا: CLI validate (`src/validation/cli.py`), GUI open/validate, build pipeline (جزئيًا عبر build_service).
- نرجع إليه عند: تغيير تسلسل التحقق أو stage naming أو نقاط التوقف.

**`src/validation/schema_layer.py`**
- الدور:
  - تحميل schema (`load_schema`)
  - التحقق من صحة schema نفسها (`validate_schema`)
  - التحقق من instance (`validate_instance`) وإرجاع `ErrorItem` مع path + schema path hint.
- يعتمد على: `jsonschema.Draft202012Validator`.
- ما يعتمد عليه لاحقًا: validation engine, generator engine, build service.
- نرجع إليه عند: ضبط format checking أو شكل أخطاء schema.

**`src/validation/model_layer.py`**
- الدور: تشغيل `ProjectFile.model_validate(instance)` وتطبيع أخطاء Pydantic إلى `ErrorItem`.
- يعتمد على: `ProjectFile`, `pydantic.ValidationError`.
- ما يعتمد عليه لاحقًا: validation engine.
- نرجع إليه عند: تغيير mapping للأخطاء أو مسارات loc→path.

**`src/validation/errors.py`**
- الدور: تعريف `ErrorItem` (code/severity/path/message/hint) + تحويل loc إلى JSON Pointer-like paths.
- يعتمد على: Pydantic BaseModel.
- ما يعتمد عليه لاحقًا: validation reports + build reports.
- نرجع إليه عند: تغيير شكل error contract أو path formatting.

**`src/validation/report.py`**
- الدور: `ValidationReport` (ok/file/stage/errors).
- ما يعتمد عليه لاحقًا: CLI validate, GUI validate display.
- نرجع إليه عند: تعديل شكل تقرير التحقق.

**`src/validation/cli.py`**
- الدور: CLI entrypoint للتحقق الصارم.
- يعتمد على: `validate_project_file`.
- ما يعتمد عليه لاحقًا: استخدام المستخدم المباشر عبر سطر الأوامر.
- نرجع إليه عند: تغيير واجهة CLI أو شكل الإخراج النصي.

### Generator (Typst Content)
**`src/generator/engine.py`**
- الدور: orchestration لتوليد المحتوى:
  - يحمّل JSON من path.
  - يتحقق schema (باستخدام schema_layer) قبل تحويله إلى `ProjectFile`.
  - يكتب `build/generated_content.typ` (افتراضيًا).
- يعتمد على: `ProjectFile`, `schema_layer`, `project_renderer`.
- ما يعتمد عليه لاحقًا: build_service (يستدعي `generate_content`).
- نرجع إليه عند: تغيير مسار output الافتراضي أو آلية التشغيل من CLI.

**`src/generator/project_renderer.py`**
- الدور: يحول `ProjectFile` إلى Typst source شامل:
  - يعرّف `meta` و `theme` كـ Typst dictionaries.
  - يستورد macros (`#import "../templates/macros.typ": *`) داخل المحتوى المولد.
  - يكتب body بسرد subjects ثم blocks (خطية).
- يعتمد على: `block_renderer`, `inline_renderer._escape_typst_string`.
- ما يعتمد عليه لاحقًا: الملف النهائي `build/generated_content.typ`.
- نرجع إليه عند: تغيير “شكل الملف المولد” أو آلية تمرير meta/theme إلى Typst.

**`src/generator/block_renderer.py`**
- الدور: تحويل `Block` إلى استدعاءات macros (`#sdre_*`) في Typst.
- يعتمد على: `Inline` rendering لـ captions/content، وعلى أنواع blocks.
- ما يعتمد عليه لاحقًا: أي إخراج Typst للـ blocks.
- نرجع إليه عند: تعديل mapping لبلوك معين أو شكل الاستدعاءات في Typst.

**`src/generator/inline_renderer.py`**
- الدور: تحويل `InlineNode` إلى Typst fragments، مع escaping محافظ للنصوص/strings.
- يعتمد على: Inline models.
- ما يعتمد عليه لاحقًا: paragraphs/lists/table cells/captions.
- نرجع إليه عند: تعديل سلوك escaping أو mapping للـ inline macros.

### Services (Build to PDF)
**`src/services/build_service.py`**
- الدور: build pipeline end-to-end:
  - load JSON
  - schema validate
  - model validate
  - generate content (`build/generated_content.typ`)
  - verify templates
  - verify typst in PATH
  - run typst compile
  - write `build/output.pdf`, `build/build.log`, `build/build_report.json`
  - يدعم `mode=strict|preview`
- يعتمد على: `validation.engine.load_json`, `schema_layer`, `ProjectFile`, `generator.engine.generate_content`, `typst_runner`.
- ما يعتمد عليه لاحقًا: GUI build actions وCLI build.
- نرجع إليه عند: مشاكل build stages، كتابة التقارير/السجلات، أو تعديل سلوك strict/preview.

**`src/services/typst_runner.py`**
- الدور:
  - اكتشاف Typst (`find_typst`)
  - تنفيذ compile عبر subprocess مع `--root` لضبط project root
  - التقاط stdout/stderr بترميز UTF-8 مع `errors="replace"`
- يعتمد على: subprocess/shutil.
- ما يعتمد عليه لاحقًا: build_service compile stage.
- نرجع إليه عند: مشاكل تشغيل Typst، أو تغييرات في صيغة الأوامر/timeout/التقاط المخرجات.

### Templates
**`templates/main.typ`**
- الدور: shell ثابت لTypst:
  - يستورد `macros.typ`
  - يضمّن `../build/generated_content.typ`
- يعتمد على: `templates/macros.typ` ووجود `build/generated_content.typ`.
- ما يعتمد عليه لاحقًا: typst compile output.
- نرجع إليه عند: تعديل “غلاف” المستند أو طريقة تضمين المحتوى.

**`templates/macros.typ`**
- الدور: مجموعة ماكروز `sdre_*`:
  - `sdre_document` لضبط page/text/dir.
  - ماكروز للعناصر: section/subsection/paragraph/LTR/inline code/math/code block/math block/table/image/image_placeholder/note/warning/lists/page_break/hr.
- يعتمد على: متغيرات `meta/theme` كما يعرّفها `generated_content.typ`.
- ما يعتمد عليه لاحقًا: generator output + build compile.
- نرجع إليه عند: أي تغيير في الإخراج المرئي أو mapping Typst للـ blocks/inlines.

### UI
**`src/ui/main_window.py`**
- الدور: نافذة التطبيق الأساسية:
  - قائمة File/Actions
  - Subjects Treeview + Blocks Treeview
  - Editor area (dynamic block form)
  - Log panel
  - تأكيدات dirty عند close/open/new
- يعتمد على: `AppController`, `project_state`, `make_block_form`, `ProjectSettingsDialog`, `LogPanel`.
- ما يعتمد عليه لاحقًا: كل تجربة المستخدم GUI.
- نرجع إليه عند: تغيير سلوك الواجهة العامة، ربط الأزرار/القائمة، مسارات الاختيار/التحديث.

**`src/ui/controllers/app_controller.py`**
- الدور: طبقة ربط بين UI والbackend:
  - يحتفظ بـ `project_file` و`path` و`dirty`
  - Open يعتمد على `validate_project_file` ثم `load_project_file`
  - Build يعتمد على `build_pdf` بعد Save
- يعتمد على: `src/validation/engine`, `src/services/build_service`, `src/ui/state/project_state`.
- ما يعتمد عليه لاحقًا: كل actions في `MainWindow`.
- نرجع إليه عند: تغيير سلوك open/save/build/validate من منظور UI.

**`src/ui/state/project_state.py`**
- الدور: منطق حالة “غير UI”:
  - إنشاء مشروع افتراضي صالح (`new_project_file`)
  - load/save JSON (save يستخدم `exclude_none=True` لتوافق schema)
  - عمليات subjects/blocks (add/delete/move/get) وتحديث `updated_at`
- يعتمد على: models فقط.
- ما يعتمد عليه لاحقًا: controller وforms.
- نرجع إليه عند: تعديل منطق الحالة (إعادة الترتيب، توليد ids، serialization).

**`src/ui/forms/block_forms.py`**
- الدور: محررات blocks حسب النوع (forms):
  - Section/Subsection/Paragraph/Code/Math/Table/Image/ImagePlaceholder/Note/Warning/Bullet/Numbered/PageBreak/HorizontalRule
  - `make_block_form` هو dispatcher الأساسي.
- يعتمد على: models + `InlineEditor`.
- ما يعتمد عليه لاحقًا: editor area في `MainWindow`.
- نرجع إليه عند: تعديل محرر block معين أو إضافة حقول للـ form.

**`src/ui/forms/inline_editor.py`**
- الدور: محرر inline nodes قائم على قائمة (add/edit/delete/up/down) وdialog لتحرير node.
- يعتمد على: inline models.
- ما يعتمد عليه لاحقًا: Paragraph/Note/Warning/Image caption/Table cells/List item dialogs.
- نرجع إليه عند: تعديل UX تحرير content للـ paragraphs أو إضافة inline types.

**`src/ui/forms/project_settings.py`**
- الدور: نافذة إعدادات المشروع (Meta + Theme) على شكل Tabs وتطبيق التغييرات على الموديل مباشرة.
- يعتمد على: controller state + theme optional models.
- ما يعتمد عليه لاحقًا: Action “Project Settings…” في `MainWindow`.
- نرجع إليه عند: تعديل حقول الإعدادات المعروضة أو طريقة تطبيقها على الموديل.

**`src/ui/widgets/log_panel.py`**
- الدور: عرض status + log text داخل UI.
- يعتمد على: CustomTkinter.
- ما يعتمد عليه لاحقًا: عرض نتائج validate/build داخل `MainWindow`.
- نرجع إليه عند: تعديل شكل/سلوك عرض الرسائل.

### Tests
**`tests/test_validation.py`**
- الدور: تغطية validate_project_file لحالات نجاح/فشل (schema/model).
- يعتمد على: `src.validation.engine`.
- نرجع إليه عند: تغيير stage naming أو error codes أو سلوك strict.

**`tests/test_generator.py`**
- الدور: تغطية inline/block renderer + توليد ملف Typst من `ProjectFile`.
- يعتمد على: generator renderers + models.
- نرجع إليه عند: تغيير صيغة output Typst أو أسماء macros أو شكل الاستدعاءات.

**`tests/test_build_service.py`**
- الدور: اختبارات build pipeline مع mocking لـ typst runner (binary missing, stop on validation, generator failure, success path).
- يعتمد على: `src.services.build_service`, `src.services.typst_runner`.
- نرجع إليه عند: تغيير stages أو أسماء الملفات الناتجة أو contract build report/log.

**`tests/test_ui_state.py`**
- الدور: تغطية منطق state (new/open/save/subject ops/block ops/serialization shape).
- يعتمد على: `src.ui.state.project_state`.
- نرجع إليه عند: تغيير منطق توليد ids أو ترتيب العناصر أو serialization.

**`tests/test_project_settings_updates.py`**
- الدور: تغطية تغييرات meta/theme + التأكد أن save لا يكتب null للحقول الاختيارية.
- يعتمد على: `project_state.save_project_file/load_project_file`.
- نرجع إليه عند: تغيير سياسة serialization أو بنية Theme optional fields.

**`tests/test_controller_dirty_state.py`**
- الدور: تغطية dirty flag و`updated_at` bump في controller.
- يعتمد على: `AppController`.
- نرجع إليه عند: تغيير سلوك dirty tracking.

## 5. Data Flow
تدفق البيانات (السلسلة القياسية):
1. **JSON**: ملف مثل `examples/sample_project.json`.
2. **Validation (Schema)**: `src/validation/schema_layer.validate_instance` باستخدام `schema/project.schema.json`.
3. **Validation (Model)**: `src/validation/model_layer.validate_model` عبر `ProjectFile.model_validate`.
4. **Models**: تمثيل صارم داخل `ProjectFile -> Project -> subjects[] -> blocks[]` مع `InlineNode` داخل `paragraph.content`/captions/lists/table cells.
5. **Generator**: `src/generator/project_renderer.render_project_file` يحول الموديل إلى Typst source.
6. **Typst**:
   - `templates/main.typ` يضمّن `build/generated_content.typ`.
   - `templates/macros.typ` يوفر ماكروز `sdre_*`.
7. **PDF**: Typst compile يكتب `build/output.pdf`.
8. **GUI Actions**:
   - Validate من الواجهة: `AppController.validate_current_file` (ملف محفوظ) أو تحقق model-in-memory إن لم يكن هناك path.
   - Build من الواجهة: `AppController.build` يستدعي `build_pdf` (بعد حفظ الملف).

## 6. UI-to-Backend Wiring
التوصيل بين UI والـ backend يتم عبر `AppController`:
- `MainWindow` لا يستدعي طبقات validation/build/generator مباشرة غالبًا؛ بل يستدعي controller.
- `AppController.open_project(path)`:
  - يستدعي `validate_project_file(path)` (schema ثم model).
  - إذا نجح، يستدعي `project_state.load_project_file(path)` لتعبئة `ProjectFile` في الذاكرة.
- `AppController.save/save_as` يستعمل `project_state.save_project_file` الذي يكتب JSON من `ProjectFile.model_dump(... exclude_none=True)`.
- `AppController.build(mode)` يستدعي `src/services/build_service.build_pdf` وهو الذي يقوم بسلسلة validate + generate + typst compile ويكتب artifacts.
- عرض النتائج داخل UI يتم في `LogPanel` عبر `MainWindow._validate/_build` (يطبع JSON report داخل panel).

## 7. Change Impact Guide
**إذا أردنا تعديل X فأين نذهب؟**

| التغيير المطلوب | ملفات أساسية (ابدأ بها) | ملفات ثانوية محتملة |
|---|---|---|
| تعديل schema | `schema/project.schema.json` | `src/models/*` (للمطابقة), `tests/test_validation.py` |
| تعديل block type (إضافة/تعديل حقول) | `src/models/blocks.py` + `schema/project.schema.json` | `src/generator/block_renderer.py`, `src/ui/forms/block_forms.py`, `tests/test_generator.py` |
| تعديل paragraph inline behavior | `src/models/inlines.py` + `src/models/blocks.py` (paragraph) | `schema/project.schema.json`, `src/generator/inline_renderer.py`, `src/ui/forms/inline_editor.py` |
| تعديل Typst macros أو الإخراج المرئي | `templates/macros.typ` | `src/generator/*_renderer.py`, `templates/main.typ` |
| تعديل build behavior (مراحل/paths/report/log) | `src/services/build_service.py` | `src/services/typst_runner.py`, `tests/test_build_service.py` |
| تعديل رسائل/شكل validation errors | `src/validation/errors.py` + `src/validation/schema_layer.py`/`model_layer.py` | `src/validation/engine.py`, `tests/test_validation.py` |
| تعديل Project Settings UI | `src/ui/forms/project_settings.py` | `src/ui/main_window.py` (menu wiring), `src/ui/controllers/app_controller.py` |
| تعديل block forms في GUI | `src/ui/forms/block_forms.py` | `src/ui/forms/inline_editor.py` |
| تعديل log panel | `src/ui/widgets/log_panel.py` | `src/ui/main_window.py` (كيفية الكتابة للـ panel) |
| تعديل save/open behavior في GUI | `src/ui/controllers/app_controller.py` + `src/ui/state/project_state.py` | `src/ui/main_window.py` (dialogs), `src/validation/engine.py` (open validation) |
| تعديل generator output file structure | `src/generator/project_renderer.py` | `src/generator/engine.py`, `templates/main.typ` |

## 8. Important Generated vs Source Files
تمييز مهم بين ملفات المصدر وملفات الناتج:

### Source Files (يُعدّلها المطور)
- `schema/project.schema.json`
- `src/models/*`
- `src/validation/*`
- `src/generator/*`
- `src/services/*`
- `templates/main.typ`, `templates/macros.typ`
- `src/ui/*`
- `examples/sample_project.json`
- `app.py`, `requirements.txt`, `README.md`

### Generated Files (ينشئها النظام، لا تعتبر مصدر الحقيقة)
- `build/generated_content.typ` (ناتج generator)
- `build/output.pdf` (ناتج typst compile)
- `build/build_report.json` (ناتج build_service)
- `build/build.log` (ناتج build_service)

### Runtime Artifacts (تشغيل/اختبار)
- ملفات/مجلدات `__pycache__/`, `.pytest_cache/`

## 9. Test Coverage Overview
تغطية الاختبارات الحالية حسب الطبقة:
- **Models**: تغطية غير مباشرة عبر `ProjectFile.model_validate` في اختبارات validation/generator/UI state.
- **Schema Validation**: مغطاة عبر `tests/test_validation.py` (missing fields/invalid types/inline structure/image_placeholder).
- **Model-only constraints**: مغطاة (duplicate subject ids / duplicate block ids) عبر `tests/test_validation.py`.
- **Generator**: مغطاة عبر `tests/test_generator.py` على مستوى النص الناتج (وجود الاستدعاءات) وليس على مستوى تشغيل Typst.
- **Build Service**: مغطاة عبر `tests/test_build_service.py` مع mocking لTypst invocation + فحص إنشاء report/log/artifacts.
- **UI state/controller**: مغطاة عبر `tests/test_ui_state.py`, `tests/test_controller_dirty_state.py`, `tests/test_project_settings_updates.py`. تغطية الـ widgets نفسها غير موجودة (الاختبارات تركز على منطق state/controller).

## 10. Final Practical Reading Order
ترتيب قراءة عملي لمهندس جديد لفهم المشروع بسرعة:
1. `README.md` (الصورة العامة + أوامر التشغيل)
2. `schema/project.schema.json` (العقدة الرسمية للـ JSON)
3. `src/models/_base.py` ثم `src/models/project.py` (root + strictness + العلاقات)
4. `src/models/blocks.py` و`src/models/inlines.py` (أنواع المحتوى)
5. `src/validation/engine.py` ثم `schema_layer.py` و`model_layer.py` و`errors.py` (منطق التحقق وتقارير الأخطاء)
6. `src/generator/project_renderer.py` ثم `block_renderer.py` و`inline_renderer.py` (كيف يتحول الموديل إلى Typst)
7. `templates/main.typ` و`templates/macros.typ` (كيف يُبنى المستند في Typst)
8. `src/services/build_service.py` و`src/services/typst_runner.py` (كيف ينتج PDF وكيف تُكتب التقارير)
9. `src/ui/main_window.py` ثم `src/ui/controllers/app_controller.py` ثم `src/ui/state/project_state.py` (كيف تعمل الواجهة وتربط backend)
10. `src/ui/forms/*` و`src/ui/widgets/log_panel.py` (تفاصيل التحرير)
11. `tests/*` (فهم التغطية الحالية وسلوك النظام المتوقع)

## 11. Appendix: Project Tree (Important Files Only)
```text
SDRE/
  app.py
  README.md
  requirements.txt
  schema/
    project.schema.json
  examples/
    sample_project.json
  templates/
    main.typ
    macros.typ
  src/
    models/
      _base.py
      types.py
      meta.py
      theme.py
      inlines.py
      blocks.py
      subject.py
      project.py
    validation/
      cli.py
      engine.py
      schema_layer.py
      model_layer.py
      errors.py
      report.py
    generator/
      engine.py
      project_renderer.py
      block_renderer.py
      inline_renderer.py
    services/
      build_service.py
      typst_runner.py
    ui/
      main_window.py
      controllers/
        app_controller.py
      state/
        project_state.py
      forms/
        block_forms.py
        inline_editor.py
        project_settings.py
      widgets/
        log_panel.py
  tests/
    test_validation.py
    test_generator.py
    test_build_service.py
    test_ui_state.py
    test_project_settings_updates.py
    test_controller_dirty_state.py
  build/  (generated artifacts)
    generated_content.typ
    output.pdf
    build_report.json
    build.log
```

