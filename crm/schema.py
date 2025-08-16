import graphene
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from decimal import Decimal
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Customer, Product, Order
from django.utils import timezone

# -------------------- Types --------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = "__all__"


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = "__all__"


# -------------------- Input Objects --------------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(default_value=None)


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True) # Accept as string to safely convert to Decimal
    stock = graphene.Int(default_value=0)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
    order_date = graphene.DateTime(default_value=None)


# -------------------- Mutations --------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, input):
        # Validate email
        try:
            validate_email(input.email)
        except ValidationError:
            raise GraphQLError("Invalid email format")

        # Ensure unique email
        if Customer.objects.filter(email=input.email).exists():
            raise GraphQLError("Email already exists")

        # Optional phone validation
        if input.phone and not (input.phone.startswith("+") or input.phone.replace("-", "").isdigit()):
            raise GraphQLError("Invalid phone format. Use +1234567890 or 123-456-7890")

        # Create customer
        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=input.phone
        )
        return CreateCustomer(customer=customer, message="Customer created successfully")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(graphene.NonNull(CustomerInput), required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        created_customers = []
        errors = []

        with transaction.atomic():
            for idx, cust in enumerate(input, start=1):
                try:
                    validate_email(cust.email)
                    if Customer.objects.filter(email=cust.email).exists():
                        errors.append(f"Row {idx}: Email already exists")
                        continue
                    if cust.phone and not (cust.phone.startswith("+") or cust.phone.replace("-", "").isdigit()):
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
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()

    def mutate(self, info, input):
        try:
            price = Decimal(input.price)
        except:
            raise GraphQLError("Invalid decimal format for price")

        if price <= 0:
            raise GraphQLError("Price must be positive")
        if input.stock < 0:
            raise GraphQLError("Stock cannot be negative")

        product = Product.objects.create(
            name=input.name,
            price=price,
            stock=input.stock
        )
        return CreateProduct(product=product, message="Product created successfully")


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()

    def mutate(self, info, input):
        try:
            customer = Customer.objects.get(id=input.customer_id)
        except Customer.DoesNotExist:
            raise GraphQLError("Invalid customer ID")

        products = list(Product.objects.filter(id__in=input.product_ids))
        if len(products) != len(input.product_ids):
            raise GraphQLError("Some product IDs are invalid")

        if not products:
            raise GraphQLError("Order must include at least one product")

        total_amount = sum(p.price for p in products)
        order = Order.objects.create(
            customer=customer,
            order_date=input.order_date or timezone.now(),
            total_amount=total_amount
        )
        order.products.set(products)

        return CreateOrder(order=order, message="Order created successfully")


# -------------------- Schema Mutation --------------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

