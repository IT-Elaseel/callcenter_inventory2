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

    class Meta:
        model = User
        fields = ["username", "email", "role", "branch"]

        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "اسم المستخدم"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "البريد الإلكتروني"
            }),
        }

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

        # تعيين الصلاحيات
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
        elif role == "callcenter":
            user.is_staff = True
            user.is_superuser = False
        else:  # branch
            user.is_staff = False
            user.is_superuser = False

        if commit:
            user.save()

            # إضافة للجروب
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)

            # تحديث UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
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

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "unit", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "اسم المنتج"}),
            "description": forms.Textarea(attrs={"class": "form-control", "placeholder": "الوصف", "rows": 2}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["name", "address", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "اسم الفرع"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "رقم التليفون"}),
        }
