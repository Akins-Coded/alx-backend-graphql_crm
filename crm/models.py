from django.db import models
from django.utils import timezone

# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
            return f"{self.name} ({self.email})"

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    stock = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
      return f"{self.name} - ${self.price}"
    
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, related_name="orders")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_date = models.DateTimeField(default=timezone.now)

    def calculate_total(self):
        """Utility to calculate total price of products in order."""
        total = sum(product.price for product in self.products.all())
        self.total_amount = total
        self.save(update_fields=["total_amount"])
        return total

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name} (${self.total_amount})"