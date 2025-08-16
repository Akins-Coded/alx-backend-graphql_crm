import graphene
from crm.schema import CreateCustomer, BulkCreateCustomers, CreateProduct, CreateOrder
from crm.schema import CustomerType, ProductType, OrderType

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(root, info):
        from crm.models import Customer
        return Customer.objects.all()

schema = graphene.Schema(query=Query, mutation=Mutation)
