import io
import os
import zipfile
import tempfile
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4

from django.http import FileResponse, HttpResponse
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

    @admin.display(ordering='orders_count')
    def orders(self, customer):
        url = (
            reverse('admin:store_order_changelist')
            + '?'
            + urlencode({
                'customer__id': str(customer.id)
            }))
        return format_html('<a href="{}">{} Orders</a>', url, customer.orders_count)

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
    actions = ['download_invoices']
    list_display = ['id', 'placed_at', 'payment_status', 'customer']
    inlines = [OrderItemInline]
    list_editable = ['payment_status']
    list_related = ['customer']
    autocomplete_fields = ['customer']
    list_per_page = 20
    ordering = ['placed_at', 'id']
    

    @admin.action(description="Download Invoice")
    def download_invoices(self, request, queryset: QuerySet):
        # order_details_queryset = queryset. \
        #                          prefetch_related('customer')

        self.message_user(
            request,
            f"Invoice downloaded successfully.",
            messages.SUCCESS
        )

        # with tempfile.SpooledTemporaryFile() as tmp:
        #     with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
        for index, order in enumerate(queryset):

            # Set annotated fields
            full_name = order.customer.first_name \
                        + ' ' \
                        + order.customer.last_name
            
            order_date = order.placed_at
            order_items = list(models.OrderItem.objects.filter(order__id=order.id).select_related('product'))
            total_invoice_amount = 0.0
            product_set = []

            # Annotate Total and all products
            for ii, order_item in enumerate(order_items, start=1):
                
                current_total = float(order_item.unit_price) * order_item.quantity
                total_invoice_amount += current_total
                current_product = {
                    'title': order_item.product.title,
                    'unit_price': order_item.unit_price,
                    'quantity': order_item.quantity,
                    'net_price': current_total,
                }

                product_set.append(current_product.copy())

                # print(f"{ii} {order_item.product.title} {order_item.unit_price} {order_item.quantity} {current_total}")


            return self.download_invoice(
                request=request,
                order_id=order.id,
                customer_name=full_name,
                placed_at=order_date.strftime("%d-%m-%Y"),
                invoice_date=datetime.datetime.today().strftime("%d/%m/%Y"),
                product_set=product_set,
                grand_total=total_invoice_amount
                )


    def download_invoice(self, request, order_id: int, customer_name: str, 
        placed_at: str, invoice_date: str, grand_total: float,
        product_set):
        
        # Create a file-like buffer to receive PDF data.
        buffer = io.BytesIO()

        # Create the PDF object, using the buffer as its "file."
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        print(width, height)
        p.setFont("Helvetica", 14)

        # Draw things on the PDF. Here's where the PDF generation happens.
        # See the ReportLab documentation for the full list of functionality.

        x1 = 20  # Padding from left
        y1 = height - 20  # Padding from bottom
        p.drawString(x1, y1, 'Sales Invoice')
        

        # Customer Info
        y1 -= 40
        p.drawString(x1, y1, f'Order ID: {order_id}')
        p.drawString(410, y1, f"Order Date: {placed_at}")

        y1 -= 20
        p.drawString(x1, y1, f'Customer Name: {customer_name}')
        
        y1 -= 20
        p.drawString(x1, y1, 'Contact Number: +91******6789')

        y1 -= 20
        p.drawString(x1, y1, f'Customer Email: ********{customer_name[-3:]}123@gmail.com')


        # Adress Section
        y1 -= 36
        address_padding_x = 80
        p.drawString(x1, y1, f'Address:')
        p.drawString(address_padding_x, y1, f'69, 420th floor, Green City Appartments')
        y1 -= 20
        p.drawString(address_padding_x, y1, f'Vakola, Santacruz East, Mumbai, Maharashtra')
        y1 -= 20
        p.drawString(address_padding_x, y1, f'Mumbai - 400055')

        # Add QR CODE
        QR_PATH: str = r'C:\Users\tejas\Projects\Web Development\storefront\store\e-store-text-400px.png'
        p.drawImage(QR_PATH, 410, y1, width=120, height=120)

        # Product Chart
        y1 -= 60

        tbale_start_y = y1
        p.line(x1 - 5, y1 + 15, width - 15, y1 + 15)
        p.drawString(x1, y1, f"{'No.':<5} {'Title':<80} {'Unit Price':<16} {'Quantity':<12} {'Net Price':<16}")
        p.line(x1 - 5, y1 - 5, width - 15, y1 - 5)

        for ii, product in enumerate(product_set, start=1):
            y1 -= 20
            p.drawString(x1, y1, f"{ii:<5} {product.get('title'):<80}")
            p.drawString(380, y1, str(product.get('unit_price')))
            p.drawString(480, y1, str(product.get('quantity')))
            p.drawString(540, y1, str(product.get('net_price')))
            p.line(x1 - 5, y1 - 5, width - 15, y1 - 5)

        y1 -= 28
        p.drawString(410, y1, f"Grand Total:       {grand_total} INR")

        # Close the PDF object cleanly, and we're done.
        p.showPage()
        p.save()
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=True, filename='hello.pdf')
