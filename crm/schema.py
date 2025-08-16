import graphene
import re
from graphene_django.types import DjangoObjectType
from .models import Customer, Product, Order
from graphql import GraphQLError
from django.db import transaction

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer

class ProductType(DjangoObjectType):
    class Meta:
        model = Product

class OrderType(DjangoObjectType):
    class Meta:
        model = Order

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            raise GraphQLError("Invalid email format")

        # Ensure unique email
        if Customer.objects.filter(email=email).exists():
            raise GraphQLError("Email already exists")

        # Optional phone validation
        if phone and not (
            phone.startswith("+") or phone.replace("-", "").isdigit()
        ):
            raise GraphQLError("Invalid phone format. Use +1234567890 or 123-456-7890")

        customer = Customer.objects.create(name=name, email=email, phone=phone)
        return CreateCustomer(customer=customer, message="Customer created successfully")

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(graphene.NonNull(CustomerInput), required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        created_customers = []
        errors = []

        with transaction.atomic():
            for idx, cust in enumerate(customers, start=1):
                try:
                    validate_email(cust.email)
                    if Customer.objects.filter(email=cust.email).exists():
                        errors.append(f"Row {idx}: Email already exists")
                        continue
                    if cust.phone and not (
                        cust.phone.startswith("+") or cust.phone.replace("-", "").isdigit()
                    ):
                        errors.append(f"Row {idx}: Invalid phone format")
                        continue

                    created_customers.append(
                        Customer.objects.create(
                            name=cust.name,
                            email=cust.email,
                            phone=cust.phone
                        )
                    )
                except ValidationError:
                    errors.append(f"Row {idx}: Invalid email format")

        return BulkCreateCustomers(customers=created_customers, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(required=False, default_value=0)

    product = graphene.Field(ProductType)

    def mutate(self, info, name, price, stock):
        if price <= 0:
            raise GraphQLError("Price must be positive")
        if stock < 0:
            raise GraphQLError("Stock cannot be negative")

        product = Product.objects.create(name=name, price=price, stock=stock)
        return CreateProduct(product=product)


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
        order_date = graphene.DateTime(required=False)

    order = graphene.Field(OrderType)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise GraphQLError("Invalid customer ID")

        products = list(Product.objects.filter(id__in=product_ids))
        if len(products) != len(product_ids):
            raise GraphQLError("Some product IDs are invalid")

        if not products:
            raise GraphQLError("Order must include at least one product")

        total_amount = sum(p.price for p in products)
        order = Order.objects.create(
            customer=customer,
            order_date=order_date or None,
            total_amount=total_amount
        )
        order.products.set(products)

        return CreateOrder(order=order)


# ----------------- Schema Mutation -----------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
