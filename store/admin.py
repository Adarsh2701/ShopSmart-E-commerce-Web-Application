from django.contrib import admin, messages
from django.db.models.aggregates import Count
from django.urls import reverse
from django.utils.html import format_html, urlencode
from django.db.models import Q, F, Value
from django.db.models import QuerySet
from . import models


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'membership', 'orders']
    list_editable = ['membership']
    list_per_page = 20
    ordering = ['first_name', 'last_name']
    search_fields = ['first_name__istartswith', 'last_name__istartswith']

    def orders(self, customer):
        url = (
            reverse('admin:store_order_changelist')
            + '?'
            + urlencode({
                'cutomer__id': str(customer.id),
            })
        )

        return format_html('<a href="{}">{}</a>', url, customer.orders_count)
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            orders_count=Count('order')
        )


class InventoryFilter(admin.SimpleListFilter):
    title = 'inventory'
    parameter_name = 'inventory'

    def lookups(self, request, model_admin):
        return [
            ('<5', 'Very Few'),
            ('<20', 'Low'),
            ('<40', 'Moderate'),
            ('>40', 'High'),
        ]
    
    def queryset(self, request, queryset: QuerySet):
        if self.value() == '<5':
            return queryset.filter(inventory__lte=5)
        elif self.value() == '<20':
            return queryset.filter(inventory__gt=5).filter(inventory__lte=20)
        elif self.value() == '<40':
            return queryset.filter(inventory__gt=20).filter(inventory__lte=40)
        elif self.value() == '>40':
            return queryset.filter(inventory__gt=40)
        

@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    actions = ['clear_inventory']
    autocomplete_fields = ['collection']
    prepopulated_fields = {
        'slug': ['title', 'collection']
    }
    list_display = ['title', 'unit_price', 'inventory_status' ,'collection_title']
    list_editable = ['unit_price']
    list_filter = ['collection', 'last_update', InventoryFilter]
    list_select_related = ['collection']
    list_per_page = 20
    ordering = ['title', 'unit_price']
    search_fields = ['title__istartswith']

    @admin.display(ordering='title')
    def collection_title(self, product):
        return product.collection.title

    @admin.display(ordering='inventory')
    def inventory_status(self, product):
        current_inventory = product.inventory
        if current_inventory <= 5:
            return "Very Few"
        
        elif current_inventory <= 20:
            return "Low"

        elif current_inventory <= 40:
            return "Moderate"
        
        return "High"
    
    @admin.action(description="Clear Inventory")
    def clear_inventory(self, request, queryset):
        updated_count = queryset.update(inventory=0)
        self.message_user(
            request,
            f"{updated_count} products was successfully updated.",
            messages.SUCCESS
        )

@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'product_count']
    ordering = ['title']
    search_fields = ['title']

    @admin.display(ordering='product_count')
    def product_count(self, collection):
        url = (
            reverse('admin:store_product_changelist')
            + '?'
            + urlencode({
                'collection__id': str(collection.id),
            }))
        return format_html('<a href="{}">{}</a>', url, collection.product_count)
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            product_count=Count('product')
        )


class OrderItemInline(admin.TabularInline):
    autocomplete_fields = ['product']
    model = models.OrderItem
    min_num = 1
    max_num = 10
    extra = 0

@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'placed_at', 'payment_status', 'customer']
    inlines = [OrderItemInline]
    list_editable = ['payment_status']
    list_related = ['customer']
    autocomplete_fields = ['customer']
    list_per_page = 20
    ordering = ['placed_at', 'id']
    