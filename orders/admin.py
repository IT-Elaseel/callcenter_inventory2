from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (Branch, Product, Inventory, Reservation, InventoryTransaction,Customer, Category, UserProfile, DailyRequest, SecondCategory)
# --------------------------------------------------------
# 📦 المنتجات
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category', 'second_category', 'is_available', 'updated_at')  # ✅ أضفنا الحالة
    list_filter = ('category', 'second_category', 'is_available')  # ✅ نقدر نفلتر بيها
    search_fields = ('name',)
    list_editable = ('is_available',)  # ✅ تعديل مباشر من الجدول




# --------------------------------------------------------
# 🧩 التصنيف الرئيسي
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'view_products_link')
    search_fields = ('name',)

    def view_products_link(self, obj):
        """زر يفتح المنتجات التابعة للتصنيف"""
        url = (
            reverse("admin:orders_product_changelist")
            + f"?category__id__exact={obj.id}"
        )
        return format_html(
            '<a class="button" href="{}" style="font-weight:bold;color:#0b6efd;">عرض المنتجات</a>', url
        )
    view_products_link.short_description = "المنتجات"


# --------------------------------------------------------
# 🧩 التصنيف الفرعي
@admin.register(SecondCategory)
class SecondCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'main_category', 'updated_at', 'view_products_link')
    search_fields = ('name', 'main_category__name')
    list_filter = ('main_category',)

    def view_products_link(self, obj):
        """زر يفتح المنتجات التابعة للتصنيف الفرعي"""
        url = (
            reverse("admin:orders_product_changelist")
            + f"?second_category__id__exact={obj.id}"
        )
        return format_html(
            '<a class="button" href="{}" style="font-weight:bold;color:#0b6efd;">عرض المنتجات</a>', url
        )
    view_products_link.short_description = "المنتجات"

#-------------------------------------------------------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'phone')
    search_fields = ('name', 'address')



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
#-------------------------------------------------------------------------------------------------------
@admin.register(DailyRequest)
class DailyRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "branch", "product", "quantity","get_unit", "order_number", "is_confirmed", "is_printed", "created_at")
    list_filter = ("branch", "is_confirmed", "is_printed", "created_at")
    search_fields = ("order_number", "product__name", "branch__name")
    def get_unit(self, obj):
        return obj.product.get_unit_display()
    get_unit.short_description = "الوحدة"
