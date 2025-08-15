import os
import django
from datetime import datetime

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "graphql_crm.settings")
django.setup()

from crm.models import Customer, Product, Order

def run():
    # Clear old data
    Order.objects.all().delete()
    Customer.objects.all().delete()
    Product.objects.all().delete()

    # Create customers
    customers = [
        Customer(name="Alice Johnson", email="alice@example.com", phone="+1234567890"),
        Customer(name="Bob Smith", email="bob@example.com", phone="123-456-7890"),
        Customer(name="Carol White", email="carol@example.com"),
    ]
    Customer.objects.bulk_create(customers)

    # Create products
    products = [
        Product(name="Laptop", price=999.99, stock=10),
        Product(name="Mouse", price=25.50, stock=50),
        Product(name="Keyboard", price=45.75, stock=30),
    ]
    Product.objects.bulk_create(products)

    # Create orders
    alice = Customer.objects.get(email="alice@example.com")
    bob = Customer.objects.get(email="bob@example.com")

    laptop = Product.objects.get(name="Laptop")
    mouse = Product.objects.get(name="Mouse")
    keyboard = Product.objects.get(name="Keyboard")

    order1 = Order.objects.create(
        customer=alice,
        order_date=datetime.now(),
        total_amount=laptop.price + mouse.price
    )
    order1.products.set([laptop, mouse])

    order2 = Order.objects.create(
        customer=bob,
        order_date=datetime.now(),
        total_amount=keyboard.price
    )
    order2.products.set([keyboard])

    print("✅ Database seeded successfully!")

if __name__ == "__main__":
    run()
