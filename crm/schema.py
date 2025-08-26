import graphene
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from decimal import Decimal
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Customer, Product, Order
from django.utils import timezone
from .filters import CustomerFilter, ProductFilter, OrderFilter
from graphene_django.filter import DjangoFilterConnectionField


# -------------------- Types --------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "stock")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order

class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        filterset_class = CustomerFilter
        interfaces = (graphene.relay.Node,)

class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        filterset_class = ProductFilter
        interfaces = (graphene.relay.Node,)

class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        filterset_class = OrderFilter
        interfaces = (graphene.relay.Node,)



# -------------------- Input Objects --------------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(default_value=None)


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.String(required=True) 
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



# -------------------- Queries --------------------
class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerNode)
    all_products = DjangoFilterConnectionField(ProductNode)
    all_orders = DjangoFilterConnectionField(OrderNode)

    # Optional custom ordering argument
    all_customers_ordered = DjangoFilterConnectionField(
        CustomerNode, order_by=graphene.List(of_type=graphene.String)
    )
    all_products_ordered = DjangoFilterConnectionField(
        ProductNode, order_by=graphene.List(of_type=graphene.String)
    )
    all_orders_ordered = DjangoFilterConnectionField(
        OrderNode, order_by=graphene.List(of_type=graphene.String)
    )

    def resolve_all_customers_ordered(root, info, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_products_ordered(root, info, order_by=None, **kwargs):
        qs = Product.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_orders_ordered(root, info, order_by=None, **kwargs):
        qs = Order.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs


class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass  # no arguments needed

    success = graphene.Boolean()
    message = graphene.String()
    updated_products = graphene.List(ProductType)

    @classmethod
    def mutate(cls, root, info):
        low_stock_products = Product.objects.filter(stock__lt=10)
        updated = []

        for product in low_stock_products:
            product.stock += 10  # simulate restock
            product.save()
            updated.append(product)

        if updated:
            return UpdateLowStockProducts(
                success=True,
                message=f"{len(updated)} products updated at {timezone.now()}",
                updated_products=updated,
            )
        else:
            return UpdateLowStockProducts(
                success=True,
                message="No low-stock products found",
                updated_products=[]
            )


class Mutation(graphene.ObjectType):
    update_low_stock_products = UpdateLowStockProducts.Field()