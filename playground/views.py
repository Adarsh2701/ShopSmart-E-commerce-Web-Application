import io
from django.http import FileResponse
from reportlab.pdfgen import canvas

from django.forms import DecimalField
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q, F, Value
from django.db.models import ExpressionWrapper
from store.models import Product, Customer, Order, OrderItem


def say_hello(request):
    
    # discounted_price = ExpressionWrapper(
    #     F('unit_price') * 0.9, output_field=DecimalField()
    # )

    # query_set = Product.objects.annotate(discounted_price=discounted_price)
    query_set = Product.objects.values('id', 'title', 'unit_price')

    return render(request, 'hello.html', {'name': 'Tejas', 'result': list(query_set)})


def download_pdf(request):
    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer)

    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    p.drawString(100, 100, "Hello world.")

    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='hello.pdf')
