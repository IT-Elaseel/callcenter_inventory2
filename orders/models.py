from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone

#-----------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

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
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    UNIT_CHOICES = [
        ("piece", "عدد"),
        ("kg", "كيلو"),
    ]
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="piece")  # 👈 الحقل الجديد

    def __str__(self):
        return f"{self.name} ({self.category.name if self.category else 'No Category'})"

#-------------------------------------
class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name
#-------------------------------------------------------------------
class Inventory(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

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
    quantity = models.PositiveIntegerField(default=1)
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)   # وقت إنشاء الحجز
    reserved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations_created"
    )  # مين عمل الحجز (كول سنتر أو أدمن)

    decision_at = models.DateTimeField(null=True, blank=True)  # أول قرار للفرع (تأكيد/إلغاء)

    # ⬇️ وقت آخر تعديل من الفرع
    branch_last_modified_at = models.DateTimeField(null=True, blank=True)
    branch_last_modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="branch_modified_reservations"
    )

    # ⬇️ وقت آخر تعديل من الأدمن
    admin_last_modified_at = models.DateTimeField(null=True, blank=True)
    admin_last_modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_modified_reservations"
    )

    def __str__(self):
        return f"{self.customer} - {self.product} - {self.status}"

    def confirm(self, user=None, is_admin=False):
        """تأكيد الحجز"""
        self.status = "confirmed"
        # أول قرار يتسجل في decision_at لو لسه فاضي
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
        """إلغاء الحجز"""
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
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

     # 👇 الجديد
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.product.name} ({self.quantity})"
#-----------------------------------------------------------
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('callcenter', 'Call Center'),
        ('branch', 'Branch'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='branch')

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
