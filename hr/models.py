from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.auth import get_user_model

User = get_user_model()

# ---------- اختيارات الحقول ----------
MARITAL_CHOICES = [
    ("single", "أعزب"),
    ("married", "متزوج"),
    ("divorced", "مطلق"),
    ("widowed", "أرمل"),
]

NATIONALITY_CHOICES = [
    ("egyptian", "مصري"),
    ("other", "غير ذلك"),
]

GENDER_CHOICES = [
    ("male", "ذكر"),
    ("female", "أنثى"),
]

RELIGION_CHOICES = [
    ("muslim", "مسلم"),
    ("other", "غير ذلك"),
]

MILITARY_CHOICES = [
    ("exempted", "إعفاء"),
    ("required", "مطلوب للتجنيد"),
    ("completed", "تم الانتهاء"),
]

VEHICLE_CHOICES = [
    ("no", "لا"),
    ("bicycle", "عجلة"),
    ("motorcycle", "دراجة بخارية"),
    ("car", "سيارة"),
]

EDU_DEGREE_CHOICES = [
    ("primary", "ابتدائية"),
    ("preparatory", "إعدادية"),
    ("diploma", "دبلوم"),
    ("bachelor", "بكالوريوس"),
]

GRADE_CHOICES = [
    ("pass", "مقبول"),
    ("good", "جيد"),
    ("vgood", "جيد جدًا"),
    ("excellent", "ممتاز"),
]

JOB_CHOICES = [
    ("chef", "شيف"),
    ("asst_chef", "مساعد شيف"),
    ("packaging", "تعبئة وتغليف"),
    ("cleaning", "نظافة"),
]

STATUS_CHOICES = [
    ("pending", "قيد الانتظار"),
    ("accepted", "مقبول"),
    ("rejected", "مرفوض"),
    ("reserve", "احتياطي"),
]

# ---------- فاليديشنز عامة ----------
national_id_validator = RegexValidator(
    regex=r"^\d{14}$",
    message="الرقم القومي يجب أن يكون 14 رقمًا."
)
egy_phone_validator = RegexValidator(
    regex=r"^0\d{10}$",
    message="رقم الهاتف يجب أن يكون 11 رقمًا ويبدأ بصفر."
)

# ---------- الموديلات الأساسية ----------
class Applicant(models.Model):
    # رقم الطلب: تسلسلي يبدأ من 1 تلقائيًا
    order_number = models.AutoField(primary_key=True)

    # بيانات مقدم الطلب
    national_id   = models.CharField("الرقم القومي",max_length=14, unique=True, validators=[national_id_validator])
    full_name = models.CharField("الاسم الكامل", max_length=200)
    phone = models.CharField("رقم الهاتف", max_length=11, validators=[egy_phone_validator])
    marital_status = models.CharField("الحالة الاجتماعية", max_length=10, choices=MARITAL_CHOICES)
    nationality = models.CharField("الجنسية", max_length=20, choices=NATIONALITY_CHOICES)
    gender = models.CharField("النوع", max_length=10, choices=GENDER_CHOICES)
    religion = models.CharField("الديانة", max_length=10, choices=RELIGION_CHOICES)
    military_status = models.CharField("الموقف من التجنيد", max_length=12, choices=MILITARY_CHOICES)
    email = models.EmailField("البريد الإلكتروني", blank=True, null=True)


    relative_name = models.CharField("اسم القريب", max_length=200)
    relative_phone = models.CharField("هاتف القريب", max_length=11, validators=[egy_phone_validator])

    is_smoker = models.BooleanField("مدخن", choices=[(True, "نعم"), (False, "لا")], default=False)
    vehicle_ownership = models.CharField("وسيلة/سيارة", max_length=12, choices=VEHICLE_CHOICES)

    photo = models.ImageField("الصورة الشخصية", upload_to="hr/photos/", blank=True, null=True)  # إعداد MEDIA مطلوب

    # المؤهل الدراسي
    edu_degree = models.CharField("المؤهل", max_length=12, choices=EDU_DEGREE_CHOICES, blank=True, null=True)
    grad_year = models.PositiveIntegerField("سنة التخرج", blank=True, null=True)  # سنة فقط
    edu_institution = models.CharField("جهة الحصول", max_length=200, blank=True, null=True)  # جهة الحصول
    specialization = models.CharField("التخصص", max_length=200, blank=True, null=True)  # التخصص
    postgrad_study = models.CharField("دراسات عليا", max_length=200, blank=True, null=True)  # دراسات عليا (نصي)
    edu_grade = models.CharField("التقدير", max_length=10, choices=GRADE_CHOICES, blank=True, null=True)


    # بيانات الوظيفة
    job_applied = models.CharField("الوظيفة المتقدم لها", max_length=20, choices=JOB_CHOICES)
    job_code = models.CharField("كود الوظيفة", max_length=20, blank=True, null=True)
    submitted_at = models.DateTimeField("تاريخ التقديم", auto_now_add=True)  # تاريخ التقديم
    prev_applied = models.BooleanField("سبق التقديم بحلواني الأصيل", default=False)

    has_relatives_in_company = models.BooleanField("هل لديك أقارب في الشركة؟", default=False)
    relatives_in_company = models.TextField("تفاصيل الأقارب في الشركة", blank=True, null=True)

    has_relatives_in_competitors = models.BooleanField("هل لديك أقارب في شركات منافسة؟", default=False)
    relatives_in_competitors = models.TextField("تفاصيل الأقارب في المنافسين", blank=True, null=True)

    has_health_issues = models.BooleanField("هل لديك مشاكل صحية؟", default=False)
    health_issues_details = models.TextField("تفاصيل المشاكل الصحية", blank=True, null=True)


    # الحالة ومسارات العمل
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    created_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="hr_created_requests")
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="hr_last_updated_requests")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    decision_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="hr_decisions")
    decision_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"{self.order_number} - {self.full_name}"


class ApplicantExperience(models.Model):
    """الخبرات السابقة: متعدد لكل متقدم"""
    applicant = models.ForeignKey(Applicant,verbose_name="مقدم الطلب",on_delete=models.CASCADE,related_name="experiences")
    employer = models.CharField("جهة العمل", max_length=200)
    job_title = models.CharField("المسمى الوظيفي", max_length=200)
    years = models.PositiveIntegerField("عدد سنوات الخبرة", validators=[MinValueValidator(1)])
    salary = models.DecimalField("الراتب", max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    reason_for_leaving = models.CharField("سبب ترك العمل", max_length=255)
           # سبب ترك العمل

    def __str__(self):
        return f"{self.applicant.full_name} - {self.job_title} ({self.years} سنة)"


class ApplicantHistory(models.Model):
    """تسجيل كل تعديل/حذف/قرار"""
    ACTIONS = [
        ("create", "إنشاء"),
        ("update", "تعديل"),
        ("delete", "حذف"),
        ("decision", "قرار"),
    ]
    applicant  = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="history")
    action     = models.CharField(max_length=10, choices=ACTIONS)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    changes    = models.TextField(blank=True, null=True)  # نص يوضح إيه اللي اتغير

    def __str__(self):
        return f"{self.applicant} - {self.action} - {self.updated_at}"


class DeletedApplicant(models.Model):
    """سجل المحذوفات مع نسخة من البيانات الأساسية"""
    original_order_number = models.IntegerField()
    full_name   = models.CharField(max_length=200)
    national_id = models.CharField(max_length=14)
    phone       = models.CharField(max_length=11)
    email       = models.EmailField(blank=True, null=True)
    snapshot_at = models.DateTimeField(auto_now_add=True)
    deleted_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Deleted #{self.original_order_number} - {self.full_name}"


class AcceptedApplicant(models.Model):
    """جدول متابعة المقبولين"""
    applicant       = models.OneToOneField(Applicant, on_delete=models.CASCADE, related_name="accepted_copy")
    follow_up_note  = models.TextField(blank=True, null=True)
    scheduled_date  = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.applicant.full_name} (مقبول)"


class Queue(models.Model):
    """صف الدور الحالي (يفضل يكون سجل وحيد تُحدّث قيمته)"""
    current_applicant = models.OneToOneField(Applicant, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"الدور الحالي: {self.current_applicant or 'غير محدد'}"
