 # 📌 Python Standard Library
from datetime import datetime
# 📌 Third-party Libraries
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
# 📌 Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse,HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, timedelta
# 📌 Local Application Imports
from .decorators import role_required
from .forms import CategoryForm, ProductForm, BranchForm, UserCreateForm, ArabicPasswordChangeForm
from .models import Category, Product, Inventory, Reservation, Branch, Customer, InventoryTransaction,DailyRequest
#------------------------------التحقق من المستخدم ادمن اول لا-------------------------------------
def is_admin(user):
    return (
        user.is_superuser
        or user.groups.filter(name="admin").exists()
        or (hasattr(user, "userprofile") and user.userprofile.role == "admin")
    )
def is_control(user):
    return user.is_authenticated and user.userprofile.role == "control"

#---------------------------------------------تصدير الحجوزات الى اكسيل----------------------------------------------------------
def export_reservations_excel(request, branch_id):
    reservations = Reservation.objects.filter(branch_id=branch_id).select_related("product", "branch", "customer").order_by("-created_at")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reservations"

    # Header
    ws.append(["ID", "Customer", "Phone", "Product", "Branch", "Delivery Type", "Status", "Created At"])

    # Data
    for r in reservations:
        ws.append([
            r.id,
            r.customer.name if r.customer else "",
            r.customer.phone if r.customer else "",
            r.product.name if r.product else "",
            r.branch.name if r.branch else "",
            r.get_delivery_type_display(),
            r.get_status_display(),
            r.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    # Response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="reservations_branch_{branch_id}.xlsx"'
    wb.save(response)
    return response
#-------------------------------------------------------------------------------------------------------
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_new_reservation(reservation, qty=1, user=None):
    """دالة موحدة لبث الحجز الجديد لجميع الفروع"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "branch_updates",
        {
            "type": "branch_update",
            "message": f"🆕 حجز جديد في فرع {reservation.branch.name} ({reservation.product.name} × {qty})",
            "reservation_id": reservation.id,
            "product_name": reservation.product.name,
            "quantity": qty,
            "customer_name": reservation.customer.name if reservation.customer else "-",
            "customer_phone": reservation.customer.phone if reservation.customer and reservation.customer.phone else "-",
            "created_at": str(reservation.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            "reserved_by": user.username if user else "-",
        }
    )
#-------------------------------------------------------------
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Product, Branch, Category, Inventory, Reservation, Customer

@login_required
def callcenter(request):
    query = request.GET.get("q")
    category_id = request.GET.get("category")

    inventories = Inventory.objects.select_related("product", "branch", "product__category")
    categories = Category.objects.all()

    if query:
        inventories = inventories.filter(product__name__icontains=query)
    if category_id:
        inventories = inventories.filter(product__category_id=category_id)

    # معالجة POST (يُتوقع AJAX أو POST عادي)
    if request.method == "POST":
        try:
            product_id = request.POST.get("product_id")
            branch_id = request.POST.get("branch_id")
            customer_name = (request.POST.get("customer_name") or "").strip()
            customer_phone = (request.POST.get("customer_phone") or "").strip()
            delivery_type = request.POST.get("delivery_type")
            try:
                qty = int(request.POST.get("quantity", 1))
            except (TypeError, ValueError):
                qty = 1

            # تحقق أساسي من وجود المنتج والفرع
            try:
                product = Product.objects.get(id=product_id)
                branch = Branch.objects.get(id=branch_id)
            except (Product.DoesNotExist, Branch.DoesNotExist):
                return JsonResponse({"success": False, "message": "❌ المنتج أو الفرع غير موجود."}, status=400)

            if qty < 1:
                return JsonResponse({"success": False, "message": "❌ الكمية لازم تكون رقم موجب."}, status=400)

            # معاملة لضمان سلامة التحديث على المخزون
            with transaction.atomic():
                inventory = Inventory.objects.select_for_update().get(product=product, branch=branch)

                if inventory.quantity < qty:
                    return JsonResponse({"success": False, "message": f"❌ الكمية المطلوبة غير متوفرة (المتاح {inventory.quantity})."}, status=400)

                # **هنا المهم**: لا نبحث عن عميل حسب الهاتف.
                # إذا دخلت اسم أو رقم → نُنشئ سجل عميل جديد. لو لم تدخل أى بيانات → نترك customer = None
                customer = None
                if customer_name or customer_phone:
                    customer = Customer.objects.create(
                        name=customer_name if customer_name else "عميل مؤقت",
                        phone=customer_phone if customer_phone else ""
                    )

                reservation = Reservation.objects.create(
                    customer=customer,
                    product=product,
                    branch=branch,
                    delivery_type=delivery_type if delivery_type else "pickup",
                    status="pending",
                    quantity=qty,
                    reserved_by=request.user if request.user.is_authenticated else None,
                )

                # خصم الكمية وحفظ
                inventory.quantity -= qty
                inventory.save()

            # إرسال تحديثات WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "callcenter_updates",
                {
                    "type": "callcenter_update",
                    "product_id": product.id,
                    "branch_id": branch.id,
                    "branch_name": branch.name,
                    "new_qty": inventory.quantity,
                    "message": f"📦 تم تحديث {product.name} في فرع {branch.name} إلى {inventory.quantity}",
                },
            )

            async_to_sync(channel_layer.group_send)(
                "branch_updates",
                {
                    "type": "branch_update",
                    "message": f"🆕 حجز جديد ({product.name} × {qty})",
                    "reservation_id": reservation.id,
                    "product_name": product.name,
                    "quantity": qty,
                    "customer_name": customer.name if customer else "-",
                    "customer_phone": customer.phone if customer else "-",
                    "created_at": timezone.localtime(reservation.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                    "reserved_by": request.user.username,
                },
            )
            # ✅ إشعار صفحة الحجوزات
            async_to_sync(channel_layer.group_send)(
                "reservations_updates",
                {
                    "type": "reservations_update",          # ← لازم يطابق دالة consumer
                    "action": "new",
                    "message": f"🆕 تم إضافة حجز جديد #{reservation.id}",
                    "reservation_id": reservation.id,
                    "product_name": product.name,
                    "quantity": qty,
                    "customer_name": customer.name if customer else "-",
                    "customer_phone": customer.phone if customer else "-",
                    "branch_name": branch.name,
                    "delivery_type": reservation.get_delivery_type_display(),
                    "status": reservation.get_status_display(),
                    "created_at": timezone.localtime(reservation.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                    "decision_at": "",  # مفيش قرار لسه
                    "reserved_by": request.user.username,
                },
            )

            return JsonResponse({
                "success": True,
                "message": f"✅ تم حجز {product.name}" + (f" للعميل {customer.name}" if customer else ""),
                "new_qty": inventory.quantity,
            })

        except Inventory.DoesNotExist:
            return JsonResponse({"success": False, "message": "❌ لا يوجد مخزون لهذا المنتج في الفرع المختار."}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"❌ خطأ داخلي: {str(e)}"}, status=500)

    # GET → عرض الصفحة
    return render(
        request,
        "orders/callcenter.html",
        {
            "categories": categories,
            "inventories": inventories,
            "selected_category": int(category_id) if category_id else None,
            "query": query,
        },
    )

#----------------------------قايمه الحجوزات---------------------------------
@login_required
def reservations_list(request):
    from datetime import date as dt_date
    today = timezone.localdate()

    # القيم من GET
    start_raw = request.GET.get("start_date", "")
    end_raw   = request.GET.get("end_date", "")
    query     = request.GET.get("q", "").strip()

    # الافتراضي: النهارده
    if not start_raw or not end_raw:
        start_date = end_date = today
        start_raw, end_raw = today.isoformat(), today.isoformat()
    else:
        try:
            start_date = dt_date.fromisoformat(start_raw)
            end_date   = dt_date.fromisoformat(end_raw)
        except ValueError:
            messages.error(request, "⚠️ صيغة التاريخ غير صحيحة.")
            start_date = end_date = today
            start_raw, end_raw = today.isoformat(), today.isoformat()

    # فلترة الحجوزات
    profile = getattr(request.user, "userprofile", None)
    reservations = Reservation.objects.all()

    if profile and profile.role == "branch":
        branch = profile.branch
        reservations = reservations.filter(branch=branch)

    reservations = reservations.filter(created_at__date__range=[start_date, end_date])

    # 🔎 البحث باسم العميل أو رقم تليفونه
    if query:
        reservations = reservations.filter(
            Q(customer__name__icontains=query) |
            Q(customer__phone__icontains=query)
        )

    reservations = reservations.select_related(
        "product", "branch", "customer"
    ).order_by("-created_at")

    return render(
        request,
        "orders/reservations.html",
        {
            "reservations": reservations,
            "user_role": profile.role if profile else None,
            "start_date": start_raw,
            "end_date": end_raw,
            "query": query,
            "today": today,  # ← أضفها
        },
    )
#-------------------------------------------------------------
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Reservation


def update_reservation_status(request, res_id, status):
    reservation = get_object_or_404(Reservation, id=res_id)
    profile = getattr(request.user, "userprofile", None)
    is_admin = profile and profile.role == "admin"

    # ✅ تحديث الحالة في قاعدة البيانات
    if status == "confirmed":
        reservation.confirm(user=request.user, is_admin=is_admin)
        msg = f"✅ تم تأكيد الحجز للعميل {reservation.customer}"
        messages.success(request, msg)
    elif status == "cancelled":
        reservation.cancel(user=request.user, is_admin=is_admin)
        msg = f"❌ تم إلغاء الحجز للعميل {reservation.customer}"
        messages.warning(request, msg)
    else:
        messages.error(request, "⚠️ حالة غير معروفة")
        return redirect(request.META.get("HTTP_REFERER", "branch_dashboard"))

    # ============================================================
    # 🔄 إرسال إشعار لتحديث صفحة الحجوزات عبر WebSocket
    # ============================================================
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "reservations_updates",
        {
            "type": "reservations_update",      # ← لازم يطابق اسم الدالة في consumer
            "action": "status_change",          # نميّز نوع التحديث
            "message": msg,
            "reservation_id": reservation.id,
            "customer_name": reservation.customer.name if reservation.customer else "-",
            "customer_phone": reservation.customer.phone if reservation.customer else "-",
            "product_name": reservation.product.name,
            "quantity": reservation.quantity,
            "branch_name": reservation.branch.name,
            "delivery_type": reservation.get_delivery_type_display(),
            "status": reservation.get_status_display(),
            "created_at": timezone.localtime(reservation.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            "decision_at": timezone.localtime(reservation.decision_at).strftime('%Y-%m-%d %H:%M:%S') if reservation.decision_at else "",
            "reserved_by": reservation.reserved_by.username if reservation.reserved_by else "-",
        },
    )

    return redirect(request.META.get("HTTP_REFERER", "branch_dashboard"))
#-------------------------------------------------------------
@login_required
@role_required(["admin"])
def reports(request):
    from datetime import date as dt_date
    today = timezone.localdate()


    start_raw = request.GET.get("start_date", "")
    end_raw   = request.GET.get("end_date", "")

    # لو مفيش قيم جاية من الفورم → الافتراضي = اليوم
    if not start_raw or not end_raw:
        start_date = end_date = today
        start_raw, end_raw = today.isoformat(), today.isoformat()
    else:
        # نحاول نفكّر التواريخ (ونتحقق من ترتيبها)
        try:
            start_date = dt_date.fromisoformat(start_raw)
            end_date   = dt_date.fromisoformat(end_raw)
        except ValueError:
            messages.error(request, "⚠️ صيغة التاريخ غير صحيحة.")
            return render(
                request,
                "orders/reports.html",
                {
                    "stats": {"total": 0, "confirmed": 0, "pending": 0, "cancelled": 0},
                    "top_products": [],
                    "top_branches": [],
                    "start_date": start_raw,
                    "end_date": end_raw,
                },
            )

        if start_date > end_date:
            messages.error(request, "⚠️ تاريخ البداية لا يجوز أن يكون بعد تاريخ النهاية.")
            return render(
                request,
                "orders/reports.html",
                {
                    "stats": {"total": 0, "confirmed": 0, "pending": 0, "cancelled": 0},
                    "top_products": [],
                    "top_branches": [],
                    "start_date": start_raw,
                    "end_date": end_raw,
                },
            )
    # لو وصلنا هنا يبقى عندنا start_date/end_date صالحين
    reservations = Reservation.objects.filter(created_at__date__range=[start_date, end_date])

    stats = {
        "total": reservations.count(),
        "confirmed": reservations.filter(status="confirmed").count(),
        "pending": reservations.filter(status="pending").count(),
        "cancelled": reservations.filter(status="cancelled").count(),
    }
    top_products = (
        reservations.values("product__name").annotate(total=Count("id")).order_by("-total")[:5]
    )

    top_branches = (
        reservations.values("branch__name").annotate(total=Count("id")).order_by("-total")[:5]
    )

    return render(
        request,
        "orders/reports.html",
        {
            "stats": stats,
            "top_products": top_products,
            "top_branches": top_branches,
            "start_date": start_raw,  # نبعث القيم كـ string عشان input يفضل ثابت
            "end_date": end_raw,
        },
    )
#-------------------------------------------------------------
@login_required
@role_required(["admin", "branch"])
def export_reports_excel(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    reservations = Reservation.objects.all()
    if start_date:
        reservations = reservations.filter(created_at__gte=start_date)
    if end_date:
        reservations = reservations.filter(created_at__lte=end_date)

    # ✅ الإحصائيات
    stats = {
        "total": reservations.count(),
        "confirmed": reservations.filter(status="confirmed").count(),
        "pending": reservations.filter(status="pending").count(),
        "cancelled": reservations.filter(status="cancelled").count(),
    }

    # ✅ أكثر المنتجات
    top_products = (
        reservations.values("product__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # ✅ أفضل الفروع
    top_branches = (
        reservations.values("branch__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # ✅ إنشاء ملف Excel
    wb = openpyxl.Workbook()

    # Sheet 1: Stats
    ws1 = wb.active
    ws1.title = "Stats"
    ws1.append(["إحصائية", "القيمة"])
    ws1.append(["إجمالي الحجوزات", stats["total"]])
    ws1.append(["✅ Confirmed", stats["confirmed"]])
    ws1.append(["🕒 Pending", stats["pending"]])
    ws1.append(["❌ Cancelled", stats["cancelled"]])

    # Sheet 2: Top Products
    ws2 = wb.create_sheet("Top Products")
    ws2.append(["Product", "Total Reservations"])
    for p in top_products:
        ws2.append([p["product__name"], p["total"]])

    # Sheet 3: Top Branches
    ws3 = wb.create_sheet("Top Branches")
    ws3.append(["Branch", "Total Reservations"])
    for b in top_branches:
        ws3.append([b["branch__name"], b["total"]])

    # ✅ Response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reports.xlsx"'
    wb.save(response)
    return response
#-------------------------------------------------------------
@login_required
@role_required(["branch", "admin", "callcenter"])
def branch_dashboard(request):
    profile = getattr(request.user, "userprofile", None)

    # 👇 لسsو المستخدم كول سنتر → يروح على الكول سنتر داشبورد
    if profile and profile.role == "callcenter":
        return redirect("callcenter_dashboard")

    # لو Admin → يقدر يختار أي فرع من Dropdown
    if request.user.is_superuser or (profile and profile.role == "admin"):
        selected_branch_id = request.GET.get("branch")
        branches = Branch.objects.all()

        if selected_branch_id:
            branch = Branch.objects.get(id=selected_branch_id)
            inventories = Inventory.objects.filter(branch=branch).select_related(
                "product", "product__category"
            )
            reservations = Reservation.objects.filter(branch=branch).select_related("product")
        else:
            branch = None
            inventories = Inventory.objects.none()
            reservations = Reservation.objects.none()

        return render(
            request,
            "orders/branch_dashboard.html",
            {
                "branch": branch,
                "inventories": inventories,
                "reservations": reservations,
                "is_admin": True,
                "branches": branches,
                "selected_branch_id": selected_branch_id,
            },
        )

    # لو موظف فرع عادي
    branch = profile.branch if profile else None
    if not branch:
        return render(request, "orders/branch_no_access.html")

    # تحديث الكمية (لموظف الفرع فقط)
    if request.method == "POST":
        inv_id = request.POST.get("inventory_id")
        qty = request.POST.get("quantity")
        if inv_id and qty is not None:
            inv = Inventory.objects.get(id=inv_id, branch=branch)
            inv.quantity = int(qty)
            inv.save()

    inventories = Inventory.objects.filter(branch=branch).select_related(
        "product", "product__category"
    )
    reservations = Reservation.objects.filter(branch=branch).select_related("product")

    return render(
        request,
        "orders/branch_dashboard.html",
        {
            "branch": branch,
            "inventories": inventories,
            "reservations": reservations,
            "is_admin": False,
        },
    )
#-------------------------------------------------------------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Redirect based on role
            profile = getattr(user, "userprofile", None)
            if profile:
                if profile.role == "admin":
                    return redirect("reports")
                elif profile.role == "callcenter":
                    return redirect("callcenter_dashboard")
                elif profile.role == "branch":
                    return redirect("branch_dashboard")
                elif profile.role == "control":   # ✅ جديد
                    return redirect("control_requests")
            return redirect("home")
        else:
            return render(request, "orders/login.html", {"error": "❌ بيانات الدخول غير صحيحة"})
    return render(request, "orders/login.html")
#-------------------------------------------------------------------
def logout_view(request):
    logout(request)
    return redirect("login")
#-------------------------------------------------------------------
def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")

    profile = getattr(request.user, "userprofile", None)

    if profile:
        if profile.role == "admin":
            return redirect("reports")
        elif profile.role == "callcenter":
            return redirect("callcenter")
        elif profile.role == "branch":
            return redirect("branch_dashboard")
        elif profile.role == "control":   # ✅ جديد
            return redirect("control_requests")
        elif profile.role == "hr":
            return redirect("hr:hr_dashboard")   # 👈 لسه نعملها في الـ hr app
        elif profile.role == "hr_help":
            return redirect("hr:hr_help_dashboard")  # 👈 برضو في hr app


    # fallback لو مفيش role
    return redirect("login")
#-------------------------------------------------------------------
@login_required
@role_required(["branch", "admin"])
def export_inventory_excel(request, branch_id=None):
    profile = getattr(request.user, "userprofile", None)

    # 🎯 لو Admin أو Superuser
    if request.user.is_superuser or (profile and profile.role == "admin"):
        if not branch_id:
            return HttpResponse("🚫 لازم تحدد فرع في الرابط", status=400)
        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            return HttpResponse("🚫 الفرع المطلوب غير موجود", status=404)

    # 🎯 لو موظف فرع
    elif profile and profile.role == "branch":
        branch = profile.branch
        if not branch:
            return HttpResponse("🚫 لا يوجد فرع مربوط بحسابك", status=400)

    else:
        return HttpResponse("🚫 غير مصرح لك", status=403)

    # ✅ جلب البيانات
    inventories = Inventory.objects.filter(branch=branch).select_related("product", "product__category")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{branch.name} Inventory"

    # Header
    headers = ["Product", "Category", "Quantity", "Price"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    alignment = Alignment(horizontal="center", vertical="center")

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = alignment

    # Data rows
    for inv in inventories:
        ws.append([
            inv.product.name,
            inv.product.category.name if inv.product.category else "",
            inv.quantity,
            inv.product.price,
        ])

    # Auto-fit columns + borders
    thin_border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
            cell.alignment = alignment
            cell.border = thin_border
        ws.column_dimensions[column].width = max_length + 2

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{branch.name}_inventory.xlsx"'
    wb.save(response)
    return response
#-------------------------------------------------------------------
@login_required
@role_required(["admin", "callcenter"])
def customers_list(request):
    query = request.GET.get("q")
    customers = Customer.objects.all()

    if query:
        customers = customers.filter(name__icontains=query) | customers.filter(phone__icontains=query)

    # ✅ Pagination: 10 عملاء في كل صفحة
    paginator = Paginator(customers, 10)
    page_number = request.GET.get("page")
    customers_page = paginator.get_page(page_number)

    return render(request, "orders/customers_list.html", {
        "customers": customers_page,
    })
#-------------------------------------------------------------------
def landing(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("root_redirect")  # بعد اللوجن يوديه حسب الـ role
    else:
        form = AuthenticationForm()

    return render(request, "orders/landing.html", {"form": form})
#-------------------------------------------------------------------------------------------------------
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
@login_required
@role_required(["branch"])
def update_inventory(request):
    profile = getattr(request.user, "userprofile", None)
    branch = profile.branch if profile else None

    if not branch:
        return render(
            request,
            "orders/no_permission.html",
            {
                "error_message": "🚫 لا يوجد فرع مربوط بحسابك. من فضلك تواصل مع مدير النظام لو محتاج صلاحية"
            },
            status=403
        )

    # 🟢 POST = تحديث الكمية
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        qty = request.POST.get("quantity")

        if product_id and qty:
            product = Product.objects.get(id=product_id)
            qty = int(qty)
            if qty < 1:
                return JsonResponse({
                    "success": False,
                    "message": "❌ أقل كمية مسموح بها هي 1"
                })
            inventory, created = Inventory.objects.get_or_create(branch=branch, product=product)
            inventory.quantity = qty
            inventory.save()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "callcenter_updates",
                {
                    "type": "callcenter_update",
                    "product_id": product.id,
                    "branch_id": branch.id,
                    "branch_name": branch.name,
                    "new_qty": inventory.quantity,
                    "message": f"📦 تم تحديث {product.name} في فرع {branch.name} إلى {inventory.quantity}",
                }
            )
            InventoryTransaction.objects.create(
                product=product,
                from_branch=None,
                to_branch=branch,
                quantity=qty,
                transaction_type="transfer_in",
                added_by=request.user
            )

            # ✅ استجابة JSON عشان الـ Ajax
            return JsonResponse({
                "success": True,
                "message": f"✅ تمت إضافة {qty} لـ {product.name}. الكمية الجديدة: {inventory.quantity}",
                "new_qty": inventory.quantity
            })

        return JsonResponse({"success": False, "message": "❌ بيانات غير صحيحة"})

    # 🟢 GET = عرض الصفحة
    categories = Category.objects.all()
    selected_category = request.GET.get("category")

    if selected_category == "":  # اختار "كل الأقسام"
        request.session["selected_category"] = None
        selected_category = None
    elif selected_category is not None:  # اختار قسم معين
        request.session["selected_category"] = selected_category
    else:  # مفيش باراميتر في GET → استرجع من السيشن
        selected_category = request.session.get("selected_category")

    products = Product.objects.all()
    if selected_category:
        products = products.filter(category_id=selected_category)

    inventories = Inventory.objects.filter(branch=branch).select_related("product")

    return render(
        request,
        "orders/update_inventory.html",
        {
            "categories": categories,
            "selected_category": int(selected_category) if selected_category else None,
            "products": products,
            "inventories": inventories,
             "branch": branch,   # 👈 أضفت الفرع هنا
        },
    )

#-------------------------------------------------------------------------------------------------------
@login_required
@role_required(["branch", "admin"])
def inventory_transactions(request):
    from datetime import date as dt_date

    profile = getattr(request.user, "userprofile", None)
    branch = profile.branch if profile else None

    # استلام باراميترز الفلترة
    start_raw = request.GET.get("start_date", "")
    end_raw   = request.GET.get("end_date", "")
    category_id = request.GET.get("category")
    query = request.GET.get("q", "").strip()
    branch_filter = request.GET.get("branch")  # للأدمن

    today = timezone.localdate()

    # الافتراضي: النهارده
    if not start_raw or not end_raw:
        start_date = end_date = today
        start_raw, end_raw = today.isoformat(), today.isoformat()
    else:
        try:
            start_date = dt_date.fromisoformat(start_raw)
            end_date   = dt_date.fromisoformat(end_raw)
        # 🛑 تأمين: ماينفعش تاريخ النهاية يعدي النهاردة
            if end_date > today:
                end_date = today
                end_raw = today.isoformat()

        except ValueError:
            start_date = end_date = today
            start_raw, end_raw = today.isoformat(), today.isoformat()
            messages.error(request, "⚠️ صيغة التاريخ غير صحيحة.")


    # 🟢 لو المستخدم أدمن
    if request.user.is_superuser or request.user.groups.filter(name="admin").exists():
        transactions = InventoryTransaction.objects.filter(
            transaction_type="transfer_in"
        ).select_related("product", "added_by", "to_branch").order_by("-created_at")

        # فلترة بالفرع (لو متبعتش فرع = كل الفروع)
        if branch_filter and branch_filter != "all":
            transactions = transactions.filter(to_branch_id=branch_filter)

        branches = Branch.objects.all()

    else:
        # 🟢 موظف فرع
        if not branch:
            return render(request, "orders/branch_no_access.html")

        transactions = InventoryTransaction.objects.filter(
            to_branch=branch, transaction_type="transfer_in"
        ).select_related("product", "added_by").order_by("-created_at")

        branches = None  # الفرع ثابت

    # فلترة بالتاريخ
    transactions = transactions.filter(created_at__date__range=[start_date, end_date])

    # فلترة بالقسم
    if category_id:
        transactions = transactions.filter(product__category_id=category_id)

    # فلترة بالبحث (اسم المنتج)
    if query:
        transactions = transactions.filter(product__name__icontains=query)

    categories = Category.objects.all()

    return render(
        request,
        "orders/inventory_transactions.html",
        {
            "transactions": transactions,
            "branch": branch,
            "branches": branches,   # للأدمن فقط
            "categories": categories,
            "selected_category": int(category_id) if category_id else None,
            "selected_branch": int(branch_filter) if branch_filter and branch_filter != "all" else None,
            "start_date": start_raw,
            "end_date": end_raw,
            "query": query,
            "today": today,   # ✅ علشان نستخدمه في max
        },
    )
#-------------------------------------------------------------------------------------------------------
@login_required
@role_required(["branch", "admin", "callcenter"])
def branch_inventory(request):
    profile = getattr(request.user, "userprofile", None)
    branch = profile.branch if profile else None
    role = profile.role if profile else None

    # ⬅️ لو المستخدم مالوش فرع وكان دوره فرع (بس) → امنعه
    if role == "branch" and not branch:
        return render(request, "orders/branch_no_access.html")

    # ⬅️ جلب باراميتر القسم والبحث والفرع من GET
    category_id = request.GET.get("category")
    query = request.GET.get("q", "").strip()
    branch_filter = request.GET.get("branch")

    # 🟢 لو المستخدم أدمن أو كول سنتر أو سوبر يوزر → يشوف كل الفروع
    if (
        request.user.is_superuser
        or role == "admin"
        or role == "callcenter"
    ):
        inventories = Inventory.objects.select_related("product", "product__category", "branch")
        if branch_filter and branch_filter != "all":
            inventories = inventories.filter(branch_id=branch_filter)

        branches = Branch.objects.all()
        branch_context = None

    else:
        # 🟢 موظف فرع → يجيب فرعه فقط
        inventories = Inventory.objects.filter(branch=branch).select_related(
            "product", "product__category"
        )
        branches = None
        branch_context = branch

    # ⬅️ فلترة بالقسم
    if category_id:
        inventories = inventories.filter(product__category_id=category_id)

    # ⬅️ فلترة بالبحث
    if query:
        inventories = inventories.filter(product__name__icontains=query)

    categories = Category.objects.all()

    return render(
        request,
        "orders/branch_inventory.html",
        {
            "branch": branch_context,
            "inventories": inventories,
            "categories": categories,
            "branches": branches,
            "selected_category": int(category_id) if category_id else None,
            "selected_branch": int(branch_filter) if branch_filter and branch_filter != "all" else None,
            "query": query,
        },
    )
#-------------------------------------------------------------------------------------------------------
@login_required
@role_required(["callcenter", "admin"])
def use_customer(request, customer_id):
    """
    دالة لاختيار عميل موجود (مثلاً لو فيه تضارب أرقام)
    """
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        messages.error(request, "❌ العميل غير موجود.")
        return redirect("customers_list")

    # ممكن نخزن الـ id في session مؤقتًا عشان نستخدمه في الحجز القادم
    request.session["selected_customer_id"] = customer.id
    messages.success(request, f"✅ تم اختيار العميل {customer.name} ({customer.phone})")

    return redirect("customers_list")
#-------------------------------------------------------------------------------------------------------
@login_required
@role_required(["callcenter", "admin"])
def add_customer(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address = request.POST.get("address", "")

        customer = Customer.objects.create(name=name, phone=phone, address=address)
        messages.success(request, f"✅ تم إضافة العميل {customer.name} ({customer.phone})")
        return redirect("customers_list")

    return render(request, "orders/add_customer.html")
#-------------------------------------------------------------------------------------------------------
@login_required
@role_required(["callcenter"])
def resolve_conflict(request):
    if request.method == "POST":
        action = request.POST.get("action")
        phone = request.POST.get("phone")
        name = request.POST.get("name")
        product_id = request.POST.get("product_id")
        branch_id = request.POST.get("branch_id")
        delivery_type = request.POST.get("delivery_type")
        qty = int(request.POST.get("quantity", 1))

        product = Product.objects.get(id=product_id)
        branch = Branch.objects.get(id=branch_id)

        # لو العميل موجود
        customer = None
        if action == "use_old":
            customer = Customer.objects.filter(phone=phone).first()

        elif action == "new_customer":
            customer = Customer.objects.create(name=name, phone=phone)

        if customer:
            try:
                inventory = Inventory.objects.get(product=product, branch=branch)
                if inventory.quantity >= qty:
                    Reservation.objects.create(
                        customer=customer,
                        product=product,
                        branch=branch,
                        delivery_type=delivery_type,
                        status="pending",
                         quantity=qty,
                        reserved_by=request.user if request.user.is_authenticated else None,
                    )
                    inventory.quantity -= qty
                    inventory.save()
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "callcenter_updates",
                        {
                            "type": "callcenter_update",
                            "product_id": product.id,
                            "branch_id": branch.id,
                            "branch_name": branch.name,
                            "new_qty": inventory.quantity,
                            "message": f"📦 تم تحديث {product.name} في فرع {branch.name} إلى {inventory.quantity}",
                        }
                    )

                    messages.success(
                        request,
                        f"✅ تم حجز {qty} {product.get_unit_display()} من {product.name} للعميل {customer.name}"
                    )
                else:
                    messages.error(request, f"❌ الكمية غير متوفرة من {product.name} في فرع {branch.name}")
            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء الحجز: {str(e)}")

        return redirect("callcenter_dashboard")

    return redirect("callcenter_dashboard")
#-------------------------------------------------------------------------------------------------------
# شرط يفتح الصفحة بس لو هو أدمن
@login_required
@user_passes_test(is_admin)
def add_user_view(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("add_user")  # يرجع لنفس الصفحة بعد الحفظ
    else:
        form = UserCreateForm()
    return render(request, "orders/add_user.html", {"form": form})
#-------------------------------------------------------------------------------------------------------
@login_required
def change_password(request):
    form = ArabicPasswordChangeForm(user=request.user, data=request.POST or None)
    success_message = None
    show_modal = False

    if request.method == "POST":
        show_modal = True  # 👈 افتح المودال دايمًا بعد POST
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            success_message = "✅ تم تغيير كلمة المرور بنجاح."
            form = ArabicPasswordChangeForm(user=request.user)  # reset للفورم بعد النجاح

        return render(request, "orders/home.html", {   # غير reports.html لصفحتك
            "password_form": form,
            "success_message": success_message,
            "show_modal": show_modal,
        })

    return redirect("home")
#-------------------------------------------------------------------------------------------------------
@login_required
@user_passes_test(is_admin)
def manage_data(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    branches = Branch.objects.all()

    success_message = None

    # دايمًا اعمل تعريف أولي للفورمات
    cat_form = CategoryForm(prefix="cat")
    prod_form = ProductForm(prefix="prod")
    branch_form = BranchForm(prefix="branch")

    if request.method == "POST":
        if "add_category" in request.POST:
            cat_form = CategoryForm(request.POST, prefix="cat")
            if cat_form.is_valid():
                cat_form.save()
                success_message = "✅ تم إضافة القسم بنجاح"
                cat_form = CategoryForm(prefix="cat")  # reset

        elif "add_product" in request.POST:
            prod_form = ProductForm(request.POST, prefix="prod")
            if prod_form.is_valid():
                prod_form.save()
                success_message = "✅ تم إضافة المنتج بنجاح"
                prod_form = ProductForm(prefix="prod")

        elif "add_branch" in request.POST:
            branch_form = BranchForm(request.POST, prefix="branch")
            if branch_form.is_valid():
                branch_form.save()
                success_message = "✅ تم إضافة الفرع بنجاح"
                branch_form = BranchForm(prefix="branch")

    return render(request, "orders/manage_data.html", {
        "cat_form": cat_form,
        "prod_form": prod_form,
        "branch_form": branch_form,
        "categories": categories,
        "products": products,
        "branches": branches,
        "success_message": success_message,
    })
#-------------------------------------------------------------------------------------------------------
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.all()

    # ✅ فلترة بالاسم
    username = request.GET.get("username", "")
    if username:
        users = users.filter(username__icontains=username)

    # ✅ فلترة بالنوع (role)
    role = request.GET.get("role", "")
    if role:
        users = users.filter(userprofile__role=role)

    # ✅ POST (حذف أو إعادة تعيين باسورد)
    if request.method == "POST":
        if "delete_user" in request.POST:
            user_id = request.POST.get("delete_user")
            User.objects.filter(id=user_id).delete()

        elif "reset_password" in request.POST:
            user_id = request.POST.get("reset_password")
            u = User.objects.get(id=user_id)
            u.set_password(settings.DEFAULT_USER_PASSWORD)
            u.save()

            if hasattr(u, "userprofile"):
                u.userprofile.last_password_reset = timezone.now()
                u.userprofile.save()

        # ✅ بعد أي أكشن: رجع لنفس الرابط بالفلترة الحالية
        return redirect(request.get_full_path())

    return render(request, "orders/manage_users.html", {
        "users": users,
        "username": username,
        "role": role,
    })
#-------------------------------------------------------------------------------------------------------
from django.urls import reverse
from urllib.parse import urlencode

@login_required
@user_passes_test(is_admin)
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    success = False

    # ✅ نحتفظ بالـ query string (عشان نرجع بنفس الفلاتر)
    query_params = request.GET.dict()
    query_string = f"?{urlencode(query_params)}" if query_params else ""

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            # ✅ بعد الحفظ رجع لنفس الصفحة مع الفلاتر
            return redirect(reverse("view_data") + query_string)
    else:
        form = CategoryForm(instance=category)

    return render(request, "orders/edit_item.html", {
        "form": form,
        "title": "✏️ تعديل قسم",
        "success": success,
        "redirect_url": reverse("view_data") + query_string,
    })
#-------------------------------------------------------------------------------------------------------
from django.urls import reverse
from urllib.parse import urlencode

@login_required
@user_passes_test(is_admin)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    success = False

    # ✅ نحتفظ بالـ query string
    query_params = request.GET.dict()
    query_string = f"?{urlencode(query_params)}" if query_params else ""

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            # ✅ بعد الحفظ رجع لنفس الصفحة مع الفلاتر
            return redirect(reverse("view_data") + query_string)
    else:
        form = ProductForm(instance=product)

    return render(request, "orders/edit_item.html", {
        "form": form,
        "title": "✏️ تعديل منتج",
        "success": success,
        "redirect_url": reverse("view_data") + query_string,
    })
#-------------------------------------------------------------------------------------------------------
from django.urls import reverse
from urllib.parse import urlencode

@login_required
@user_passes_test(is_admin)
def edit_branch(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    success = False

    query_params = request.GET.dict()
    query_string = f"?{urlencode(query_params)}" if query_params else ""

    if request.method == "POST":
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            # ✅ استخدم reverse
            return redirect(reverse("view_data") + query_string)
    else:
        form = BranchForm(instance=branch)

    return render(request, "orders/edit_item.html", {
        "form": form,
        "title": "✏️ تعديل فرع",
        "success": success,
        "redirect_url": reverse("view_data") + query_string,
    })
#-------------------------------------------------------------------------------------------------------
@login_required
@user_passes_test(is_admin)
def view_data(request):
    selected_table = request.GET.get("table", "categories")
    query = request.GET.get("q", "")
    selected_category = request.GET.get("category", "")  # ✅ نقرأ القسم المختار
    success_message = None

    # ✅ حذف
    if request.method == "POST":
        if "delete_category" in request.POST:
            Category.objects.filter(id=request.POST.get("delete_category")).delete()
            success_message = "❌ تم حذف القسم بنجاح"
        elif "delete_product" in request.POST:
            Product.objects.filter(id=request.POST.get("delete_product")).delete()
            success_message = "❌ تم حذف المنتج بنجاح"
        elif "delete_branch" in request.POST:
            Branch.objects.filter(id=request.POST.get("delete_branch")).delete()
            success_message = "❌ تم حذف الفرع بنجاح"

    categories = Category.objects.all()
    products = Product.objects.all()
    branches = Branch.objects.all()

    # ✅ فلترة المنتجات
    if selected_table == "products":
        if query:
            products = products.filter(name__icontains=query)
        if selected_category:
            products = products.filter(category_id=selected_category)

    return render(request, "orders/view_data.html", {
        "categories": categories,
        "products": products,
        "branches": branches,
        "selected_table": selected_table,
        "query": query,
        "selected_category": selected_category,
        "success_message": success_message,
    })
#-------------------------------------------------------------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import DailyRequest, Product, OrderCounter
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
@login_required
def add_daily_request(request):
    profile2 = getattr(request.user, "userprofile", None)

    # 🚫 لو مش كنترول او ادمن
    if not profile2 or profile2.role not in ["branch"]:
        return render(
            request,
            "orders/no_permission.html",
            {
                "error_message": "🚫 غير مسموح لك بدخول هذه الصفحة. من فضلك تواصل مع مدير النظام لو محتاج صلاحية."
            },
            status=403
        )
    branch = request.user.userprofile.branch

    # 🔑 رقم الطلبية مؤقت مخزن في السيشن
    order_number = request.session.get("current_order_number")
    if not order_number:
        counter, _ = OrderCounter.objects.get_or_create(id=1)
        counter.current_number += 1
        counter.save()
        order_number = str(counter.current_number)
        request.session["current_order_number"] = order_number

    # 🟢 رجّع القسم المختار (لو موجود في السيشن)
    selected_category = request.session.get("selected_category")

    if request.method == "POST":
        if "add_item" in request.POST:
            # ➕ إضافة منتج جديد (أو زيادة الكمية لو موجود قبل كده)
            category_id = request.POST.get("category")
            product_id = request.POST.get("product")
            qty = int(request.POST.get("quantity", 1))

            if product_id and qty > 0:
                try:
                    # لو المنتج موجود بنفس الطلبية → زود الكمية
                    dr = DailyRequest.objects.get(
                        branch=branch,
                        category_id=category_id,
                        product_id=product_id,
                        order_number=order_number,
                        is_confirmed=False
                    )
                    dr.quantity += qty
                    dr.save()
                except DailyRequest.DoesNotExist:
                    # لو مش موجود → أضف صف جديد
                    DailyRequest.objects.create(
                        branch=branch,
                        category_id=category_id,
                        product_id=product_id,
                        quantity=qty,
                        created_by=request.user,
                        order_number=order_number,
                        is_confirmed=False
                    )

            # ✅ خزّن القسم المختار في السيشن عشان يفضل بعد الريدايركت
            request.session["selected_category"] = category_id

            return redirect("add_daily_request")

        elif "update_item" in request.POST:
            # ✏️ تعديل الكمية
            req_id = request.POST.get("request_id")
            new_qty = request.POST.get("new_quantity")
            if req_id and new_qty:
                try:
                    dr = DailyRequest.objects.get(
                        id=req_id,
                        branch=branch,
                        order_number=order_number,
                        is_confirmed=False
                    )
                    dr.quantity = int(new_qty)
                    dr.save()
                except DailyRequest.DoesNotExist:
                    pass
            return redirect("add_daily_request")

        elif "delete_item" in request.POST:
            # 🗑️ حذف المنتج
            req_id = request.POST.get("request_id")
            if req_id:
                DailyRequest.objects.filter(
                    id=req_id,
                    branch=branch,
                    order_number=order_number,
                    is_confirmed=False
                ).delete()
            return redirect("add_daily_request")

        elif "confirm_order" in request.POST:
            # ✅ تأكيد الطلبية
            now = timezone.now()
            DailyRequest.objects.filter(
                order_number=order_number,
                branch=branch
            ).update(
                is_confirmed=True,
                confirmed_at=now
            )

            # 🧩 إرسال تحديث لحظي للكنترول
            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                "control_updates",
                {
                    "type": "control_update",
                    "action": "new",
                    "message": f"🆕 طلبية جديدة من فرع {branch.name}",
                    "order_number": order_number,
                }
            )

            # 🧹 امسح رقم الطلبية و القسم بعد التأكيد
            request.session["current_order_number"] = None
            request.session["selected_category"] = None
            return redirect("add_daily_request")


    # البيانات للـ HTML
    products = Product.objects.all()
    categories = Category.objects.all()
    requests_today = DailyRequest.objects.filter(
        order_number=order_number,
        branch=branch,
        is_confirmed=False
    )

    return render(request, "orders/add_daily_request.html", {
        "products": products,
        "categories": categories,
        "requests_today": requests_today,
        "order_number": order_number,
        "selected_category": selected_category,  # ✅ بيرجع القسم للـ HTML
    })


#-------------------------------------------------------------------------------------------------------
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import localdate, now
from django.shortcuts import render, redirect
from .models import DailyRequest, Branch

@login_required
def control_requests(request):
    profile = getattr(request.user, "userprofile", None)

    # 🚫 لو مش كنترول او ادمن
    if not profile or profile.role not in ["control", "admin"]:
        return render(
            request,
            "orders/no_permission.html",
            {
                "error_message": "🚫 غير مسموح لك بدخول هذه الصفحة. من فضلك تواصل مع مدير النظام لو محتاج صلاحية."
            },
            status=403
        )

    today = timezone.now().date()  # تاريخ اليوم
    branch_id = request.GET.get("branch")
    start_date = request.GET.get("start_date", str(localdate()))
    end_date = request.GET.get("end_date", str(localdate()))
    printed_filter = request.GET.get("printed", "no")

    requests_qs = DailyRequest.objects.filter(is_confirmed=True, created_at__date__range=[start_date, end_date])

    if branch_id:
        requests_qs = requests_qs.filter(branch_id=branch_id)

    if printed_filter == "yes":
        requests_qs = requests_qs.filter(is_printed=True)
    elif printed_filter == "no":
        requests_qs = requests_qs.filter(is_printed=False)

    # Group by (branch, order_number, created_by)
    grouped_requests = {}
    for r in requests_qs.select_related("branch", "product", "created_by").order_by("order_number", "created_at"):
        key = (r.branch, r.order_number, r.created_by)
        grouped_requests.setdefault(key, []).append(r)

    branches = Branch.objects.all()

    return render(request, "orders/control_requests.html", {
        "today": today,
        "grouped_requests": grouped_requests,
        "branches": branches,
        "selected_start": start_date,
        "selected_end": end_date,
        "selected_branch": branch_id,
        "printed_filter": printed_filter,
    })
#-------------------------sockets-------------------------------------------------------------------------
from django.http import JsonResponse
from django.template.loader import render_to_string

@login_required
def control_requests_data(request):
    """ترجع HTML الطلبات فقط لتحديث الصفحة عبر AJAX"""
    today = timezone.now().date()
    branch_id = request.GET.get("branch")
    start_date = request.GET.get("start_date", str(localdate()))
    end_date = request.GET.get("end_date", str(localdate()))
    printed_filter = request.GET.get("printed", "no")

    requests_qs = DailyRequest.objects.filter(is_confirmed=True, created_at__date__range=[start_date, end_date])

    if branch_id:
        requests_qs = requests_qs.filter(branch_id=branch_id)

    if printed_filter == "yes":
        requests_qs = requests_qs.filter(is_printed=True)
    elif printed_filter == "no":
        requests_qs = requests_qs.filter(is_printed=False)

    grouped_requests = {}
    for r in requests_qs.select_related("branch", "product", "created_by").order_by("order_number", "created_at"):
        key = (r.branch, r.order_number, r.created_by)
        grouped_requests.setdefault(key, []).append(r)

    html = render_to_string("orders/_requests_list.html", {
        "grouped_requests": grouped_requests,
        "today": today,
    }, request=request)

    return JsonResponse({"html": html})
#-------------------------------------------------------------------------------------------------------
from django.utils import timezone
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@require_POST
@login_required
def mark_printed(request, order_number):
    requests = DailyRequest.objects.filter(order_number=order_number)
    if not requests.exists():
        return JsonResponse({"status": "not_found"}, status=404)

    # ✅ تحديث الحالة
    requests.update(is_printed=True, printed_at=timezone.now())

    # ✅ إرسال تحديث للسوكيت
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        "control_updates",
        {
            "type": "control_update",
            "action": "printed",
            "message": f"طلبية رقم {order_number} تم تعليمها مطبوعة ✅",
            "order_number": order_number,
        }
    )

    return JsonResponse({"status": "ok"})
#-------------------------------------------------------------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localdate
from django.shortcuts import render
from .models import DailyRequest

@login_required
def branch_requests(request):
    profile = getattr(request.user, "userprofile", None)

    # 🚫 لو مش فرع
    if not profile or profile.role not in ["branch"]:
        return render(
            request,
            "orders/no_permission.html",
            {
                "error_message": "🚫 غير مسموح لك بدخول هذه الصفحة."
            },
            status=403
        )

    branch = profile.branch
    today = localdate()

    start_date = request.GET.get("start_date", str(today))
    end_date = request.GET.get("end_date", str(today))
    printed_filter = request.GET.get("printed", "no")

    # ✅ الطلبات المؤكدة الخاصة بالفرع الحالي فقط
    requests_qs = DailyRequest.objects.filter(
        is_confirmed=True,
        branch=branch,
        created_at__date__range=[start_date, end_date]
    )

    if printed_filter == "yes":
        requests_qs = requests_qs.filter(is_printed=True)
    elif printed_filter == "no":
        requests_qs = requests_qs.filter(is_printed=False)

    # ✅ Group by (branch, order_number, created_by)
    grouped_requests = {}
    for r in requests_qs.select_related("product", "created_by").order_by("order_number", "created_at"):
        key = (branch, r.order_number, r.created_by)
        grouped_requests.setdefault(key, []).append(r)

    return render(request, "orders/branch_requests.html", {
        "today": today,
        "grouped_requests": grouped_requests,
        "branches": [branch],          # mirror للكنترول بس للفرع الحالي
        "selected_branch": branch.id,  # يتعلم في الـ select
        "selected_start": start_date,
        "selected_end": end_date,
        "printed_filter": printed_filter,
        "branch": branch,
    })
