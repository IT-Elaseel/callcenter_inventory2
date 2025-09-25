from django.contrib import admin
from .models import Branch, Product, Inventory, Reservation, InventoryTransaction, Customer
from .models import Category
from .models import UserProfile

#-------------------------------------------------------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'phone')
    search_fields = ('name', 'address')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price')
    search_fields = ('name',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'branch', 'product', 'quantity')
    list_filter = ('branch', 'product')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_customer_name', 'get_customer_phone', 'product', 'branch', 'delivery_type', 'status', 'created_at')
    list_filter = ('delivery_type', 'status', 'branch')
    search_fields = ('customer__name', 'customer__phone')  # لاحظ التغيير هنا

    def get_customer_name(self, obj):
        return obj.customer.name
    get_customer_name.short_description = "Customer Name"

    def get_customer_phone(self, obj):
        return obj.customer.phone
    get_customer_phone.short_description = "Customer Phone"
#-------------------------------------------------------------------
@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'transaction_type', 'quantity', 'from_branch', 'to_branch', 'created_at')
    list_filter = ('transaction_type', 'from_branch', 'to_branch')
#------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
#-------------------------------------------------------------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "branch")
    list_filter = ("branch",)
#-------------------------------------------------------------------
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "address")
    search_fields = ("name", "phone")
