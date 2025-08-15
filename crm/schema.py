import graphene
import re
from graphene_django.types import DjangoObjectType
from .models import Customer
from graphql import GraphQLError
from django.db import transaction

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        # Validation + saving will go here
        from graphql import GraphQLError

        if Customer.objects.filter(email=email).exists():
            raise GraphQLError("Customer with this email already exists.")

        if phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', phone):
            raise GraphQLError("Invalid phone number format. Use +1234567890 or 123-456-7890.")

        customer = Customer(name=name, email=email, phone=phone)
        customer.save()
        return CreateCustomer(customer=customer, message="Customer created successfully.")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(
            graphene.InputObjectType(
                'CustomerInput',
                name=graphene.String(required=True),
                email=graphene.String(required=True),
                phone=graphene.String(required=False)
            ),
            required=True
        )

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

def mutate(self, info, customers):
    
    valid_customers = []
    errors = []

    phone_regex = re.compile(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$')
    existing_emails = set(Customer.objects.values_list('email', flat=True))
    new_emails = set()

    for index, customer in enumerate(customers):
        # Check duplicate in DB or in current batch
        if customer.email in existing_emails or customer.email in new_emails:
            errors.append(f"Customer {index+1}: Email '{customer.email}' already exists.")
            continue

        # Validate phone number
        if customer.phone and not phone_regex.match(customer.phone):
            errors.append(f"Customer {index+1}: Invalid phone number '{customer.phone}'.")
            continue

        valid_customers.append(
            Customer(name=customer.name, email=customer.email, phone=customer.phone)
        )
        new_emails.add(customer.email)

    # Save valid customers if there are no errors
    if valid_customers:
        with transaction.atomic():
            Customer.objects.bulk_create(valid_customers)

    return CreateCustomers(
        customers=valid_customers,
        errors=errors,
        message=(
            "Some customers were not created due to errors."
            if errors else
            "All customers created successfully."
        )
    )
    
