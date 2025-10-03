from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),       # الصفحة الرئيسية الجديدة
    path("dashboard/", views.root_redirect, name="home"),   # الداشبورد القديمة
    path("reservations/", views.reservations_list, name="reservations_list"),
    path("reservations/<int:res_id>/<str:status>/", views.update_reservation_status, name="update_reservation_status"),
    path("reports/", views.reports, name="reports"),
    path("reports/export/excel/", views.export_reports_excel, name="export_reports_excel"),
    path("callcenter/", views.callcenter_dashboard, name="callcenter_dashboard"),
    path("branch/", views.branch_dashboard, name="branch_dashboard"),
    path("login/", views.landing, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("export-reservations/<int:branch_id>/", views.export_reservations_excel, name="export_reservations_excel"),
    path("branch/export/excel/", views.export_inventory_excel, name="branch_export_inventory_excel"),
    path("customers/", views.customers_list, name="customers_list"),
    path("landing/", views.landing, name="landing"), # الصفحة الجديدة
    path("inventory/update/", views.update_inventory, name="update_inventory"),
    path("inventory/transactions/", views.inventory_transactions, name="inventory_transactions"),
    path("branch/inventory/", views.branch_inventory, name="branch_inventory"),
    path("customers/use/<int:customer_id>/", views.use_customer, name="use_customer"),
    path("customers/add/", views.add_customer, name="add_customer"),
    path("customers/resolve_conflict/", views.resolve_conflict, name="resolve_conflict"),
    path("add-user/", views.add_user_view, name="add_user"),
    path("password/change/", views.change_password, name="change_password"),
    path("manage-data/", views.manage_data, name="manage_data"),
    path("manage-users/", views.manage_users, name="manage_users"),
    path("edit-category/<int:pk>/", views.edit_category, name="edit_category"),
    path("edit-product/<int:pk>/", views.edit_product, name="edit_product"),
    path("edit-branch/<int:pk>/", views.edit_branch, name="edit_branch"),
    path("view-data/", views.view_data, name="view_data"),
    path("daily-request/", views.add_daily_request, name="add_daily_request"),
    path("control-requests/", views.control_requests, name="control_requests"),
    path("branch/requests/", views.branch_requests, name="branch_requests"),
    path("mark-printed/<str:order_number>/", views.mark_printed, name="mark_printed"),

]
