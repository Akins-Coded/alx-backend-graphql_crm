from celery import shared_task
from django.utils import timezone
from django.db.models import Sum
from crm.models import Customer, Order  # adjust to your actual model names

@shared_task
def generate_crm_report():
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum("totalamount"))["total"] or 0

    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, {total_revenue} revenue\n"

    with open("/tmp/crm_report_log.txt", "a") as f:
        f.write(report)

    return report
