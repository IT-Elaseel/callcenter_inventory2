from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .models import Category, Product, Inventory, Reservation, Branch,Customer
from django.db.models import Count,Q
from django.utils.timezone import now, timedelta
import openpyxl
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .decorators import role_required
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from django.contrib.auth.forms import AuthenticationForm
from .models import Product, Inventory, InventoryTransaction
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse   # ✅ أضفت JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserCreateForm

#-------------------------------------------------------------------
def export_reservations_excel(request):
    reservations = Reservation.objects.select_related("product", "branch").order_by("-created_at")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reservations"

    # Header
    ws.append(["ID", "Customer", "Phone", "Product", "Branch", "Delivery Type", "Status", "Created At"])

    # Data
    for r in reservations:
        ws.append([
            r.id,
            r.customer_name,
            r.customer_phone,
            r.product.name,
            r.branch.name,
            r.get_delivery_type_display(),
            r.get_status_display(),
            r.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    # Response
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="reservations.xlsx"'
    wb.save(response)
    return response
#-------------------------------------------------------------
def home(request):
    query = request.GET.get("q")
    inventories = Inventory.objects.select_related("branch", "product", "product__category")

    if query:
        inventories = inventories.filter(product__name__icontains=query)

    # Handle Reservation
    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        customer_phone = request.POST.get("customer_phone")
        delivery_type = request.POST.get("delivery_type")
        product_id = request.POST.get("product_id")
        branch_id = request.POST.get("branch_id")

        # ✅ التشيك على رقم الموبايل (لو مكتوب)
        if customer_phone:
            if not customer_phone.isdigit() or len(customer_phone) != 11:
                messages.error(request, "❌ رقم الموبايل لازم يكون 11 رقم صحيح أو اتركه فارغ.")
                return redirect("home")
        else:
            customer_phone = None


        product = Product.objects.get(id=product_id)
        branch = Branch.objects.get(id=branch_id)

        # ✅ منطق العميل الجديد
        if customer_phone:
            existing_customers = Customer.objects.filter(phone=customer_phone)
        else:
            existing_customers = Customer.objects.none()


        if not existing_customers.exists():
            customer = Customer.objects.create(name=customer_name, phone=customer_phone)

        elif existing_customers.count() > 1:
            messages.warning(
                request,
                f"⚠️ الرقم {customer_phone} مرتبط بأكثر من عميل، من فضلك اختر من العملاء أو أنشئ عميل جديد."
            )
            return redirect("customers_list")

        else:
            existing_customer = existing_customers.first()
            if existing_customer.name == customer_name:
                customer = existing_customer
            else:
                messages.warning(
                    request,
                    f"⚠️ الرقم {customer_phone} موجود باسم {existing_customer.name}. "
                    f"هل تود استخدامه أم إنشاء عميل جديد؟"
                )
                return redirect("customers_list")

        try:
            inventory = Inventory.objects.get(product=product, branch=branch)

            if inventory.quantity > 0:
                # ✅ إنشاء الحجز بالطريقة الصحيحة
                Reservation.objects.create(
                    customer=customer,
                    product=product,
                    branch=branch,
                    delivery_type=delivery_type,
                    status="pending",
                     quantity=qty,
                    reserved_by=request.user if request.user.is_authenticated else None,
                )

                # خصم الكمية
                inventory.quantity -= 1
                inventory.save()

                messages.success(request, f"تم حجز {product.name} للعميل {customer.name}")
            else:
                messages.error(request, f"المنتج {product.name} غير متوفر في الفرع {branch.name}")
        except Exception as e:
            messages.error(request, f"حدث خطأ: {str(e)}")

        return redirect("home")

    categories = Category.objects.all()
    # ⬅️ هنا بنجيب آخر 20 حجز
    reservations = Reservation.objects.select_related(
        "customer", "product", "branch", "reserved_by"
    ).order_by("-created_at")[:20]

    return render(
        request,
        "orders/home.html",
        {
            "categories": categories,
            "inventories": inventories,
            "query": query,
            "reservations": reservations,  # ⬅️ مهم جداً
        },
    )

#-------------------------------------------------------------
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
        },
    )
#-------------------------------------------------------------
def update_reservation_status(request, res_id, status):
    reservation = get_object_or_404(Reservation, id=res_id)
    profile = getattr(request.user, "userprofile", None)

    is_admin = profile and profile.role == "admin"

    if status == "confirmed":
        reservation.confirm(user=request.user, is_admin=is_admin)
        messages.success(request, f"تم تأكيد الحجز للعميل {reservation.customer}")
    elif status == "cancelled":
        reservation.cancel(user=request.user, is_admin=is_admin)
        messages.warning(request, f"تم إلغاء الحجز للعميل {reservation.customer}")
    else:
        messages.error(request, "حالة غير معروفة")

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
def export_reservations_excel(request):
    reservations = Reservation.objects.select_related("product", "branch").order_by("-created_at")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reservations"

    # Header
    ws.append(["ID", "Customer", "Phone", "Product", "Branch", "Delivery Type", "Status", "Created At"])

    # Data
    for r in reservations:
        ws.append([
            r.id,
            r.customer_name,
            r.customer_phone,
            r.product.name,
            r.branch.name,
            r.get_delivery_type_display(),
            r.get_status_display(),
            r.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    # Response
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="reservations.xlsx"'
    wb.save(response)
    return response
#-------------------------------------------------------------
def export_reservations_pdf(request):
    reservations = Reservation.objects.select_related("product", "branch").order_by("-created_at")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reservations.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica", 12)
    p.drawString(50, y, "Reservations Report")
    y -= 30

    for r in reservations:
        line = f"{r.id} | {r.customer_name} | {r.customer_phone} | {r.product.name} | {r.branch.name} | {r.get_status_display()} | {r.created_at.strftime('%Y-%m-%d')}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()
    return response
#-------------------------------------------------------------
@login_required
@role_required(["callcenter"])
def callcenter_dashboard(request):
    query = request.GET.get("q")
    category_id = request.GET.get("category")

    # ✅ لو فيه category في GET → خزنه في Session
    if category_id is not None:
        request.session["selected_category"] = category_id
    else:
        category_id = request.session.get("selected_category")

    inventories = Inventory.objects.select_related("branch", "product", "product__category")

    # 🔎 منطق البحث + الفلترة
    if query and category_id:
        inventories = inventories.filter(
            product__category_id=category_id,
            product__name__icontains=query
        )
        if not inventories.exists():
            inventories = Inventory.objects.filter(
                product__name__icontains=query
            ).select_related("branch", "product", "product__category")
    elif query:
        inventories = inventories.filter(product__name__icontains=query)
    elif category_id:
        inventories = inventories.filter(product__category_id=category_id)

    # 📝 إضافة حجز جديد
    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        customer_phone = request.POST.get("customer_phone")
        delivery_type = request.POST.get("delivery_type")
        product_id = request.POST.get("product_id")
        branch_id = request.POST.get("branch_id")
        qty = int(request.POST.get("quantity", 1))

        # ✅ التشيك على رقم الموبايل (لو مكتوب)
        if customer_phone:
            if not customer_phone.isdigit() or len(customer_phone) != 11:
                return redirect("callcenter_dashboard")
        else:
            customer_phone = None

        product = Product.objects.get(id=product_id)
        branch = Branch.objects.get(id=branch_id)

        if customer_phone:
            existing_customers = Customer.objects.filter(phone=customer_phone)
        else:
            existing_customers = Customer.objects.none()

        if not existing_customers.exists():
            customer = Customer.objects.create(name=customer_name, phone=customer_phone)
        elif existing_customers.count() > 1:
            return render(
                request,
                "orders/callcenter.html",
                {
                    "categories": Category.objects.all(),
                    "inventories": inventories,
                    "query": query,
                    "selected_category": int(category_id) if category_id else None,
                    "reservations": Reservation.objects.select_related(
                        "customer", "product", "branch", "reserved_by"
                    ).order_by("-created_at")[:20],
                    "conflict_phone": customer_phone,
                    "conflict_name": customer_name,
                    "conflict_product_id": product_id,
                    "conflict_branch_id": branch_id,
                    "conflict_delivery_type": delivery_type,
                    "conflict_qty": qty,
                },
            )
        else:
            existing_customer = existing_customers.first()
            if existing_customer.name == customer_name:
                customer = existing_customer
            else:
                return render(
                    request,
                    "orders/callcenter.html",
                    {
                        "categories": Category.objects.all(),
                        "inventories": inventories,
                        "query": query,
                        "selected_category": int(category_id) if category_id else None,
                        "reservations": Reservation.objects.select_related(
                            "customer", "product", "branch", "reserved_by"
                        ).order_by("-created_at")[:20],
                        "conflict_phone": customer_phone,
                        "conflict_name": customer_name,
                        "conflict_product_id": product_id,
                        "conflict_branch_id": branch_id,
                        "conflict_delivery_type": delivery_type,
                        "conflict_qty": qty,
                    },
                )

        # ✅ إنشاء الحجز
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
                return redirect("callcenter_dashboard")
            else:
                # ❌ خطأ الكمية
                categories = Category.objects.all()
                reservations = Reservation.objects.select_related(
                    "customer", "product", "branch", "reserved_by"
                ).order_by("-created_at")[:20]
                return render(
                    request,
                    "orders/callcenter.html",
                    {
                        "categories": categories,
                        "inventories": inventories,
                        "query": query,
                        "selected_category": int(category_id) if category_id else None,
                        "reservations": reservations,
                        "quantity_error": {
                            "product_id": product.id,
                            "branch_id": branch.id,
                            "message": f"الكمية المطلوبة غير متوفرة (المتاح {inventory.quantity})"
                        },
                    },
                )
        except Exception as e:
            return redirect("callcenter_dashboard")

    # ✅ الحالة العادية
    categories = Category.objects.all()
    reservations = Reservation.objects.select_related(
        "customer", "product", "branch", "reserved_by"
    ).order_by("-created_at")[:20]

    return render(
        request,
        "orders/callcenter.html",
        {
            "categories": categories,
            "inventories": inventories,
            "query": query,
            "selected_category": int(category_id) if category_id else None,
            "reservations": reservations,
        },
    )
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
            return redirect("callcenter_dashboard")
        elif profile.role == "branch":
            return redirect("branch_dashboard")

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

    return render(request, "orders/customers_list.html", {"customers": customers})
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

            inventory, created = Inventory.objects.get_or_create(branch=branch, product=product)
            inventory.quantity = qty
            inventory.save()

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
    selected_category = request.GET.get("category") or request.session.get("selected_category")

    if selected_category:
        request.session["selected_category"] = selected_category

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
# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserCreateForm

# شرط يفتح الصفحة بس لو هو أدمن
def is_admin(user):
    return user.is_superuser or user.groups.filter(name="admin").exists()

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
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect
from .forms import ArabicPasswordChangeForm

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

        return render(request, "orders/reports.html", {   # غير reports.html لصفحتك
            "password_form": form,
            "success_message": success_message,
            "show_modal": show_modal,
        })

    return redirect("home")


#-------------------------------------------------------------------------------------------------------
