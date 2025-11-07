from django import forms
from django.contrib.auth.models import User, Group
from django.conf import settings
from .models import Branch, UserProfile

class UserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="الدور"
    )

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="اختر الفرع"
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "البريد الإلكتروني"}),
        label="البريد الإلكتروني"
    )

    # ✅ الحقل الجديد
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "رقم الموبايل (مثال: 01012345678)"}),
        label="رقم الموبايل"
    )

    class Meta:
        model = User
        fields = ["username", "email", "phone", "role", "branch"]

    # ✅ التحقق من رقم الموبايل
    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("❌ رقم الموبايل يجب أن يحتوي على أرقام فقط.")
            if not phone.startswith("0"):
                raise forms.ValidationError("❌ رقم الموبايل يجب أن يبدأ بالرقم 0.")
            if len(phone) != 11:
                raise forms.ValidationError("❌ رقم الموبايل يجب أن يتكون من 11 رقم بالضبط.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        branch = cleaned_data.get("branch")
        if role == "branch" and not branch:
            self.add_error("branch", "يجب اختيار الفرع لموظف الفرع")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(settings.DEFAULT_USER_PASSWORD)
        role = self.cleaned_data["role"]

        # الصلاحيات
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
        elif role == "callcenter":
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False

        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.phone = self.cleaned_data.get("phone")  # ✅ حفظ رقم الموبايل
            if role == "branch":
                profile.branch = self.cleaned_data.get("branch")
            else:
                profile.branch = None
            profile.save()

        return user
#-------------------------------------------------------------------------------------------------------
from django.contrib.auth.forms import PasswordChangeForm
class ArabicPasswordChangeForm(PasswordChangeForm):
    error_messages = {
        'password_incorrect': "❌ كلمة المرور الحالية غير صحيحة.",
        'password_mismatch': "❌ كلمة المرور الجديدة وتأكيدها غير متطابقين.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = "كلمة المرور الحالية"
        self.fields['new_password1'].label = "كلمة المرور الجديدة"
        self.fields['new_password2'].label = "تأكيد كلمة المرور"

#-------------------------------------------------------------------------------------------------------
from .models import Category, Product, Branch
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "اسم القسم"}),
            "description": forms.Textarea(attrs={"class": "form-control", "placeholder": "الوصف", "rows": 2}),
        }
#-------------------------------------------------------------------------------------------------------
from django import forms
from .models import Product, Category, SecondCategory

class ProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="القسم الرئيسي",
        widget=forms.Select(attrs={"class": "form-select", "id": "mainCategory"})
    )
    second_category = forms.ModelChoiceField(
        queryset=SecondCategory.objects.none(),
        label="القسم الفرعي",
        widget=forms.Select(attrs={"class": "form-select", "id": "subCategory"})
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "price",
            "unit",
            "category",
            "second_category",
            "is_available",   # ✅ أضفناها هنا
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "اسم المنتج"}),
            "description": forms.Textarea(attrs={"class": "form-control", "placeholder": "الوصف", "rows": 2}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),  # ✅ خانة التوفر
        }
        labels = {
            "is_available": "متوفر؟",  # ✅ عنوان الحقل بالعربي
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ فلترة الأقسام الفرعية بناءً على القسم الرئيسي
        if "category" in self.data:
            try:
                category_id = int(self.data.get("category"))
                self.fields["second_category"].queryset = SecondCategory.objects.filter(main_category_id=category_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields["second_category"].queryset = SecondCategory.objects.filter(main_category=self.instance.category)
#-------------------------------------------------------------------------------------------------------
class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["name", "address", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "اسم الفرع"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "رقم التليفون"}),
        }
