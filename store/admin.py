from django.contrib import admin
from django.db.models.aggregates import Count
from . import models


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'membership']
    list_editable = ['membership']
    list_per_page = 50
    ordering = ['first_name', 'last_name']

@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit_price', 'inventory_status' ,'collection_title']
    list_editable = ['unit_price']
    list_select_related = ['collection']
    list_per_page = 20
    ordering = ['title', 'unit_price']

    @admin.display(ordering='title')
    def collection_title(self, product):
        return product.collection.title

    @admin.display(ordering='inventory')
    def inventory_status(self, product):
        current_inventory = product.inventory
        if current_inventory < 5:
            return "Very Few"
        
        elif current_inventory < 20:
            return "Low"

        elif current_inventory < 40:
            return "OK"
        
        return "High"

@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'product_count']

    @admin.display(ordering='product_count')
    def product_count(self, collection):
        return collection.product_count
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            product_count=Count('product')
        )


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'placed_at', 'payment_status', 'customer']
    list_editables = ['payment_status']
    list_related = ['customers']
    list_per_page = 20
    ordering = ['placed_at', 'id']