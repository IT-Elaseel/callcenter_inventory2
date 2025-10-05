from django import forms
from django.forms import inlineformset_factory
from .models import (
    Applicant, ApplicantExperience, AcceptedApplicant,
    MARITAL_CHOICES, NATIONALITY_CHOICES, GENDER_CHOICES, RELIGION_CHOICES,
    MILITARY_CHOICES, VEHICLE_CHOICES, EDU_DEGREE_CHOICES, GRADE_CHOICES, JOB_CHOICES
)

class ApplicantCreateForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = [
            # بيانات مقدم الطلب
            "national_id", "full_name", "phone", "marital_status", "nationality",
            "gender", "religion", "military_status", "email",
            "relative_name", "relative_phone", "is_smoker", "vehicle_ownership", "photo",

            # المؤهل
            "edu_degree", "grad_year", "edu_institution", "specialization", "postgrad_study", "edu_grade",

            # الوظيفة
            "job_applied", "job_code", "prev_applied",
            "has_relatives_in_company", "relatives_in_company",
            "has_relatives_in_competitors", "relatives_in_competitors",
            "has_health_issues", "health_issues_details",
        ]
        widgets = {
            "national_id":      forms.TextInput(attrs={"class": "form-control", "placeholder": "الرقم القومي (14 رقم)"}),
            "full_name":        forms.TextInput(attrs={"class": "form-control", "placeholder": "الاسم رباعي"}),
            "phone":            forms.TextInput(attrs={"class": "form-control", "placeholder": "رقم الهاتف 11 رقم يبدأ بصفر"}),
            "marital_status":   forms.Select(choices=MARITAL_CHOICES, attrs={"class": "form-select"}),
            "nationality":      forms.Select(choices=NATIONALITY_CHOICES, attrs={"class": "form-select"}),
            "gender":           forms.Select(choices=GENDER_CHOICES, attrs={"class": "form-select"}),
            "religion":         forms.Select(choices=RELIGION_CHOICES, attrs={"class": "form-select"}),
            "military_status":  forms.Select(choices=MILITARY_CHOICES, attrs={"class": "form-select"}),
            "email":            forms.EmailInput(attrs={"class": "form-control", "placeholder": "اختياري"}),
            "relative_name":    forms.TextInput(attrs={"class": "form-control"}),
            "relative_phone":   forms.TextInput(attrs={"class": "form-control", "placeholder": "11 رقم يبدأ بصفر"}),
            "is_smoker":        forms.Select(choices=[(True, "نعم"), (False, "لا")], attrs={"class": "form-select"}),
            "vehicle_ownership":forms.Select(choices=VEHICLE_CHOICES, attrs={"class": "form-select"}),
            "photo":            forms.ClearableFileInput(attrs={"class": "form-control"}),

            "edu_degree":       forms.Select(choices=EDU_DEGREE_CHOICES, attrs={"class": "form-select"}),
            "grad_year":        forms.NumberInput(attrs={"class": "form-control", "placeholder": "سنة التخرج (عام)"}),
            "edu_institution":  forms.TextInput(attrs={"class": "form-control", "placeholder": "جهة الحصول"}),
            "specialization":   forms.TextInput(attrs={"class": "form-control", "placeholder": "التخصص"}),
            "postgrad_study":   forms.TextInput(attrs={"class": "form-control", "placeholder": "دراسات عليا"}),
            "edu_grade":        forms.Select(choices=GRADE_CHOICES, attrs={"class": "form-select"}),

            "job_applied":      forms.Select(choices=JOB_CHOICES, attrs={"class": "form-select"}),
            "job_code":         forms.TextInput(attrs={"class": "form-control"}),
            "prev_applied":     forms.Select(choices=[(True, "نعم"), (False, "لا")], attrs={"class": "form-select"}),

            "has_relatives_in_company":    forms.Select(choices=[(True, "نعم"), (False, "لا")], attrs={"class": "form-select"}),
            "relatives_in_company":        forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "has_relatives_in_competitors":forms.Select(choices=[(True, "نعم"), (False, "لا")], attrs={"class": "form-select"}),
            "relatives_in_competitors":    forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "has_health_issues":           forms.Select(choices=[(True, "نعم"), (False, "لا")], attrs={"class": "form-select"}),
            "health_issues_details":       forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def clean(self):
        data = super().clean()
        phone = data.get("phone") or ""
        rel_phone = data.get("relative_phone") or ""
        if phone and rel_phone and phone == rel_phone:
            self.add_error("relative_phone", "رقم قريب المتقدم يجب أن يختلف عن رقم المتقدم نفسه.")
        # لو قال عندي أقارب بالشركة ولم يذكر أسماء
        if data.get("has_relatives_in_company") and not data.get("relatives_in_company"):
            self.add_error("relatives_in_company", "برجاء ذكر أسماء الأقارب العاملين بالشركة.")
        # لو قال عندي أقارب/أصدقاء في شركات منافسة ولم يذكر التفاصيل
        if data.get("has_relatives_in_competitors") and not data.get("relatives_in_competitors"):
            self.add_error("relatives_in_competitors", "برجاء ذكر صلة القرابة والأماكن.")
        # لو قال عندي مشاكل صحية ولم يذكر التفاصيل
        if data.get("has_health_issues") and not data.get("health_issues_details"):
            self.add_error("health_issues_details", "برجاء ذكر تفاصيل المشاكل الصحية.")
        return data


class ApplicantEditFormHRHelp(forms.ModelForm):
    """الموظف العادي: يسمح له بتعديل البيانات الأساسية فقط (بدون تغيير الرقم القومي)"""
    national_id = forms.CharField(disabled=True, required=False, label="الرقم القومي")

    class Meta:
        model = Applicant
        fields = [
            "full_name", "national_id", "phone", "marital_status", "nationality",
            "gender", "religion", "military_status", "email",
            "relative_name", "relative_phone", "is_smoker", "vehicle_ownership", "photo",
            "edu_degree", "grad_year", "edu_institution", "specialization", "postgrad_study", "edu_grade",
            "job_applied", "job_code", "prev_applied",
            "has_relatives_in_company", "relatives_in_company",
            "has_relatives_in_competitors", "relatives_in_competitors",
            "has_health_issues", "health_issues_details",
        ]
        # متستعملش fields هنا تاني
        widgets = {
            "full_name": ApplicantCreateForm.Meta.widgets["full_name"],
            "national_id": ApplicantCreateForm.Meta.widgets["national_id"],
            "phone": ApplicantCreateForm.Meta.widgets["phone"],
            "marital_status": ApplicantCreateForm.Meta.widgets["marital_status"],
            "nationality": ApplicantCreateForm.Meta.widgets["nationality"],
            "gender": ApplicantCreateForm.Meta.widgets["gender"],
            "religion": ApplicantCreateForm.Meta.widgets["religion"],
            "military_status": ApplicantCreateForm.Meta.widgets["military_status"],
            "email": ApplicantCreateForm.Meta.widgets["email"],
            "relative_name": ApplicantCreateForm.Meta.widgets["relative_name"],
            "relative_phone": ApplicantCreateForm.Meta.widgets["relative_phone"],
            "is_smoker": ApplicantCreateForm.Meta.widgets["is_smoker"],
            "vehicle_ownership": ApplicantCreateForm.Meta.widgets["vehicle_ownership"],
            "photo": ApplicantCreateForm.Meta.widgets["photo"],
            "edu_degree": ApplicantCreateForm.Meta.widgets["edu_degree"],
            "grad_year": ApplicantCreateForm.Meta.widgets["grad_year"],
            "edu_institution": ApplicantCreateForm.Meta.widgets["edu_institution"],
            "specialization": ApplicantCreateForm.Meta.widgets["specialization"],
            "postgrad_study": ApplicantCreateForm.Meta.widgets["postgrad_study"],
            "edu_grade": ApplicantCreateForm.Meta.widgets["edu_grade"],
            "job_applied": ApplicantCreateForm.Meta.widgets["job_applied"],
            "job_code": ApplicantCreateForm.Meta.widgets["job_code"],
            "prev_applied": ApplicantCreateForm.Meta.widgets["prev_applied"],
            "has_relatives_in_company": ApplicantCreateForm.Meta.widgets["has_relatives_in_company"],
            "relatives_in_company": ApplicantCreateForm.Meta.widgets["relatives_in_company"],
            "has_relatives_in_competitors": ApplicantCreateForm.Meta.widgets["has_relatives_in_competitors"],
            "relatives_in_competitors": ApplicantCreateForm.Meta.widgets["relatives_in_competitors"],
            "has_health_issues": ApplicantCreateForm.Meta.widgets["has_health_issues"],
            "health_issues_details": ApplicantCreateForm.Meta.widgets["health_issues_details"],
        }




class ApplicantEditFormHR(forms.ModelForm):
    """HR: يقدر يعدل كل شيء بما فيهم الرقم القومي والحالة"""
    class Meta:
        model = Applicant
        fields = [
            "full_name", "national_id", "phone", "marital_status", "nationality",
            "gender", "religion", "military_status", "email",
            "relative_name", "relative_phone", "is_smoker", "vehicle_ownership", "photo",
            "edu_degree", "grad_year", "edu_institution", "specialization", "postgrad_study", "edu_grade",
            "job_applied", "job_code", "prev_applied",
            "has_relatives_in_company", "relatives_in_company",
            "has_relatives_in_competitors", "relatives_in_competitors",
            "has_health_issues", "health_issues_details",
            "status",
        ]
        widgets = ApplicantCreateForm.Meta.widgets


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = ApplicantExperience
        fields = ["employer", "job_title", "years", "salary", "reason_for_leaving"]
        widgets = {
            "employer":          forms.TextInput(attrs={"class": "form-control"}),
            "job_title":         forms.TextInput(attrs={"class": "form-control"}),
            "years":             forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "salary":            forms.NumberInput(attrs={"class": "form-control", "min": 1, "step": "0.50"}),
            "reason_for_leaving":forms.TextInput(attrs={"class": "form-control"}),
        }

# فورم سِت للخبرات (InlineFormSet) لاستخدامه مع فورم المتقدم
ExperienceFormSet = inlineformset_factory(
    parent_model=Applicant,
    model=ApplicantExperience,
    form=ExperienceForm,
    extra=1,
    can_delete=True
)

class AcceptedFollowUpForm(forms.ModelForm):
    class Meta:
        model = AcceptedApplicant
        fields = ["follow_up_note", "scheduled_date"]
        widgets = {
            "follow_up_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "scheduled_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }
