from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
#-----------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)  # ✅ يتحدث تلقائي مع أي تعديل

    def __str__(self):
        return self.name
#-------------------------------------------------------------------
class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True
    )
    second_category = models.ForeignKey(
        'SecondCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True, verbose_name="متوفر")  # ✅ الجديد
    is_shwo = models.BooleanField(blank=True, null=True, verbose_name="Is Show")  # ✅ الحقل الجديد

    UNIT_CHOICES = [
        ("piece", "عدد"),
        ("kg", "كيلو"),
        ("service", "سرفيز"),
        ("tray", "صاج"),
    ]
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="piece")

    def __str__(self):
        main_cat = self.category.name if self.category else 'No Category'
        sub_cat = self.second_category.name if self.second_category else 'No Subcategory'
        return f"{self.name} ({main_cat} / {sub_cat})"
#-------------------------------------
class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)  # ✅ يتحدث تلقائي مع أي تعديل

    def __str__(self):
        return self.name
#-------------------------------------------------------------------
class Inventory(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        unique_together = ('branch', 'product')

    def __str__(self):
        return f"{self.product.name} - {self.branch.name} ({self.quantity})"
#-------------------------------------------------------------------
class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=11, null=True, blank=True)  # 👈 كده مش إجباري
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.id} - {self.name} ({self.phone})"
#-------------------------------------------------------------------
class Reservation(models.Model):
    DELIVERY_CHOICES = [
        ("pickup", "Pickup"),
        ("delivery", "Delivery"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="reservations", null=True, blank=True
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    reserved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations_created"
    )

    decision_at = models.DateTimeField(null=True, blank=True)

    branch_last_modified_at = models.DateTimeField(null=True, blank=True)
    branch_last_modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="branch_modified_reservations"
    )

    admin_last_modified_at = models.DateTimeField(null=True, blank=True)
    admin_last_modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_modified_reservations"
    )

    def __str__(self):
        return f"{self.customer} - {self.product} - {self.status}"

    def clean(self):
        super().clean()
        # تأمين: تأكد المنتج موجود قبل التحقق من وحدته
        unit = getattr(self.product, "unit", None)
        if unit == 'piece':
            # Decimal modulo works؛ إذا الباقي ≠ 0 فموجود كسور
            if (self.quantity % 1) != 0:
                raise ValidationError({"quantity": "هذا المنتج لا يقبل كسورًا. استخدم عددًا صحيحًا."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def confirm(self, user=None, is_admin=False):
        self.status = "confirmed"
        self.decision_at = self.decision_at or timezone.now()
        if user:
            if is_admin:
                self.admin_last_modified_at = timezone.now()
                self.admin_last_modified_by = user
            else:
                self.branch_last_modified_at = timezone.now()
                self.branch_last_modified_by = user
        self.save()

    def cancel(self, user=None, is_admin=False):
        self.status = "cancelled"
        self.decision_at = self.decision_at or timezone.now()
        if user:
            if is_admin:
                self.admin_last_modified_at = timezone.now()
                self.admin_last_modified_by = user
            else:
                self.branch_last_modified_at = timezone.now()
                self.branch_last_modified_by = user
        self.save()
#-------------------------------------------------------------------
class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('sale', 'Sale'),
        ('reservation', 'Reservation'),
        ('transfer_out', 'Transfer Out'),
        ('transfer_in', 'Transfer In'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions_from")
    to_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions_to")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#-----------------------------------------------------------
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('callcenter', 'Call Center'),
        ('branch', 'Branch'),
        ('control', 'Control'),  # ✨ الجديد
        ('production', 'إنتاج'),
        ('warehouse', 'مخزن'),
        ('quality', 'جودة'),
        ('maintenance', 'صيانة'),
        ('driver', 'سائق'),
        ('delivery', 'دليفري'),
        ("hr", "HR"),
        ("hr_help", "HR Help"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='branch')
     # ✨ الجديد
    last_password_reset = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
#-----------------------------------------------------------
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    from .models import UserProfile
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # لو مفيش profile، أنشئ واحد
        UserProfile.objects.get_or_create(user=instance)
#-------------------------------------------------------------------
class DailyRequest(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    category = models.ForeignKey("Category", on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order_number = models.CharField(max_length=50) # 🔑 رقم الطلبية
    is_confirmed = models.BooleanField(default=False)  # ✅ حالة التأكيد
    is_printed = models.BooleanField(default=False)
    printed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)  # ⏰ وقت التأكيد
    class Meta:
        verbose_name = "طلب يومي"
        verbose_name_plural = "الطلبات اليومية"

    def __str__(self):
        return f"{self.branch.name} - {self.product.name} ({self.quantity})"
#-------------------------------------------------------------------------------------------------------
from django.db import models

class OrderCounter(models.Model):
    current_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Current Order Number: {self.current_number}"
#-------------------------------------------------------------------------------------------------------
class SecondCategory(models.Model):
    main_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.main_category.name})"
#-------------------------------------------------------------------------------------------------------
class StandardRequest(models.Model):
    STAMP_TYPES = [
        ("order", "طلبية قياسية"),
        ("inventory", "تحديث مخزون"),
    ]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="standard_requests")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    default_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    stamp_type = models.CharField(max_length=20, choices=STAMP_TYPES, default="order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("branch", "product", "stamp_type")

    def __str__(self):
        return f"{self.branch.name} - {self.get_stamp_type_display()} - {self.product.name} ({self.default_quantity})"
# ===================== Production Requests =====================
from django.utils.timezone import localdate

class ProductionTemplate(models.Model):
    """
    المنتجات التي يحددها الكنترول لتظهر للـفروع يوميًا في نموذج طلب الإنتاج.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="production_templates")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product",)

    def __str__(self):
        return f"{self.product.name} ({'Active' if self.is_active else 'Inactive'})"


class ProductionRequest(models.Model):
    """
    الكميات اليومية التي يرسلها كل فرع للإنتاج.
    فرع × منتج × تاريخ (unique)؛ ويمكن تأكيد اليوم.
    """
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateField(default=localdate)  # تاريخ الطلب
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                   validators=[MinValueValidator(Decimal('0.00'))])
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("branch", "product", "date")

    def __str__(self):
        return f"{self.date} | {self.branch.name} | {self.product.name} = {self.quantity}"
